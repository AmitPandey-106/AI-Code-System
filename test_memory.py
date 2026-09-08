import sys
from app.repair_memory import repair_memory

print("Initializing...")
print(repair_memory.get_memory_stats())

success = repair_memory.add_repair_experience(
    task="Write a function to add two numbers",
    error_type="TypeError",
    error_message="unsupported operand type(s) for +: 'int' and 'str'",
    broken_code="def add(a, b):\n    return a + str(b)",
    successful_fix="def add(a, b):\n    return a + b",
    tests="assert add(1, 2) == 3",
    verification={"tests_passed": True},
    repair_attempts=1
)
print("Add success:", success)

results = repair_memory.search_similar_experiences(
    task="Write a function to add two numbers",
    error_type="TypeError",
    error_message="unsupported operand type(s) for +: 'int' and 'str'",
    broken_code="def add(a, b):\n    return a + '2'"
)

print("Search results:")
for r in results:
    print(r['similarity'], r['memory']['successful_fix'])
