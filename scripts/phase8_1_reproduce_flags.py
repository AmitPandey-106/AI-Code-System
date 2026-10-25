"""Reproduce starting-tree flag behavior in a disposable export, not historical files."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
START = "e46b2f1d36beac4f46abd09d6d75ce7bfea7f449"
CHILD = '''import json, pathlib, os
from app.engineering_loop import EngineeringSession
from app.repair_memory import RepairMemory
from app.strategy_selector import StrategySelector
from app.config import config
import app.engineering_loop as loop
repo=pathlib.Path("fixture"); repo.mkdir()
(repo/"mod.py").write_text("def f():\\n    return 0\\n")
(repo/"test_mod.py").write_text("from mod import f\\ndef test_f(): assert f() == 1\\n")
loop.generate_raw=lambda prompt: "FILE: mod.py\\n<<<<<<< SEARCH\\nreturn 0\\n=======\\nreturn 1\\n>>>>>>> REPLACE\\n"
session=EngineeringSession("Fix f",str(repo),"pytest test_mod.py",repo_index_enabled=False,
    memory_enabled=True,strategy_enabled=True,storage_dir="state")
session.step(); session.approve(); session.step()
print("REPRO_RESULT="+json.dumps({"state":session.state,"test_results":session.current_test_results,
    "memory_requested":session.memory_enabled,"strategy_requested":session.strategy_enabled,
    "memory_default_effective":RepairMemory(storage_dir="state").is_enabled(),
    "strategy_default_effective":StrategySelector(storage_dir="state").is_enabled(),
    "starting_config_memory":config.get("MEMORY_ENABLED"),
    "starting_config_strategy":config.get("STRATEGY_LEARNING_ENABLED"),
    "persisted_files":sorted(p.name for p in pathlib.Path("state").glob("*") if p.is_file())}))
'''


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="phase8-1-starting-repro-") as temp:
        target = Path(temp)
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", START, "app", "config.json"], cwd=ROOT, text=True).splitlines()
        for name in names:
            if name == "config.json" or name.endswith(".py"):
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(subprocess.check_output(["git", "show", f"{START}:{name}"], cwd=ROOT))
        (target / "repro.py").write_text(CHILD, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("LITECODER_")}
        env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONPATH=temp)
        process = subprocess.run([sys.executable, str(target / "repro.py")], cwd=temp, env=env,
                                 capture_output=True, text=True, timeout=90)
        records = [line.partition("REPRO_RESULT=")[2] for line in process.stdout.splitlines() if "REPRO_RESULT=" in line]
        result = json.loads(records[-1]) if records and process.returncode == 0 else {
            "status": "FAIL", "stdout": process.stdout[-5000:], "stderr": process.stderr[-5000:]}
        result["source_commit"] = START
        result["scope"] = "original app and config exported byte-for-byte into a temporary directory; fake model, real native test"
        (ROOT / "eval_results_phase8_1/starting_flag_reproduction.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
