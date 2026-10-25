"""Package only committed, allowlisted source; never rebuild historical archives."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval_results_phase8_1"
CORE_TESTS = {
    "test_patch_engine.py", "test_patch_engine_search_replace.py", "test_phase7b_patch_reliability.py",
    "test_project_test_runner.py", "test_engineering_loop.py", "test_engineering_loop_safety.py",
    "test_engineering_loop_retries.py", "test_phase8_architecture.py", "test_audit_security_boundaries.py",
    "test_repo_index.py", "test_strategy_bookkeeping.py", "test_strategy_learning.py"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def include(name):
    if name.startswith("app/") and name.endswith(".py"):
        return True
    if name.startswith("eval_dataset_v2/") and name.endswith((".py", ".json", ".md")):
        return True
    if name.startswith("tests/"):
        return Path(name).name in CORE_TESTS or Path(name).name.startswith("test_phase8_1_")
    return name in {"run_frontend.py", "frontend/index.html", "frontend/server.py", "frontend/engineering.js", "train_worker.py",
        "colab_phase8_1/config.json", "colab_phase8_1/run_targeted.py", "requirements-phase8_1.txt",
        "PHASE8_1_EXECUTION_GUIDE.md", "PHASE8_1_ENGINEERING_PLAN.md",
        "scripts/phase8_1_validate.py", "scripts/phase8_1_model_smoke.py",
        "scripts/phase8_1_studio_smoke.py", "scripts/phase8_1_studio_browser.cjs",
        "scripts/build_phase8_1_package.py"}


def build():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit], cwd=ROOT, text=True).splitlines()
    payload = {}
    for name in names:
        if not include(name):
            continue
        data = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
        if re.search(rb"(?:hf_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9_-]{25,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)", data):
            raise ValueError(f"Potential credential in allowlisted source: {name}")
        payload[name] = data
    required = {"app/file_transaction.py", "app/engineering_api.py", "frontend/engineering.js",
                "colab_phase8_1/run_targeted.py", "scripts/phase8_1_validate.py", "requirements-phase8_1.txt"}
    if not required.issubset(payload):
        raise ValueError("Commit the Phase 8.1 source before packaging")
    payload["config.json"] = payload["colab_phase8_1/config.json"]
    manifest = {"source_commit": commit,
        "historical_baseline": "9ef57511e0e25d58d0f1318e9d73ccb58465ec44",
        "dataset_tree": subprocess.check_output(["git", "rev-parse", f"{commit}:eval_dataset_v2"], cwd=ROOT, text=True).strip(),
        "model": "Qwen/Qwen2.5-Coder-1.5B-Instruct", "model_revision": "2e1fd397ee46e1388853d2af2c993145b0f1098a",
        "embedding_model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "files": {name: {"sha256": sha(data), "size": len(data)} for name, data in sorted(payload.items())},
        "manifest_self_hash": "Excluded to avoid circular hashing; external checksum covers the archive."}
    manifest_data = json.dumps(manifest, indent=2).encode()
    payload["PHASE8_1_PACKAGE_MANIFEST.json"] = manifest_data
    OUT.mkdir(exist_ok=True)
    archive = OUT / "LITE_CODER_PHASE8_1_SOURCE.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            package.writestr(info, data)
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        assert set(package.namelist()) == set(payload)
        for name, entry in manifest["files"].items():
            assert sha(package.read(name)) == entry["sha256"]
        assert sha(package.read("PHASE8_1_PACKAGE_MANIFEST.json")) == sha(manifest_data)
    checksum = sha(archive.read_bytes())
    archive.with_suffix(".zip.sha256").write_text(checksum + "  " + archive.name + "\n", encoding="utf-8")
    (OUT / "package_validation.json").write_text(json.dumps({"status": "PASS", "source_commit": commit,
        "archive": archive.name, "sha256": checksum, "manifest_sha256": sha(manifest_data),
        "file_count": len(payload), "checks": ["all member hashes", "CRC", "exact allowlist",
        "no manifest self-reference", "credential pattern scan", "committed source only"]}, indent=2), encoding="utf-8")
    print(json.dumps({"archive": str(archive), "sha256": checksum, "file_count": len(payload), "source_commit": commit}, indent=2))


if __name__ == "__main__":
    build()
