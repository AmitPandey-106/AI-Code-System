import requests
import time
import json

URL = "http://127.0.0.1:8000/generate"

prompts = [
    "Write Python code to add two numbers",
    "Write a function to calculate factorial",
    "Write code to reverse a string",
    "Write a function to check prime number",
    "Write code to find maximum in a list",
    "Write a function to sort a list",
    "Write code to calculate Fibonacci series",
    "Write a function to check palindrome",
    "Write code to count vowels in string",
    "Write a function to merge two lists",
    "Write code to remove duplicates from list",
    "Write a function to find sum of digits",
    "Write code to convert Celsius to Fahrenheit",
    "Write a function to count words in sentence",
    "Write code to find GCD of two numbers",
    "Write a function to generate random numbers",
    "Write code to flatten nested list",
    "Write a function to find second largest number",
    "Write code to check even or odd",
    "Write a function to find square of number",

    # 🔥 HARD PROMPTS
    "Write recursive factorial with user input",
    "Write recursive quicksort implementation",
    "Write binary search using recursion",
    "Write linked list implementation",
    "Write stack class in Python",
    "Write queue implementation",
    "Write DFS traversal",
    "Write BFS traversal",
    "Write Dijkstra algorithm",
    "Write merge sort implementation",
    "Write login authentication system",
    "Write file handling example",
    "Write calculator using class",
    "Write API request using requests library",
    "Write multithreading example",
]

# repeat
prompts = prompts * 5

success = 0
fail = 0

results = []

for i, prompt in enumerate(prompts):

    try:

        response = requests.post(
            URL,
            json={"prompt": prompt}
        )

        data = response.json()

        results.append(data)

        if (
            "execution" in data
            and data["execution"]["success"]
        ):

            success += 1
            print(f"[{i}] ✅ SUCCESS")

        elif (
            "final_execution" in data
            and data["final_execution"]["success"]
        ):

            success += 1
            print(f"[{i}] ✅ FIXED")

        else:

            fail += 1
            print(f"[{i}] ❌ FAIL")

    except Exception as e:

        fail += 1
        print(f"[{i}] ERROR:", str(e))

    time.sleep(0.3)

print("\n====================")
print("Total:", len(prompts))
print("Success:", success)
print("Fail:", fail)

# 🔥 SAVE RESULTS
with open("generation_results.json", "w") as f:
    json.dump(results, f, indent=4)

print("\nSaved results to generation_results.json")