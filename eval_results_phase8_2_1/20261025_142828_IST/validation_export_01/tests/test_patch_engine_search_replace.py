import os
import tempfile
import pytest
import hashlib
from app.patch_engine import PatchEngine

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        yield td

def test_single_file_search_replace(temp_repo):
    engine = PatchEngine(temp_repo)
    file_path = os.path.join(temp_repo, "calc.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("def add(a, b):\n    return a - b\n")

    patch = """
FILE: calc.py
<<<<<<< SEARCH
    return a - b
=======
    return a + b
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is True
    assert "calc.py" in res["modified_files"]
    assert res["format"] == "search_replace"

    with open(file_path, "r", encoding="utf-8") as f:
        assert f.read() == "def add(a, b):\n    return a + b\n"

def test_missing_search_match_fails(temp_repo):
    engine = PatchEngine(temp_repo)
    file_path = os.path.join(temp_repo, "calc.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("def add(a, b):\n    return a - b\n")

    patch = """
FILE: calc.py
<<<<<<< SEARCH
    return a * b * c
=======
    return a + b
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is False
    assert any("SearchBlockNotFound" in err for err in res["errors"])

    # Verify file was untouched
    with open(file_path, "r", encoding="utf-8") as f:
        assert f.read() == "def add(a, b):\n    return a - b\n"

def test_ambiguous_search_match_fails(temp_repo):
    engine = PatchEngine(temp_repo)
    file_path = os.path.join(temp_repo, "dups.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("VALUE = 1\nVALUE = 1\nVALUE = 2\n")

    patch = """
FILE: dups.py
<<<<<<< SEARCH
VALUE = 1
=======
VALUE = 99
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is False
    assert any("AmbiguousMatchError" in err for err in res["errors"])

    # Verify file was untouched
    with open(file_path, "r", encoding="utf-8") as f:
        assert f.read() == "VALUE = 1\nVALUE = 1\nVALUE = 2\n"

def test_multi_file_and_multi_blocks_search_replace(temp_repo):
    engine = PatchEngine(temp_repo)
    f1 = os.path.join(temp_repo, "module1.py")
    f2 = os.path.join(temp_repo, "module2.py")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("def first():\n    return 1\n\ndef second():\n    return 2\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("CONFIG = False\n")

    patch = """
FILE: module1.py
<<<<<<< SEARCH
def first():
    return 1
=======
def first():
    return 10
>>>>>>> REPLACE
<<<<<<< SEARCH
def second():
    return 2
=======
def second():
    return 20
>>>>>>> REPLACE

FILE: module2.py
<<<<<<< SEARCH
CONFIG = False
=======
CONFIG = True
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is True
    assert set(res["modified_files"]) == {"module1.py", "module2.py"}

    with open(f1, "r", encoding="utf-8") as f:
        assert f.read() == "def first():\n    return 10\n\ndef second():\n    return 20\n"
    with open(f2, "r", encoding="utf-8") as f:
        assert f.read() == "CONFIG = True\n"

def test_rejected_multi_file_leaves_all_files_unchanged(temp_repo):
    engine = PatchEngine(temp_repo)
    f1 = os.path.join(temp_repo, "good.py")
    f2 = os.path.join(temp_repo, "bad.py")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("A = 1\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("B = 2\n")

    patch = """
FILE: good.py
<<<<<<< SEARCH
A = 1
=======
A = 100
>>>>>>> REPLACE

FILE: bad.py
<<<<<<< SEARCH
NON_EXISTENT = 999
=======
B = 200
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is False
    assert any("SearchBlockNotFound" in err for err in res["errors"])

    # Atomic guarantee: good.py must NOT have been modified
    with open(f1, "r", encoding="utf-8") as f:
        assert f.read() == "A = 1\n"
    with open(f2, "r", encoding="utf-8") as f:
        assert f.read() == "B = 2\n"

def test_overlapping_blocks_rejected(temp_repo):
    engine = PatchEngine(temp_repo)
    f1 = os.path.join(temp_repo, "overlap.py")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("line 1\nline 2\nline 3\n")

    patch = """
FILE: overlap.py
<<<<<<< SEARCH
line 1
line 2
=======
line 1 modified
>>>>>>> REPLACE
<<<<<<< SEARCH
line 2
line 3
=======
line 3 modified
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is False
    assert any("OverlappingBlocksError" in err for err in res["errors"])

    with open(f1, "r", encoding="utf-8") as f:
        assert f.read() == "line 1\nline 2\nline 3\n"

def test_malformed_delimiters_rejected(temp_repo):
    engine = PatchEngine(temp_repo)
    patch_missing_replace = """
FILE: calc.py
<<<<<<< SEARCH
line 1
=======
line 2
"""
    res = engine.apply_patch(patch_missing_replace)
    assert res["success"] is False
    assert any("MalformedBlockError" in err for err in res["errors"])

    patch_missing_file_header = """
<<<<<<< SEARCH
line 1
=======
line 2
>>>>>>> REPLACE
"""
    res2 = engine.apply_patch(patch_missing_file_header)
    assert res2["success"] is False
    assert any("MalformedBlockError" in err for err in res2["errors"])

def test_traversal_and_symlink_rejection(temp_repo):
    engine = PatchEngine(temp_repo)

    # Traversal test
    patch_traversal = """
FILE: ../secret.py
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch_traversal)
    assert res["success"] is False
    assert any("SecurityViolation" in err for err in res["errors"])

    # Absolute path test
    patch_abs = """
FILE: /etc/passwd
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE
"""
    res_abs = engine.apply_patch(patch_abs)
    assert res_abs["success"] is False
    assert any("SecurityViolation" in err for err in res_abs["errors"])

def test_crlf_and_trailing_newline_preservation(temp_repo):
    engine = PatchEngine(temp_repo)
    f_crlf = os.path.join(temp_repo, "crlf.py")
    with open(f_crlf, "wb") as f:
        f.write(b"def test():\r\n    return 1\r\n")

    patch = """
FILE: crlf.py
<<<<<<< SEARCH
    return 1
=======
    return 2
>>>>>>> REPLACE
"""
    res = engine.apply_patch(patch, dry_run=False)
    assert res["success"] is True

    with open(f_crlf, "rb") as f:
        raw = f.read()
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert raw == b"def test():\r\n    return 2\r\n"

def test_stale_source_hash_rejection(temp_repo):
    engine = PatchEngine(temp_repo)
    f_path = os.path.join(temp_repo, "stale.py")
    with open(f_path, "w", encoding="utf-8") as f:
        f.write("def run():\n    return 1\n")

    patch = """
FILE: stale.py
<<<<<<< SEARCH
    return 1
=======
    return 2
>>>>>>> REPLACE
"""
    # Dry run records initial hash
    res_dry = engine.apply_patch(patch, dry_run=True)
    assert res_dry["success"] is True
    initial_hash = res_dry["source_file_hashes"]["stale.py"]

    # Modify file on disk to simulate concurrent edit
    with open(f_path, "w", encoding="utf-8") as f:
        f.write("# Modified by user\ndef run():\n    return 1\n")

    # Apply with expected hash from proposal
    res_apply = engine.apply_patch(patch, dry_run=False, expected_hashes={"stale.py": initial_hash})
    assert res_apply["success"] is False
    assert any("StaleSourceError" in err for err in res_apply["errors"])

    # Verify content was NOT overwritten
    with open(f_path, "r", encoding="utf-8") as f:
        assert "# Modified by user" in f.read()
