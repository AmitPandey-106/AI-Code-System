"""Local deterministic Studio QA server; never loads an LLM or user repository."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
import threading
from fastapi import FastAPI
import uvicorn
import app.engineering_loop as loop
from app.engineering_api import router
from frontend.server import ProxyHTTPRequestHandler
from frontend import server
from http.server import ThreadingHTTPServer


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="litecoder-studio-qa-") as temp:
        root = Path(temp)
        (root / "mod.py").write_text("def f():\n    return 0\n")
        (root / "test_mod.py").write_text("from mod import f\ndef test_f(): assert f() == 1\n")
        loop.generate_raw = lambda prompt: "FILE: mod.py\n<<<<<<< SEARCH\nreturn 0\n=======\nreturn 1\n>>>>>>> REPLACE\n"
        app = FastAPI()
        app.include_router(router)
        @app.get("/")
        def home():
            return {"message": "Deterministic Studio QA backend"}
        server.backend_url = "http://127.0.0.1:18081"
        config = uvicorn.Config(app, host="127.0.0.1", port=18081, log_level="warning")
        backend = uvicorn.Server(config)
        worker = threading.Thread(target=backend.run, daemon=True)
        worker.start()
        print(f"QA_REPO={temp}", flush=True)
        print("QA_UI=http://127.0.0.1:18501", flush=True)
        with ThreadingHTTPServer(("127.0.0.1", 18501), ProxyHTTPRequestHandler) as proxy:
            try:
                proxy.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                for session in loop.engineering_manager.sessions.values():
                    session.cancel()
                backend.should_exit = True
                worker.join(5)
