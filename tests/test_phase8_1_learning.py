import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import app.engineering_loop as loop
import app.repair_memory as memory
from app.strategy_selector import StrategySelector
from test_phase8_1_patches import patch


LEGACY_VERIFICATION = {"syntax_passed": True, "safety_passed": True,
                       "execution_passed": True, "tests_passed": True}
ENGINEERING_VERIFICATION = {"passed": True, "native_tests_passed": True,
                            "independent_verification_passed": True}


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
    assert documents[0]["metadata"]["source_hashes"] == s.source_file_hashes
    assert documents[0]["metadata"]["patch_hash"] == s.current_patch_hash
    assert documents[0]["verification"] == ENGINEERING_VERIFICATION
    assert documents[0]["successful_fix"] == s.current_diff
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
            broken_code="return 0", successful_fix=f"return {i}", tests="pytest",
            verification=dict(ENGINEERING_VERIFICATION), repair_attempts=1)
        selector = StrategySelector(str(tmp_path), enabled=True)
        assert selector.record_outcome("DIRECT_REPAIR", "AssertionError", f"task {i}", 1, True, True, True, 1,
                                       f"feedback-{i}", False, False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, [1, 2]))
    assert len(memory.RepairMemory(str(tmp_path), enabled=True).memories) == 2
    assert StrategySelector(str(tmp_path), enabled=True).stats["DIRECT_REPAIR"]["AssertionError"]["successes"] == 2


@pytest.mark.parametrize("predicate,verification,expected", [
    pytest.param("memory", LEGACY_VERIFICATION, True, id="complete-legacy"),
    pytest.param("memory", ENGINEERING_VERIFICATION, True, id="complete-engineering"),
    pytest.param("memory", {"passed": True, "tests_passed": False}, False, id="contradictory"),
    pytest.param("training", ENGINEERING_VERIFICATION, False, id="engineering-patch-is-not-training-code"),
])
def test_verification_schema_probe(predicate, verification, expected):
    # The four observations from the architecture audit, with repaired expectations.
    if predicate == "memory":
        assert memory.verified(verification) is expected
    else:
        from app.training_dataset import validate_training_experience
        assert validate_training_experience(dict(success=True, error_type="AssertionError",
            error_message="failure", broken_code="def f(): return 0", successful_fix=patch(),
            verification=dict(verification))) is expected


def assert_verification_rejected(tmp_path, verification):
    assert memory.verified(verification) is False
    storage = tmp_path / "rejected"
    mem = memory.RepairMemory(str(storage), enabled=True)
    args = dict(task="f", error_type="AssertionError", error_message="failure",
                broken_code="def f(): return 0", successful_fix="def f(): return 1",
                tests="pytest", verification=verification, repair_attempts=1)
    assert mem.add_repair_experience(**args) is False
    assert mem.add_verified_experience(**args) is False
    assert not storage.exists()


@pytest.mark.parametrize("verification", [None, False, 1, "passed", [], {},
    {"status": "success"}, {"success": True}, {"sandboxed_execution": True},
    {"syntax_passed": True, "safety_passed": True, "execution_passed": True,
     "passed": True, "native_tests_passed": True}])
def test_missing_malformed_and_mixed_partial_verification(tmp_path, verification):
    assert_verification_rejected(tmp_path, verification)


@pytest.mark.parametrize("verification", [
    pytest.param({key: True for i, key in enumerate(schema) if mask & (1 << i)},
                 id=f"{name}-{mask}")
    for name, schema in (("legacy", LEGACY_VERIFICATION), ("engineering", ENGINEERING_VERIFICATION))
    for mask in range(1, (1 << len(schema)) - 1)
])
def test_every_incomplete_schema_is_rejected(tmp_path, verification):
    assert_verification_rejected(tmp_path, verification)


@pytest.mark.parametrize("field", ["syntax_passed", "safety_passed", "execution_passed", "tests_passed",
    "passed", "native_tests_passed", "independent_verification_passed", "success", "sandboxed_execution"])
@pytest.mark.parametrize("value", [False, None, 0, 1, "true", "false", [], np.bool_(True)])
def test_explicit_negative_or_non_boolean_verification_is_rejected(tmp_path, field, value):
    # Even a second complete positive schema cannot override a contradictory flag.
    verification = {**LEGACY_VERIFICATION, **ENGINEERING_VERIFICATION,
                    "success": True, "sandboxed_execution": True, field: value}
    assert_verification_rejected(tmp_path, verification)


