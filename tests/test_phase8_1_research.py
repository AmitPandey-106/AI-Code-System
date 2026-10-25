import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
import app.engineering_loop as loop
from app.project_test_runner import ProjectTestRunner
from colab_phase8_1.run_targeted import run_task
from eval_dataset_v2.tasks import TaskSpec
from test_phase8_1_patches import patch


def test_research_default_lists_without_model_calls():
    result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "colab_phase8_1/run_targeted.py")], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["model_calls"] == 0 and len(data["tasks"]) == 20


def test_targeted_research_adapter_uses_real_events_and_oracle(tmp_path, monkeypatch):
    def setup(root):
        (Path(root) / "mod.py").write_text("def f():\n    return 0\n")
        (Path(root) / "test_mod.py").write_text("from mod import f\ndef test_f(): assert f() == 1\n")
    def oracle(root, status):
        result = ProjectTestRunner().run_tests(root, "pytest test_mod.py")
        return {"passed": result["success"], "tests": result}
    task = TaskSpec("deterministic_fixture", "fixture", "fixture", "single_function_bugfix", "fix", "Fix f",
                    "pytest test_mod.py", setup, oracle, ["mod.py"])
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    result = run_task(task, {"memory_enabled": False, "strategy_enabled": False, "fallback_enabled": False},
                      tmp_path / "state", approve=lambda proposal: True)
    assert result["functional_repair"]
    assert result["model_calls"] == 1 and result["attempts"] == 1
    assert result["evidence"]["events"][-1]["to"] == "completed"
    assert result["evidence"]["verification_results"]["passed"]


def test_model_revision_is_forwarded_and_invalidates_cache(monkeypatch):
    import app.model as model
    monkeypatch.setenv("LITECODER_MODEL_REVISION", "revision-one")
    monkeypatch.setattr(model, "_base_model", None)
    monkeypatch.setattr(model, "_tokenizer", None)
    monkeypatch.setattr(model, "_model", None)
    monkeypatch.setitem(__import__("app.config", fromlist=["config"]).config.config, "LORA_ENABLED", False)
    loader = MagicMock(side_effect=[MagicMock(), MagicMock()])
    tokenizer = MagicMock()
    monkeypatch.setattr(model.AutoModelForCausalLM, "from_pretrained", loader)
    monkeypatch.setattr(model.AutoTokenizer, "from_pretrained", tokenizer)
    monkeypatch.setattr(model.torch.cuda, "is_available", lambda: False)
    first, _ = model.get_model()
    assert loader.call_args.kwargs["revision"] == "revision-one"
    assert tokenizer.call_args.kwargs["revision"] == "revision-one"
    assert model.get_model()[0] is first and loader.call_count == 1
    monkeypatch.setenv("LITECODER_MODEL_REVISION", "revision-two")
    model.get_model()
    assert loader.call_count == 2 and loader.call_args.kwargs["revision"] == "revision-two"
