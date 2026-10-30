import os
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple

class PatchEngine:
    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    def _is_safe_path(self, path: str) -> bool:
        if not path or os.path.isabs(path):
            return False
        # Normalize path
        norm = os.path.normpath(path)
        parts = norm.split(os.sep)
        if ".." in parts or "." in parts[:1]:
            return False

        abs_path = os.path.abspath(os.path.join(self.repo_root, norm))
        real_repo = os.path.realpath(self.repo_root)

        # String prefix check
        if not (abs_path == self.repo_root or abs_path.startswith(self.repo_root + os.sep)):
            return False

        # Realpath check to prevent symlink escapes
        if os.path.exists(abs_path):
            real_file = os.path.realpath(abs_path)
            if not (real_file == real_repo or real_file.startswith(real_repo + os.sep)):
                return False
        else:
            # Walk up to closest existing ancestor directory
            curr = os.path.dirname(abs_path)
            while curr and not os.path.exists(curr):
                parent = os.path.dirname(curr)
                if parent == curr:
                    break
                curr = parent
            if curr and os.path.exists(curr):
                real_curr = os.path.realpath(curr)
                if not (real_curr == real_repo or real_curr.startswith(real_repo + os.sep)):
                    return False
        return True

    def detect_format(self, text: str) -> str:
        """Determines whether patch text is structured SEARCH/REPLACE or unified diff."""
        if "<<<<<<< SEARCH" in text:
            return "search_replace"
        elif ("--- " in text and "+++ " in text) or text.strip().startswith("diff --git"):
            return "unified_diff"
        elif any(line.strip().startswith("FILE:") or line.strip().startswith("### FILE:") for line in text.splitlines()):
            return "search_replace"
        return "unknown"

    def extract_target_files(self, patch_text: str) -> List[str]:
        """Extracts list of relative file paths targeted by the patch."""
        fmt = self.detect_format(patch_text)
        target_files = []
        if fmt == "search_replace":
            for line in patch_text.splitlines():
                s = line.strip()
                if s.startswith("FILE:"):
                    target_files.append(s[5:].strip())
                elif s.startswith("### FILE:"):
                    target_files.append(s[9:].strip())
                elif s.startswith("File:"):
                    target_files.append(s[5:].strip())
        elif fmt == "unified_diff":
            for line in patch_text.splitlines():
                if line.startswith("+++ b/"):
                    target_files.append(line[6:].strip())
                elif line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
                    target_files.append(line[4:].strip())

        # Clean and deduplicate while preserving order
        seen = set()
        clean = []
        for tf in target_files:
            tf = tf.strip().strip("'\"`")
            if tf.startswith("a/") or tf.startswith("b/"):
                tf = tf[2:]
            if tf and tf not in seen:
                seen.add(tf)
                clean.append(tf)
        return clean

    # -------------------------------------------------------------
    # SEARCH / REPLACE PARSER & APPLIER
    # -------------------------------------------------------------

    def _parse_search_replace(self, text: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Parses SEARCH/REPLACE blocks.
        Format:
        FILE: rel/path
        <<<<<<< SEARCH
        [search text]
        =======
        [replace text]
        >>>>>>> REPLACE
        """
        files: List[Dict[str, Any]] = []
        current_file: Optional[Dict[str, Any]] = None
        in_search = False
        in_replace = False
        search_lines: List[str] = []
        replace_lines: List[str] = []

        lines = text.splitlines()
        for line_num, line in enumerate(lines, start=1):
            s_line = line.strip()

            # Detect file header
            clean_hdr = s_line.lstrip("#/").strip()
            if (clean_hdr.startswith("FILE:") or clean_hdr.startswith("File:")) and not in_search and not in_replace:
                fname = clean_hdr[5:].strip().strip("'\"`")
                if fname.startswith("a/") or fname.startswith("b/"):
                    fname = fname[2:]

                current_file = {"file": fname, "blocks": []}
                files.append(current_file)
                continue

            if s_line == "<<<<<<< SEARCH":
                if in_search:
                    return False, [], f"MalformedBlockError (line {line_num}): Nested <<<<<<< SEARCH encountered."
                if in_replace:
                    return False, [], f"MalformedBlockError (line {line_num}): <<<<<<< SEARCH encountered before closing >>>>>>> REPLACE."
                if not current_file:
                    return False, [], f"MalformedBlockError (line {line_num}): SEARCH block encountered without FILE: header."

                in_search = True
                search_lines = []
                continue

            elif s_line == "=======":
                if not in_search:
                    return False, [], f"MalformedBlockError (line {line_num}): ======= delimiter without opening <<<<<<< SEARCH."
                in_search = False
                in_replace = True
                replace_lines = []
                continue

            elif s_line == ">>>>>>> REPLACE":
                if not in_replace:
                    return False, [], f"MalformedBlockError (line {line_num}): >>>>>>> REPLACE delimiter without ======= separator."
                in_replace = False
                current_file["blocks"].append({
                    "search": "\n".join(search_lines),
                    "replace": "\n".join(replace_lines),
                    "line": line_num
                })
                continue

            if in_search:
                search_lines.append(line)
            elif in_replace:
                replace_lines.append(line)

        if in_search:
            return False, [], "MalformedBlockError: Unclosed <<<<<<< SEARCH block (missing ======= and >>>>>>> REPLACE)."
        if in_replace:
            return False, [], "MalformedBlockError: Unclosed replacement block (missing >>>>>>> REPLACE)."

        if not files:
            return False, [], "No valid FILE: blocks found in patch."

        for f in files:
            if not f["blocks"]:
                return False, [], f"MalformedBlockError: File '{f['file']}' contains no SEARCH/REPLACE blocks."

        return True, files, ""

    def _apply_search_replace_file(self, rel_path: str, blocks: List[Dict[str, Any]]) -> Tuple[bool, str, str, str]:
        """
        Validates and applies SEARCH/REPLACE blocks in-memory to a single file.
        Returns: (success, new_content_str, original_hash, error_message)
        """
        abs_path = os.path.abspath(os.path.join(self.repo_root, rel_path))

        file_exists = os.path.exists(abs_path)
        original_bytes = b""
        original_text = ""
        original_hash = ""
        is_crlf = False
        has_trailing_nl = True

        if file_exists:
            try:
                with open(abs_path, "rb") as fb:
                    original_bytes = fb.read()
                original_hash = hashlib.sha256(original_bytes).hexdigest()
                original_text = original_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return False, "", "", f"UnsupportedEncoding: Target file '{rel_path}' is not valid UTF-8."
            except Exception as e:
                return False, "", "", f"FileReadError: Failed reading '{rel_path}': {str(e)}"

            is_crlf = ("\r\n" in original_text)
            has_trailing_nl = original_text.endswith("\r\n") or original_text.endswith("\n")
        else:
            # File creation scenario: only valid if exactly one block with empty search
            if len(blocks) != 1 or blocks[0]["search"].strip() != "":
                return False, "", "", f"FileNotFound: Cannot patch non-existent file '{rel_path}' (search block is not empty)."
            original_hash = ""

        # Normalize line breaks to \n for strict string matching
        norm_text = original_text.replace("\r\n", "\n")

        # Match each search block
        spans = []
        for idx, block in enumerate(blocks, start=1):
            s_content = block["search"].replace("\r\n", "\n")
            r_content = block["replace"].replace("\r\n", "\n")

            if not file_exists:
                # New file creation
                norm_text = r_content
                spans = []
                break

            count = norm_text.count(s_content)
            if count == 0:
                return False, "", "", f"SearchBlockNotFound: Exact search block #{idx} not found in '{rel_path}'."
            if count > 1:
                return False, "", "", f"AmbiguousMatchError: Search block #{idx} occurs {count} times in '{rel_path}' (must occur exactly once)."

            match_idx = norm_text.find(s_content)
            spans.append((match_idx, match_idx + len(s_content), r_content))

        if file_exists and spans:
            # Check for overlapping blocks
            spans.sort(key=lambda s: s[0])
            for i in range(len(spans) - 1):
                if spans[i][1] > spans[i + 1][0]:
                    return False, "", "", f"OverlappingBlocksError: Replacement blocks #{i+1} and #{i+2} overlap in '{rel_path}'."

            # Apply replacements from back to front to preserve offset indices
            for start_idx, end_idx, r_content in reversed(spans):
                norm_text = norm_text[:start_idx] + r_content + norm_text[end_idx:]

        # Restore original newline convention and trailing newline
        if is_crlf:
            final_text = norm_text.replace("\n", "\r\n")
        else:
            final_text = norm_text

        if has_trailing_nl and not (final_text.endswith("\r\n") or final_text.endswith("\n")):
            final_text += "\r\n" if is_crlf else "\n"

        return True, final_text, original_hash, ""

    # -------------------------------------------------------------
    # UNIFIED DIFF PARSER & APPLIER (Backward-Compatible)
    # -------------------------------------------------------------

    def _parse_diff(self, diff_text: str) -> List[Dict[str, Any]]:
        files = []
        current_file = None
        current_hunk = None

        lines = diff_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("--- "):
                if current_file:
                    files.append(current_file)
                current_file = {"old_file": line[4:].strip(), "new_file": "", "hunks": []}
            elif line.startswith("+++ "):
                if current_file:
                    current_file["new_file"] = line[4:].strip()
            elif line.startswith("@@ "):
                m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if m and current_file:
                    old_start = int(m.group(1))
                    new_start = int(m.group(2))
                    current_hunk = {"old_start": old_start, "new_start": new_start, "lines": []}
                    current_file["hunks"].append(current_hunk)
            else:
                if current_hunk is not None:
                    if line.startswith(" ") or line.startswith("+") or line.startswith("-"):
                        current_hunk["lines"].append(line)
                    elif line == "\\ No newline at end of file":
                        pass
                    else:
                        if line == "":
                            current_hunk["lines"].append(" ")
            i += 1

        if current_file:
            files.append(current_file)

        return files

    def _apply_hunk(self, lines: List[str], hunk: Dict[str, Any]) -> Tuple[bool, List[str], str]:
        old_start = hunk["old_start"] - 1
        hunk_old_lines = []
        hunk_new_lines = []
        for hline in hunk["lines"]:
            if hline.startswith(" "):
                hunk_old_lines.append(hline[1:])
                hunk_new_lines.append(hline[1:])
            elif hline.startswith("-"):
                hunk_old_lines.append(hline[1:])
            elif hline.startswith("+"):
                hunk_new_lines.append(hline[1:])

        if old_start < 0:
            old_start = 0

        match_idx = -1
        search_range = range(max(0, old_start - 50), min(len(lines), old_start + 50))
        for idx in search_range:
            if idx + len(hunk_old_lines) <= len(lines):
                if lines[idx:idx + len(hunk_old_lines)] == hunk_old_lines:
                    match_idx = idx
                    break

        if match_idx == -1:
            if not lines and not hunk_old_lines:
                match_idx = 0
            else:
                return False, lines, f"Context mismatch for hunk at line {old_start+1}"

        new_lines = lines[:match_idx] + hunk_new_lines + lines[match_idx + len(hunk_old_lines):]
        return True, new_lines, ""

    # -------------------------------------------------------------
    # PRIMARY ATOMIC PATCH ENTRY POINT
    # -------------------------------------------------------------

    def apply_patch(
        self,
        patch_text: str,
        dry_run: bool = False,
        expected_hashes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Validates and applies patch (SEARCH/REPLACE or unified diff) atomically.
        Guarantees:
        - Rejects unparseable syntax, ambiguous matches, and traversal/symlinks.
        - If expected_hashes is given, verifies disk state before writing.
        - If any error occurs, 0 files are written to disk.
        """
        result = {
            "success": False,
            "modified_files": [],
            "source_file_hashes": {},
            "errors": [],
            "dry_run": dry_run,
            "format": "unknown"
        }

        if not patch_text or not patch_text.strip():
            result["errors"].append("EmptyPatch: No patch content provided.")
            return result

        fmt = self.detect_format(patch_text)
        result["format"] = fmt

        # ==========================================
        # ROUTE A: SEARCH / REPLACE
        # ==========================================
        if fmt == "search_replace":
            parse_ok, parsed_files, parse_err = self._parse_search_replace(patch_text)
            if not parse_ok:
                result["errors"].append(parse_err)
                return result

            # Validation stage (100% in-memory)
            file_modifications = []  # (abs_path, rel_path, new_content, original_hash)
            for f_entry in parsed_files:
                rel_path = f_entry["file"]
                if not self._is_safe_path(rel_path):
                    result["errors"].append(f"SecurityViolation: Invalid or unsafe path '{rel_path}'")
                    return result

                abs_path = os.path.abspath(os.path.join(self.repo_root, rel_path))

                # Expected hash check
                if expected_hashes and rel_path in expected_hashes:
                    if os.path.exists(abs_path):
                        with open(abs_path, "rb") as check_f:
                            curr_h = hashlib.sha256(check_f.read()).hexdigest()
                        if curr_h != expected_hashes[rel_path]:
                            result["errors"].append(
                                f"StaleSourceError: File '{rel_path}' was modified on disk after proposal. "
                                f"Expected {expected_hashes[rel_path][:8]}, got {curr_h[:8]}."
                            )
                            return result

                ok, new_content, orig_hash, err = self._apply_search_replace_file(rel_path, f_entry["blocks"])
                if not ok:
                    result["errors"].append(err)
                    return result

                result["source_file_hashes"][rel_path] = orig_hash
                file_modifications.append((abs_path, rel_path, new_content, orig_hash))

            # Application stage (Only executed if all validations succeeded)
            if not dry_run:
                # Second verification of disk hashes immediately before writing (race protection)
                for abs_path, rel_path, _, orig_hash in file_modifications:
                    if os.path.exists(abs_path) and orig_hash:
                        with open(abs_path, "rb") as check_f:
                            disk_hash = hashlib.sha256(check_f.read()).hexdigest()
                        if disk_hash != orig_hash:
                            result["errors"].append(f"StaleSourceError: File '{rel_path}' changed immediately prior to write.")
                            return result

                for abs_path, rel_path, new_content, _ in file_modifications:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8", newline="") as out_f:
                        out_f.write(new_content)
                    result["modified_files"].append(rel_path)
            else:
                for _, rel_path, _, _ in file_modifications:
                    result["modified_files"].append(rel_path)

            result["success"] = True
            return result

        # ==========================================
        # ROUTE B: UNIFIED DIFF
        # ==========================================
        elif fmt == "unified_diff":
            try:
                files = self._parse_diff(patch_text)
            except Exception as e:
                result["errors"].append(f"Malformed diff syntax: {str(e)}")
                return result

            if not files:
                result["errors"].append("No valid files found in unified diff.")
                return result

            file_modifications = []
            for f in files:
                old_file = f["old_file"]
                new_file = f["new_file"]
                if old_file.startswith("a/"): old_file = old_file[2:]
                if new_file.startswith("b/"): new_file = new_file[2:]

                target_file = new_file or old_file
                if not self._is_safe_path(target_file):
                    result["errors"].append(f"SecurityViolation: Invalid or unsafe path '{target_file}'")
                    return result

                abs_path = os.path.abspath(os.path.join(self.repo_root, target_file))

                # Expected hash check
                if expected_hashes and target_file in expected_hashes:
                    if os.path.exists(abs_path):
                        with open(abs_path, "rb") as check_f:
                            curr_h = hashlib.sha256(check_f.read()).hexdigest()
                        if curr_h != expected_hashes[target_file]:
                            result["errors"].append(
                                f"StaleSourceError: File '{target_file}' was modified on disk after proposal."
                            )
                            return result

                lines = []
                orig_hash = ""
                if os.path.exists(abs_path):
                    with open(abs_path, "rb") as check_f:
                        orig_bytes = check_f.read()
                    orig_hash = hashlib.sha256(orig_bytes).hexdigest()
                    lines = orig_bytes.decode("utf-8", errors="replace").splitlines()
                elif old_file != "/dev/null" and f.get("hunks") and any(hline.startswith("-") for hline in f["hunks"][0].get("lines", [])):
                    result["errors"].append(f"FileNotFound: Cannot patch missing file '{target_file}'")
                    return result

                if not f.get("hunks"):
                    result["errors"].append(f"MalformedDiff: No valid hunks found for '{target_file}'")
                    return result

                current_lines = list(lines)
                for hunk in f["hunks"]:
                    success, current_lines, err = self._apply_hunk(current_lines, hunk)
                    if not success:
                        result["errors"].append(f"HunkApplicationFailed in '{target_file}': {err}")
                        return result

                result["source_file_hashes"][target_file] = orig_hash
                file_modifications.append((abs_path, target_file, "\n".join(current_lines) + "\n", orig_hash))

            if not dry_run:
                for abs_path, rel_path, new_content, _ in file_modifications:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8", newline="") as out_f:
                        out_f.write(new_content)
                    result["modified_files"].append(rel_path)
            else:
                for _, rel_path, _, _ in file_modifications:
                    result["modified_files"].append(rel_path)

            result["success"] = True
            return result

        else:
            result["errors"].append("UnrecognizedPatchFormat: Patch is neither a recognized SEARCH/REPLACE block nor a unified diff.")
            return result
