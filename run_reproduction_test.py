import sys
import time
import json
from app.main import plan, generate, PlanRequest, Request
from app.contract import TaskContract
import app.model as model_module
import app.tester as tester_module

prompt = """Implement find_top_students(students, n):
- calculate averages for each student's marks
- ignore empty marks
- sort by average descending
- alphabetical tie-break when averages are equal
- return top n
- output dictionaries containing {name, average}
- round averages to 2 decimals
- if n > valid students, return all valid students
- if n <= 0, return []
- do not mutate the input
- skip invalid student records
- skip nonnumeric marks"""

print("==================================================")
print("STARTING END-TO-END REPRODUCTION TEST")
print("==================================================")

# Count model calls
model_calls = {"generate_plan": 0, "generate_code": 0, "fix_code": 0, "generate_tests_with_llm": 0, "total": 0}

orig_generate_plan = model_module.generate_plan
orig_generate_code = model_module.generate_code
orig_fix_code = model_module.fix_code
orig_generate_tests_with_llm = tester_module.generate_tests_with_llm

def counted_generate_plan(*args, **kwargs):
    model_calls["generate_plan"] += 1
    model_calls["total"] += 1
    return orig_generate_plan(*args, **kwargs)

def counted_generate_code(*args, **kwargs):
    model_calls["generate_code"] += 1
    model_calls["total"] += 1
    return orig_generate_code(*args, **kwargs)

def counted_fix_code(*args, **kwargs):
    model_calls["fix_code"] += 1
    model_calls["total"] += 1
    return orig_fix_code(*args, **kwargs)

def counted_generate_tests_with_llm(*args, **kwargs):
    model_calls["generate_tests_with_llm"] += 1
    model_calls["total"] += 1
    return orig_generate_tests_with_llm(*args, **kwargs)

model_module.generate_plan = counted_generate_plan
model_module.generate_code = counted_generate_code
model_module.fix_code = counted_fix_code
tester_module.generate_tests_with_llm = counted_generate_tests_with_llm

start_time = time.time()

# 1. Step 1: /plan
print("\n--- STEP 1: Calling /plan ---")
t0 = time.time()
plan_req = PlanRequest(prompt=prompt)
plan_res = plan(plan_req)
t_plan = time.time() - t0
print(f"Plan response success: {plan_res.get('success')}")
print(f"Plan entry_point: {plan_res.get('entry_point')}")
print(f"Plan parameters: {plan_res.get('parameters')}")
print(f"Plan time: {t_plan:.2f}s")
print("Generated Plan Preview:\n", plan_res.get("plan")[:300] + "...")

# 2. Step 2: /generate
print("\n--- STEP 2: Calling /generate with approved plan ---")
t1 = time.time()
gen_req = Request(
    prompt=prompt,
    approved_plan=plan_res.get("plan"),
    experiment_id="phase2_repro_test"
)
gen_res = generate(gen_req)
t_gen = time.time() - t1
total_elapsed = time.time() - start_time

print(f"\nGenerate response success: {gen_res.get('success')}")
print(f"Status: {gen_res.get('status')}")
print(f"Attempts count: {gen_res.get('attempts')}")
print(f"Total model calls: {model_calls}")
print(f"Total elapsed time: {total_elapsed:.2f}s (Plan: {t_plan:.2f}s, Generate: {t_gen:.2f}s)")

print("\n--- ATTEMPT HISTORY SUMMARY ---")
history = gen_res.get("attempt_history", [])
for idx, att in enumerate(history):
    print(f"Attempt {idx+1}:")
    print(f"  Attempt number: {att.get('attempt_number')}")
    print(f"  Execution status: {att.get('execution_status')}")
    print(f"  Error type: {att.get('error_type')}")
    print(f"  Test status: {att.get('test_results', {}).get('status')}")
    print(f"  Test failure type: {att.get('test_results', {}).get('failure_type')}")

print("\n--- GENERATED CODE ---")
code = gen_res.get("code")
print(code)

# 3. Step 3: Verify the code with independent ground truth test cases
print("\n--- STEP 3: INDEPENDENT GROUND TRUTH VERIFICATION ---")
test_env = {}
try:
    exec(code, test_env)
    fn = test_env.get("find_top_students")
    if not fn:
        print("FAIL: find_top_students not found in test_env")
    else:
        # Test 1: Tie break Bob < Charlie
        st1 = [
            {"name": "Charlie", "marks": [90, 97]}, # avg = 93.5
            {"name": "Bob", "marks": [93, 94]},     # avg = 93.5
            {"name": "Alice", "marks": [95, 96]}    # avg = 95.5
        ]
        res1 = fn(st1, 3)
        assert res1 == [
            {"name": "Alice", "average": 95.5},
            {"name": "Bob", "average": 93.5},
            {"name": "Charlie", "average": 93.5}
        ], f"Test 1 Failed: {res1}"
        print("Ground Truth Test 1 (Tie-break Bob < Charlie): PASSED")

        # Test 2: n <= 0
        assert fn(st1, 0) == [], f"Test 2 (n=0) Failed: {fn(st1, 0)}"
        assert fn(st1, -1) == [], f"Test 2 (n=-1) Failed: {fn(st1, -1)}"
        print("Ground Truth Test 2 (n <= 0): PASSED")

        # Test 3: n > valid students
        assert len(fn(st1, 10)) == 3, f"Test 3 Failed: {fn(st1, 10)}"
        print("Ground Truth Test 3 (n > valid students): PASSED")

        # Test 4: empty marks, invalid marks, invalid records
        st2 = [
            {"name": "Invalid1"},
            {"name": "Invalid2", "marks": []},
            {"name": "Invalid3", "marks": ["a", "b"]},
            {"name": "Valid", "marks": [10, 20]} # avg = 15.0
        ]
        res4 = fn(st2, 2)
        assert res4 == [{"name": "Valid", "average": 15.0}], f"Test 4 Failed: {res4}"
        print("Ground Truth Test 4 (empty/invalid/nonnumeric): PASSED")

        # Test 5: input mutation check
        st_copy = [{"name": "Bob", "marks": [90, 100]}]
        import copy
        st_before = copy.deepcopy(st_copy)
        fn(st_copy, 1)
        assert st_copy == st_before, "Test 5 Failed: Input was mutated!"
        print("Ground Truth Test 5 (Input mutation): PASSED")

        print("\nALL GROUND TRUTH TESTS PASSED ON CANDIDATE CODE!")
except Exception as e:
    import traceback
    print("Ground Truth Verification Error:")
    traceback.print_exc()

print("\n==================================================")
print("REPRODUCTION TEST EXECUTION FINISHED")
print("==================================================")
