"""One bounded, offline model transport smoke. No repair/benchmark claim."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    if "--child" in sys.argv:
        from app.model import generate_raw, get_current_model_name
        import torch
        import transformers
        started = time.monotonic()
        response = generate_raw("Complete this Python function:\ndef add(a, b):\n    return", max_new_tokens=16)
        print("SMOKE_RESULT=" + json.dumps({"model": get_current_model_name(), "response": response,
            "model_calls": 1, "max_new_tokens": 16, "duration_s": time.monotonic() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "status": "PASS" if response.strip() else "FAIL", "scope": "generation transport only"}), flush=True)
    else:
        from app.process_control import ProcessTree
        output = Path("eval_results_phase8_1/model_smoke.json")
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1")
        started = time.monotonic()
        child = subprocess.Popen([sys.executable, __file__, "--child"], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, env=env, start_new_session=os.name != "nt")
        tree = ProcessTree(child)
        try:
            raw, _ = child.communicate(timeout=90)
            text = raw.decode("utf-8", errors="replace")
            records = [line.split("SMOKE_RESULT=", 1)[1] for line in text.splitlines() if "SMOKE_RESULT=" in line]
            result = json.loads(records[-1]) if records and child.returncode == 0 else {"status": "FAIL", "output": text[-8000:]}
        except subprocess.TimeoutExpired:
            tree.stop()
            raw, _ = child.communicate()
            result = {"status": "BLOCKED", "reason": "Offline CPU smoke exceeded the 90-second limit", "model_calls_limit": 1}
        finally:
            tree.stop()
        result["wall_duration_s"] = time.monotonic() - started
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
