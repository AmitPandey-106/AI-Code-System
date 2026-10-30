import os
import sys
import tempfile
from eval_dataset_v2.tasks import ALL_TASKS
from app.engineering_loop import EngineeringSession
from app.repo_index import get_repo_indexer
from app.model import generate_raw, get_current_model_name

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
    # Let's inspect context and prompt
    context_str = ""
    res = indexer.search(task.prompt, top_k=3)
    for r in res:
        print(f"Index result: {r['rel_path']}")
    
    # Run _do_planning
    plan, patch = session._do_planning()
    print("--- RAW PLAN/RESPONSE ---")
    print(plan)
    print("--- EXTRACTED PATCH ---")
    print(repr(patch))
