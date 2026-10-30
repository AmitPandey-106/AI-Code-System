import hashlib
from pathlib import Path
import app.engineering_loop as loop
from app.multi_file_orchestrator import MultiFileEngineeringOrchestrator
from test_phase8_1_patches import patch


def setup_repo(tmp_path):
    (tmp_path / "a.py").write_bytes(b"VALUE = 0\r\n")
    (tmp_path / "b.py").write_bytes(b"from a import VALUE\nOTHER = 0\n")
    (tmp_path / "test_all.py").write_text("from a import VALUE\nfrom b import OTHER\ndef test_all():\n    assert VALUE == 1 and OTHER == 2\n")


def orchestrator(tmp_path, **options):
    return MultiFileEngineeringOrchestrator(str(tmp_path), "pytest test_all.py", repo_index_enabled=False,
            memory_enabled=False, strategy_enabled=False, **options)


def test_sequential_dependency_order_approval_and_full_verification(tmp_path, monkeypatch):
    setup_repo(tmp_path)
    approvals = []
    def approve(status):
        approvals.append(status["current_patch_hash"])
        return True
    def generate(prompt):
        if "TARGET FILE TO EDIT: a.py" in prompt:
            return patch("a.py", "VALUE = 0", "VALUE = 1")
        assert (tmp_path / "a.py").read_bytes() == b"VALUE = 1\r\n"
        return patch("b.py", "OTHER = 0", "OTHER = 2")
    monkeypatch.setattr(loop, "generate_raw", generate)
    result = orchestrator(tmp_path, approval_callback=approve).execute_plan("update", ["b.py", "a.py"])
    assert result.success, result.to_dict()
    assert result.completed_files == ["a.py", "b.py"]
    assert len(approvals) == 2
    assert result.evidence["test_results"]["success"]
    assert result.evidence["verification_results"]["success"]
    assert "+VALUE = 1" in result.evidence["final_diff"]


def test_later_model_failure_rolls_back_actual_first_mutation(tmp_path, monkeypatch):
    setup_repo(tmp_path)
    originals = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    observed = []
    def generate(prompt):
        if "TARGET FILE TO EDIT: a.py" in prompt:
            return patch("a.py", "VALUE = 0", "VALUE = 1")
        observed.append((tmp_path / "a.py").read_bytes())
        raise RuntimeError("controlled File B generation failure")
    monkeypatch.setattr(loop, "generate_raw", generate)
    result = orchestrator(tmp_path, approval_callback=lambda status: True).execute_plan("update", ["a.py", "b.py"])
    assert observed == [b"VALUE = 1\r\n"]
    assert not result.success and result.rolled_back
    assert result.evidence["mutation_count"] == 1
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == originals
    restored = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.iterdir()}
    assert restored == {name: hashlib.sha256(data).hexdigest() for name, data in originals.items()}
    assert {name: restored[name] for name in ("a.py", "b.py")} == result.evidence["original_hashes"]


def test_unapproved_and_unplanned_edits_cannot_mutate(tmp_path, monkeypatch):
    setup_repo(tmp_path)
    result = orchestrator(tmp_path).execute_plan("update", ["a.py", "b.py"])
    assert not result.success and "ApprovalRequired" in result.error
    monkeypatch.setattr(loop, "generate_raw", lambda p: patch("b.py", "OTHER = 0", "OTHER = 2"))
    result = orchestrator(tmp_path, approval_callback=lambda status: True).execute_plan("update", ["a.py"])
    assert not result.success and not result.completed_files
    assert "unplanned target" in result.error
    result = orchestrator(tmp_path, approval_callback=lambda status: True).execute_plan("update", ["../evil.py"])
    assert not result.success and "SecurityViolation" in result.error
