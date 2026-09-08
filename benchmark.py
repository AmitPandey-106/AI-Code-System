import json
import requests
import time


# =========================================================
# LOAD TASKS
# =========================================================

with open("data/benchmark_tasks.json", "r") as f:

    tasks = json.load(f)


# =========================================================
# METRICS
# =========================================================

total_tasks = len(tasks)

success_count = 0

repair_used_count = 0

attempts_total = 0

results = []


# =========================================================
# RUN BENCHMARK
# =========================================================

for index, task in enumerate(tasks):

    prompt = task["prompt"]

    print("\n======================================")
    print(f"TASK {index + 1}/{total_tasks}")
    print(f"Prompt: {prompt}")
    print("======================================")

    start_time = time.time()

    try:

        response = requests.post(
            "http://127.0.0.1:8000/generate",
            json={
                "prompt": prompt
            }
        )

        data = response.json()

        elapsed = round(
            time.time() - start_time,
            2
        )

        success = data.get("success", False)

        attempts_used = data.get(
            "attempts_used",
            1
        )

        # =============================================
        # METRICS
        # =============================================

        if success:
            success_count += 1

        if attempts_used > 1:
            repair_used_count += 1

        attempts_total += attempts_used

        # =============================================
        # STORE RESULT
        # =============================================

        result = {
            "prompt": prompt,
            "success": success,
            "attempts_used": attempts_used,
            "time_seconds": elapsed
        }

        results.append(result)

        # =============================================
        # PRINT RESULT
        # =============================================

        print(f"Success: {success}")

        print(f"Attempts Used: {attempts_used}")

        print(f"Time: {elapsed}s")

    except Exception as e:

        print("Benchmark Error:", e)


# =========================================================
# FINAL METRICS
# =========================================================

success_rate = round(
    (success_count / total_tasks) * 100,
    2
)

average_attempts = round(
    attempts_total / total_tasks,
    2
)

repair_rate = round(
    (repair_used_count / total_tasks) * 100,
    2
)

print("\n======================================")
print("FINAL BENCHMARK RESULTS")
print("======================================")

print(f"Total Tasks: {total_tasks}")

print(f"Success Count: {success_count}")

print(f"Success Rate: {success_rate}%")

print(f"Average Attempts: {average_attempts}")

print(f"Repair Usage Rate: {repair_rate}%")

# =========================================================
# SAVE RESULTS
# =========================================================

with open("data/benchmark_results.json", "w") as f:

    json.dump(
        results,
        f,
        indent=4
    )

print("\nBenchmark results saved ✅")