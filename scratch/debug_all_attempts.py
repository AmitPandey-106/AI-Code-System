import os
import sys
import tempfile
from eval_dataset_v2.tasks import ALL_TASKS
from app.engineering_loop import EngineeringSession
from app.repo_index import get_repo_indexer

task = ALL_TASKS[0]
with tempfile.TemporaryDirectory() as td:
    task.setup_fn(td)
    indexer = get_repo_indexer(td)
    indexer.scan_and_index()
    session = EngineeringSession(
        task_prompt=task.prompt,
        repo_root=td,
        test_command=task.test_command,
        fallback_enabled=True,
        prompt_example_enabled=True,
        repo_index_enabled=True
    )
    session.step()
    print("Session state:", session.state)
    print("Total history steps:", len(session.history))
    for i, h in enumerate(session.history):
        print(f"--- Attempt {h.get('attempt')} State: {h.get('state')} ---")
        print("Plan/Response:")
        print(h.get("plan")[:300] if h.get("plan") else "(None)")
        print("Error:")
        print(h.get("error_message") or h.get("last_syntax_error"))
