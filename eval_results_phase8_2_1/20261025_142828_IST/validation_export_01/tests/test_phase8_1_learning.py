import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import app.engineering_loop as loop
import app.repair_memory as memory
from app.strategy_selector import StrategySelector
from test_phase8_1_patches import patch


class DeterministicEmbedding:
    def get_sentence_embedding_dimension(self):
        return 32

    def encode(self, texts, normalize_embeddings=True):
        vectors = np.array([[b / 255 for b in hashlib.sha256(t.encode()).digest()] for t in texts], dtype="float32")
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


@pytest.fixture(autouse=True)
def fake_embedding(monkeypatch):
    monkeypatch.setattr(memory, "get_embedding_model", lambda: DeterministicEmbedding())


def make_session(tmp_path, **kwargs):
    return loop.EngineeringSession("Fix f", str(tmp_path), "pytest test_mod.py", repo_index_enabled=False,
                                  storage_dir=str(tmp_path / "state"), **kwargs)


def test_verified_repair_persists_and_is_retrieved_in_later_session(tmp_path, monkeypatch):
    (tmp_path / "mod.py").write_text("def f():\n    return 0\n")
    (tmp_path / "test_mod.py").write_text("from mod import f\ndef test_f():\n    assert f() == 1\n")
    prompts = []
    def generate(prompt):
        prompts.append(prompt)
        return patch()
    monkeypatch.setattr(loop, "generate_raw", generate)
    s = make_session(tmp_path, memory_enabled=True, strategy_enabled=True)
    assert s.step() == loop.S.AWAITING_APPROVAL
    assert "SELECTED REPAIR STRATEGY" in prompts[0]
    assert s.strategy_decision["reason"]
    assert s.approve(s.current_patch_hash)
    assert s.step() == loop.S.COMPLETED, s.get_status()
    documents = json.loads((Path(s.storage_dir) / "repair_memory.json").read_text())
    assert len(documents) == 1
    assert documents[0]["metadata"]["session_id"] == s.session_id
    assert "return 0" in documents[0]["broken_code"]
    assert documents[0]["verification"]["independent_verification_passed"]
    selector = StrategySelector(s.storage_dir, enabled=True)
    assert selector.stats[s.selected_strategy]["test_failure"]["successes"] == 1
    later = make_session(tmp_path, memory_enabled=True, strategy_enabled=True)
    later.step()
    assert later.memory_retrieved_count == 1
    assert "SIMILAR VERIFIED REPAIR EXPERIENCE" in prompts[-1]
    other = make_session(tmp_path, memory_enabled=True, strategy_enabled=False)
    assert other.storage_dir != later.storage_dir
    assert not memory.RepairMemory(other.storage_dir, enabled=True).memories


def test_disabled_and_explicit_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("LITECODER_MEMORY_ENABLED", "true")
    monkeypatch.setenv("LITECODER_STRATEGY_ENABLED", "true")
    s = make_session(tmp_path, memory_enabled=False, strategy_enabled=False)
    assert not s.memory_enabled and not s.strategy_enabled
    disabled = memory.RepairMemory(str(tmp_path / "disabled"), enabled=False)
    assert not disabled.search_similar_experiences("f", "error", "", "")
    assert disabled.memories == []
    assert not (tmp_path / "disabled").exists()
    monkeypatch.setenv("LITECODER_STRATEGY_ENABLED", "false")
    assert not StrategySelector(str(tmp_path / "other")).is_enabled()


@pytest.mark.parametrize("verification", [{}, {"passed": False}, {"passed": True, "native_tests_passed": False}, {"passed": True, "status": "failed"}])
def test_both_ingestion_entrypoints_reject_unverified(tmp_path, verification):
    mem = memory.RepairMemory(str(tmp_path), enabled=True)
    args = dict(task="f", error_type="AssertionError", error_message="failed", broken_code="return 0",
                successful_fix="return 1", tests="pytest", verification=verification, repair_attempts=1)
    assert not mem.add_verified_experience(**args)
    assert not mem.add_repair_experience(**args)
    assert not (tmp_path / "repair_memory.json").exists()


@pytest.mark.parametrize("data", ["", "{bad", "{}", "[3]", '[{"verification":{"passed":false}}]'])
def test_corrupt_and_incompatible_memory_is_safe(tmp_path, data):
    (tmp_path / "repair_memory.json").write_text(data)
    mem = memory.RepairMemory(str(tmp_path), enabled=True)
    assert not mem.memories
    assert mem.warnings


def test_strategy_corruption_reload_and_invalid_outcome(tmp_path):
    (tmp_path / "strategy_stats.json").write_text('["bad schema"]')
    selector = StrategySelector(str(tmp_path), enabled=True)
    assert selector.stats == {} and selector.warnings
    args = dict(strategy_id="DIRECT_REPAIR", error_type="AssertionError", task="f", attempt_number=1,
                success=True, tests_passed=False, execution_passed=True, duration_ms=1,
                feedback_id="test", security_violation=False, timeout=False)
    assert not selector.record_outcome(**args)
    args["tests_passed"] = True
    assert selector.record_outcome(**args)
    assert not selector.record_outcome(**args)
    assert StrategySelector(str(tmp_path), enabled=True).stats["DIRECT_REPAIR"]["AssertionError"]["successes"] == 1


def test_failed_independent_verification_never_enters_memory(tmp_path, monkeypatch):
    (tmp_path / "mod.py").write_text("def f():\n    return 0\n")
    (tmp_path / "test_mod.py").write_text("def test_ok(): assert True\n")
    monkeypatch.setattr(loop, "generate_raw", lambda p: patch())
    s = make_session(tmp_path, memory_enabled=True, strategy_enabled=True, max_attempts=1,
                     verifier=lambda s: {"success": False, "status": "oracle_failed", "output": "independent mismatch"})
    s.step(); assert s.approve()
    assert s.step() == loop.S.FAILED
    assert not (Path(s.storage_dir) / "repair_memory.json").exists()
    assert (tmp_path / "mod.py").read_text().endswith("return 0\n")


def test_concurrent_learning_writes_are_not_lost(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    def write(i):
        mem = memory.RepairMemory(str(tmp_path), enabled=True)
        assert mem.add_verified_experience(task=f"task {i}", error_type="AssertionError", error_message="failure",
            broken_code="return 0", successful_fix=f"return {i}", tests="pytest", verification={"passed": True}, repair_attempts=1)
        selector = StrategySelector(str(tmp_path), enabled=True)
        assert selector.record_outcome("DIRECT_REPAIR", "AssertionError", f"task {i}", 1, True, True, True, 1,
                                       f"feedback-{i}", False, False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, [1, 2]))
    assert len(memory.RepairMemory(str(tmp_path), enabled=True).memories) == 2
    assert StrategySelector(str(tmp_path), enabled=True).stats["DIRECT_REPAIR"]["AssertionError"]["successes"] == 2
