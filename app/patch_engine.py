import os
import ast
from app.file_transaction import FileTransaction, safe_path, read_bytes, digest
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple

class PatchEngine:
    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    def _is_safe_path(self, path: str) -> bool:
        try:
            safe_path(self.repo_root, path)
            return True
        except (ValueError, OSError):
            return False

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
                current_hunk = None
                current_file = {"old_file": line[4:].strip(), "new_file": "", "hunks": []}
            elif line.startswith("+++ "):
                if current_file:
                    current_file["new_file"] = line[4:].strip()
            elif line.startswith("@@ "):
                m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if m and current_file:
                    old_start = int(m.group(1))
                    new_start = int(m.group(3))
                    current_hunk = {"old_start": old_start, "new_start": new_start, "old_count": int(m.group(2) or 1), "new_count": int(m.group(4) or 1), "lines": []}
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

        if len(hunk_old_lines) != hunk.get("old_count", len(hunk_old_lines)) or len(hunk_new_lines) != hunk.get("new_count", len(hunk_new_lines)):
            return False, lines, "MalformedDiff: hunk line counts do not match header"
        if not hunk_old_lines:
            matches = [min(old_start, len(lines))]
        else:
            matches = [i for i in range(len(lines) - len(hunk_old_lines) + 1)
                       if lines[i:i + len(hunk_old_lines)] == hunk_old_lines]
        if len(matches) != 1:
            return False, lines, "AmbiguousMatchError" if matches else f"Context mismatch for hunk at line {old_start+1}"
        match_idx = matches[0]

        new_lines = lines[:match_idx] + hunk_new_lines + lines[match_idx + len(hunk_old_lines):]
        return True, new_lines, ""

    # -------------------------------------------------------------
    # PRIMARY ATOMIC PATCH ENTRY POINT
    # -------------------------------------------------------------

    def apply_patch(self, patch_text, dry_run=False, expected_hashes=None):
        result = {"success": False, "modified_files": [], "source_file_hashes": {},
                  "errors": [], "dry_run": dry_run, "format": self.detect_format(patch_text or "")}
        tx = None
        try:
            fmt = result["format"]
            if fmt == "search_replace":
                ok, entries, error = self._parse_search_replace(patch_text)
                if not ok:
                    raise ValueError(error)
                targets = [e["file"].replace("\\", "/") for e in entries]
            elif fmt == "unified_diff":
                entries = self._parse_diff(patch_text)
                targets = []
                for entry in entries:
                    old = entry["old_file"].removeprefix("a/")
                    new = entry["new_file"].removeprefix("b/")
                    if not new or new == "/dev/null" or (old != "/dev/null" and old != new):
                        raise ValueError("MalformedDiff: deletion/rename or incomplete header unsupported")
                    targets.append(new.replace("\\", "/"))
            else:
                raise ValueError("UnrecognizedPatchFormat: no recognized patch blocks")
            if not targets:
                raise ValueError("EmptyPatch: no targets")
            canonical_hashes = None if expected_hashes is None else {k.replace("\\", "/"): v for k, v in expected_hashes.items()}
            if canonical_hashes is not None and set(canonical_hashes) != set(targets):
                raise ValueError("StaleSourceError: proposal target set does not match approved snapshot")
            tx = FileTransaction(self.repo_root, targets, canonical_hashes)
            modifications = {}
            for rel, entry in zip(targets, entries):
                original = tx.original[rel]
                if fmt == "search_replace":
                    ok, text, original_hash, error = self._apply_search_replace_file(rel, entry["blocks"])
                    if not ok:
                        raise ValueError(error)
                    if original_hash != digest(original):
                        raise ValueError(f"StaleSourceError: {rel} changed during validation")
                else:
                    if original is None and entry["old_file"] != "/dev/null" and not (entry["hunks"] and all(h["old_count"] == 0 for h in entry["hunks"])):
                        raise ValueError(f"FileNotFound: {rel}")
                    source = (original or b"").decode("utf-8")
                    lines = source.splitlines()
                    if not entry["hunks"]:
                        raise ValueError(f"MalformedDiff: no hunks in {rel}")
                    for hunk in entry["hunks"]:
                        ok, lines, error = self._apply_hunk(lines, hunk)
                        if not ok:
                            raise ValueError(f"HunkApplicationFailed in '{rel}': {error}")
                    newline = "\r\n" if "\r\n" in source else "\n"
                    text = newline.join(lines)
                    if original is None or source.endswith("\n"):
                        text += newline
                if rel.endswith(".py"):
                    compile(text.lstrip("\ufeff"), rel, "exec")
                modifications[rel] = text.encode("utf-8")
                result["source_file_hashes"][rel] = digest(original)
            tx.verify()
            if not dry_run:
                for rel, data in modifications.items():
                    tx.write(rel, data)
            result["created_directories"] = [str(p.relative_to(self.repo_root)) for p in tx.created_dirs]
            result["applied_file_hashes"] = {k: digest(v) for k, v in modifications.items()}
            result["modified_files"] = targets
            result["success"] = True
        except Exception as exc:
            result["errors"].append(f"{type(exc).__name__}: {exc}")
            if tx is not None and not dry_run:
                result["rolled_back"] = tx.rollback()
                result["rollback_errors"] = tx.rollback_errors
                result["errors"].extend(tx.rollback_errors)
        return result
