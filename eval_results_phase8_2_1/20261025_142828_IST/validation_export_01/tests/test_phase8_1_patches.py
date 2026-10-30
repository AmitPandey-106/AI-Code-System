import hashlib
import pytest
from app.engineering_loop import EngineeringSession
from app.patch_engine import PatchEngine
from app.repo_index import RepoIndexer


def patch(rel="mod.py", old="return 0", new="return 1"):
    return f"FILE: {rel}\n<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE\n"


def test_fallback_contract_and_decorator_removal(tmp_path):
    (tmp_path / "mod.py").write_text("@old_decorator\ndef f():\n    return 0\n")
    s = EngineeringSession("fix f", str(tmp_path), "pytest", fallback_enabled=True)
    candidate = s._synthesize_single_function_fallback("Here:\n```python\ndef f():\n    return 1\n```\nDone.")
    assert "@old_decorator" in candidate
    assert PatchEngine(str(tmp_path)).apply_patch(candidate, dry_run=True)["success"]
    for text in ["```python\ndef f(): pass\n```\n```python\ndef f(): return 1\n```",
                 "import os\ndef f(): pass", "print('side effect')\ndef f(): pass",
                 "def f():\n    def nested(): pass\n    return nested()",
                 "class C:\n    def f(self): pass"]:
        assert not s._synthesize_single_function_fallback(text)
        assert s.fallback_rejected_reason


@pytest.mark.parametrize("rel", ["../outside.py", "nested/../../outside.py", "C:\\evil.py",
                                     "mod.py:stream", ".git/config", "CON.py"])
def test_platform_independent_path_rejections(tmp_path, rel):
    assert not PatchEngine(str(tmp_path)).apply_patch(patch(rel), dry_run=True)["success"]


def test_syntax_stale_creation_and_crlf_preservation(tmp_path):
    p = tmp_path / "mod.py"
    original = b"def f():\r\n    return 0\r\n"
    p.write_bytes(original)
    engine = PatchEngine(str(tmp_path))
    assert not engine.apply_patch(patch(new="return ("), dry_run=True)["success"]
    proposal = engine.apply_patch(patch(), dry_run=True)
    assert proposal["success"]
    p.unlink()
    assert not engine.apply_patch(patch(), expected_hashes=proposal["source_file_hashes"])["success"]
    p.write_bytes(original)
    assert engine.apply_patch(patch(), expected_hashes=proposal["source_file_hashes"])["success"]
    assert p.read_bytes() == original.replace(b"return 0", b"return 1")
    creation = patch("new.py", "", "VALUE = 1")
    check = engine.apply_patch(creation, dry_run=True)
    (tmp_path / "new.py").write_bytes(b"# external work\n")
    assert not engine.apply_patch(creation, expected_hashes=check["source_file_hashes"])["success"]
    assert (tmp_path / "new.py").read_bytes() == b"# external work\n"


def test_repository_index_isolation_and_live_boundaries(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    (a / "mod.py").write_text("@decorate\ndef alpha():\n    return 1\n")
    (b / "mod.py").write_text("def beta():\n    return 2\n")
    ia = RepoIndexer(str(a), str(tmp_path / "index"))
    ib = RepoIndexer(str(b), str(tmp_path / "index"))
    assert ia.index_dir != ib.index_dir
    ia.scan_and_index(semantic=False); ib.scan_and_index(semantic=False)
    result = ia.search("alpha")[0]
    assert result["line_start"] == 1 and result["line_end"] == 3
    assert result["snippet"].startswith("@decorate")
    assert not ib.search("alpha")
    (a / "mod.py").write_text("# changed\n")
    assert not ia.search("alpha")
