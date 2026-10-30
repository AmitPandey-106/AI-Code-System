"""Fixed model-free child for control tests. Never imports experiment/model code."""
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase8_2_1_controls import WritePolicy

if sys.argv[1] == "ready":
    print("READY", flush=True)
    time.sleep(30)
elif sys.argv[1] == "policy":
    workspace, protected, other, evidence = map(Path, sys.argv[2:6])
    policy = WritePolicy(workspace, evidence, workspace / "fixture")
    sys.addaudithook(policy.audit)
    outcomes = {}
    for name, path in (("protected", protected / "x.txt"), ("other", other / "x.txt"),
                       ("fixture_before_review", workspace / "fixture/micro_http/router.py"),
                       ("evidence_overwrite", evidence / "existing.json")):
        try:
            path.write_text("forbidden", encoding="utf-8")
            outcomes[name] = "WRITTEN"
        except (PermissionError, ValueError):
            outcomes[name] = "rejected"
    (workspace / "own.txt").write_text("allowed", encoding="utf-8")
    with (evidence / "new.json").open("x") as stream:
        stream.write("{}")
    print(json.dumps(outcomes))
