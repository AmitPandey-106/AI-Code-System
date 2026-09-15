import os
import json
from benchmark.runner import save_experiment_manifest
from app.config import config

def test_manifest():
    experiment_dir = "experiments/test_manifest_exp"
    if os.path.exists(experiment_dir):
        import shutil
        shutil.rmtree(experiment_dir)
        
    config.set("LORA_ENABLED", True)
    config.set("BENCHMARK_SEED", 999)
    config.set("DIFFICULTY_ALLOCATION_ENABLED", True)
    
    save_experiment_manifest(
        experiment_dir=experiment_dir,
        mode="MODE_TEST",
        dataset_path="dummy_path.json",
        task_count=100,
        dataset_hash="dummy_hash"
    )
    
    manifest_path = os.path.join(experiment_dir, "experiment_manifest.json")
    assert os.path.exists(manifest_path)
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    assert manifest["mode"] == "MODE_TEST"
    assert manifest["dataset_sha256"] == "dummy_hash"
    assert manifest["benchmark_seed"] == 999
    assert manifest["lora_enabled"] is True
    assert manifest["difficulty_allocation_enabled"] is True
    assert manifest["model_name"] == "Qwen/Qwen2.5-Coder-1.5B"
    assert manifest["max_retries"] == 5
    assert "transformers_version" in manifest["hardware"]
    assert "pytorch_version" in manifest["hardware"]
    assert manifest["full_config"]["LORA_ENABLED"] is True
    
    print("MANIFEST TEST PASSED!")

if __name__ == "__main__":
    test_manifest()
