import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import app.engineering_api as api
import app.engineering_loop as loop
from test_phase8_1_patches import patch


@pytest.fixture
def client(monkeypatch):
    manager = loop.SessionManager()
    monkeypatch.setattr(api, "engineering_manager", manager)
    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as client:
        yield client, manager
    for s in manager.sessions.values():
        s.cancel()


def wait_status(client, session_id, states):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/engineering/status/{session_id}")
        assert response.status_code == 200
        status = response.json()
        if status["state"] in states:
            return status
        time.sleep(0.02)
    raise AssertionError(status)


def request(tmp_path):
    (tmp_path / "mod.py").write_text("def f():\n    return 0\n")
    (tmp_path / "test_mod.py").write_text("from mod import f\ndef test_f(): assert f() == 1\n")
    return dict(task_prompt="Fix f", repo_root=str(tmp_path), test_command="pytest test_mod.py",
                repo_index_enabled=False, memory_enabled=False, strategy_enabled=False)


def test_start_is_nonblocking_progress_and_cancel_are_isolated(tmp_path, client, monkeypatch):
    http, manager = client
    entered, release = threading.Event(), threading.Event()
    def slow(prompt):
        entered.set()
        assert release.wait(5)
        return patch()
    monkeypatch.setattr(loop, "generate_raw", slow)
    body = request(tmp_path)
    response = http.post("/engineering/start", json=body)
    assert response.status_code == 202
    sid = response.json()["session_id"]
    assert entered.wait(3)
    assert http.get(f"/engineering/status/{sid}").json()["state"] == "generating"
    second = http.post("/engineering/start", json={**body, "test_command": "python evil.py"}).json()
    assert second["session_id"] != sid and second["state"] == "failed"
    assert second["failure_category"] == "policy_rejection"
    response = http.post(f"/engineering/cancel/{sid}")
    assert response.json()["state"] == "cancelling"
    release.set()
    final = wait_status(http, sid, {"cancelled"})
    assert not final["functional_success"]


def test_api_approval_hash_and_completion_evidence(tmp_path, client, monkeypatch):
    http, manager = client
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    sid = http.post("/engineering/start", json=request(tmp_path)).json()["session_id"]
    status = wait_status(http, sid, {"awaiting_approval"})
    assert http.post(f"/engineering/approve/{sid}").status_code == 422
    assert http.post(f"/engineering/approve/{sid}?expected_patch_hash={'0'*64}").status_code == 409
    response = http.post(f"/engineering/approve/{sid}?expected_patch_hash={status['current_patch_hash']}")
    assert response.status_code == 202
    final = wait_status(http, sid, {"completed", "failed"})
    assert final["state"] == "completed", final
    assert final["functional_success"] and final["test_results"]["success"]
    assert final["verification_results"]["success"] and final["current_diff"]
    assert http.post(f"/engineering/reject/{sid}").status_code == 409
    assert http.get("/engineering/status/missing").status_code == 404


def test_rejected_proposal_never_mutates(tmp_path, client, monkeypatch):
    http, manager = client
    monkeypatch.setattr(loop, "generate_raw", lambda prompt: patch())
    body = request(tmp_path)
    original = (tmp_path / "mod.py").read_bytes()
    sid = http.post("/engineering/start", json=body).json()["session_id"]
    wait_status(http, sid, {"awaiting_approval"})
    assert http.post(f"/engineering/reject/{sid}").json()["state"] == "cancelled"
    assert (tmp_path / "mod.py").read_bytes() == original


def test_direct_patch_api_requires_review_hash_and_snapshot(tmp_path):
    from app.main import app
    http = TestClient(app)
    request(tmp_path)
    body = {"repo_root": str(tmp_path), "diff_text": patch()}
    assert http.post("/apply_patch", json=body).status_code == 409
    proposed = http.post("/propose_patch", json=body).json()
    assert proposed["success"]
    (tmp_path / "mod.py").write_text("# external change\ndef f():\n    return 0\n")
    result = http.post("/apply_patch", json={**body, "expected_patch_hash": proposed["patch_hash"],
                        "expected_hashes": proposed["source_file_hashes"]}).json()
    assert not result["success"] and "StaleSourceError" in str(result["errors"])
    assert (tmp_path / "mod.py").read_text().startswith("# external change")


def test_studio_proxy_preserves_get_post_and_query(monkeypatch):
    from frontend import server
    calls = []
    class Backend(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.command, self.path))
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"state":"testing"}')
        do_POST = do_GET
        def log_message(self, *args): pass
    backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), server.ProxyHTTPRequestHandler)
    monkeypatch.setattr(server, "backend_url", f"http://127.0.0.1:{backend.server_port}")
    workers = [threading.Thread(target=s.serve_forever, daemon=True) for s in (backend, proxy)]
    for worker in workers: worker.start()
    try:
        base = f"http://127.0.0.1:{proxy.server_port}/api/engineering/"
        with urllib.request.urlopen(base + "status/id") as response:
            assert json.load(response)["state"] == "testing"
        with urllib.request.urlopen(urllib.request.Request(base + "approve/id?expected_patch_hash=abc", data=b"", method="POST")) as response:
            assert response.status == 200
        assert calls == [("GET", "/engineering/status/id"), ("POST", "/engineering/approve/id?expected_patch_hash=abc")]
    finally:
        for s in (proxy, backend): s.shutdown(); s.server_close()