@pytest.mark.parametrize("schema", [LEGACY_VERIFICATION, ENGINEERING_VERIFICATION], ids=["legacy", "engineering"])
@pytest.mark.parametrize("status", ["cancelled", "canceled", "cancelling", "failed", "error", "timeout",
    "oracle_failed", "pending", "running", "", None, False, 1, [], {}])
def test_unsuccessful_unknown_or_malformed_status_is_rejected(tmp_path, schema, status):
    assert_verification_rejected(tmp_path, {**schema, "status": status})


@pytest.mark.parametrize("schema", [LEGACY_VERIFICATION, ENGINEERING_VERIFICATION], ids=["legacy", "engineering"])
@pytest.mark.parametrize("status", ["success", "passed", "completed", "verified"])
def test_complete_verification_accepts_successful_terminal_status(schema, status):
    assert memory.verified({**schema, "status": status}) is True


@pytest.mark.parametrize("verification", [
    {**LEGACY_VERIFICATION, "sandboxed_execution": True},
    {**LEGACY_VERIFICATION, "passed": True, "success": True},
    {**ENGINEERING_VERIFICATION, "tests_passed": True, "success": True},
    {**ENGINEERING_VERIFICATION, "duration_ms": 5, "detail": "native verification"},
    {**LEGACY_VERIFICATION, **ENGINEERING_VERIFICATION},
])
def test_complete_schema_accepts_positive_supplemental_evidence(verification):
    before = json.dumps(verification, sort_keys=True)
    assert memory.verified(verification) is True
    assert json.dumps(verification, sort_keys=True) == before


@pytest.mark.parametrize("method", ["add_repair_experience", "add_verified_experience"])
@pytest.mark.parametrize("kind", ["legacy", "engineering"])
def test_complete_verification_round_trips_without_schema_conversion(tmp_path, method, kind):
    from app.training_dataset import validate_training_experience
    verification = dict(LEGACY_VERIFICATION if kind == "legacy" else ENGINEERING_VERIFICATION)
    if kind == "legacy":
        verification["sandboxed_execution"] = True
    successful_fix = "def f():\n    return 1\n" if kind == "legacy" else patch()
    metadata = {} if kind == "legacy" else {"session_id": "reviewed-session",
        "source_hashes": {"mod.py": hashlib.sha256(b"def f(): return 0\n").hexdigest()},
        "patch_hash": hashlib.sha256(successful_fix.encode()).hexdigest(), "fallback_used": False}
    before = json.dumps([verification, metadata], sort_keys=True)
    mem = memory.RepairMemory(str(tmp_path), enabled=True)
    assert getattr(mem, method)(task="f", error_type="AssertionError", error_message="failure",
        broken_code="def f(): return 0", successful_fix=successful_fix, tests="pytest",
        verification=verification, repair_attempts=1, metadata=metadata) is True
    raw = (tmp_path / "repair_memory.json").read_bytes()
    record = json.loads(raw)[0]
    assert record["verification"] == verification
    assert record["metadata"] == metadata and record["successful_fix"] == successful_fix
    assert json.dumps([verification, metadata], sort_keys=True) == before
    assert validate_training_experience(record) is (kind == "legacy")
    reloaded = memory.RepairMemory(str(tmp_path), enabled=True)
    assert reloaded.memories == [record]
    found = reloaded.search_similar_experiences("f", "AssertionError", "failure", "def f(): return 0")
    assert found[0]["memory"] == record
    assert (tmp_path / "repair_memory.json").read_bytes() == raw
    assert not (tmp_path / "repair_memory_index.faiss").exists()


def test_loading_does_not_rewrite_existing_valid_or_incomplete_records(tmp_path):
    records = [dict(memory_id=name, task="f", error_type="AssertionError", error_message="failure",
                    broken_code="def f(): return 0", successful_fix=fix, verification=verification,
                    metadata={"original_provenance": name})
               for name, verification, fix in (
                   ("legacy", dict(LEGACY_VERIFICATION), "def f(): return 1"),
                   ("engineering", dict(ENGINEERING_VERIFICATION), patch()),
                   ("incomplete", {"passed": True}, patch()))]
    path = tmp_path / "repair_memory.json"
    raw = json.dumps(records, indent=4).encode()
    path.write_bytes(raw)
    before = path.stat()
    mem = memory.RepairMemory(str(tmp_path), enabled=True)
    assert mem.memories == records[:2]
    assert mem.warnings
    assert mem.search_similar_experiences("f", "AssertionError", "failure", "def f(): return 0")
    after = path.stat()
    assert path.read_bytes() == raw
    assert (after.st_size, after.st_mtime_ns, after.st_mode) == (before.st_size, before.st_mtime_ns, before.st_mode)
    assert not (tmp_path / "repair_memory_index.faiss").exists()
