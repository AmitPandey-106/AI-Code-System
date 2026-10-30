import os
from eval_dataset_v2.tasks import ALL_TASKS
from eval_dataset_v2.eval_runner import run_task, CONFIGURATIONS

task = ALL_TASKS[0]
res = run_task(task, CONFIGURATIONS["CONFIG_D"]["flags"])
print("Task 01 under CONFIG_D:")
print("State:", res["state"])
print("Passed:", res["acceptance_passed"])
print("Attempts:", res["attempts"])
print("Native Syntax OK:", res["native_syntax_ok"])
print("Fallback Used:", res["fallback_used"])
print("Failure Category:", res["failure_category"])
print("Oracle stdout:")
print(res["oracle_details"]["stdout"])
