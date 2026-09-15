from app.repair_difficulty import estimate_difficulty

def test_difficulty():
    print("--- Test 1: Easy Task ---")
    d = estimate_difficulty("SyntaxError", "def a(): pass", 1, True)
    print(f"Score: {d['score']}, Level: {d['difficulty']}, Budget: {d['recommended_attempts']}")
    assert d['difficulty'] == "EASY"

    print("--- Test 2: Medium Task ---")
    d = estimate_difficulty("TypeError", "def a(): pass", 1, True)
    print(f"Score: {d['score']}, Level: {d['difficulty']}, Budget: {d['recommended_attempts']}")
    assert d['difficulty'] == "EASY" # wait, TypeError (2) + 0 + 0 + 0 = 2.0 (EASY)
    
    d2 = estimate_difficulty("TimeoutError", "def a(): pass", 1, True)
    print(f"Score: {d2['score']}, Level: {d2['difficulty']}, Budget: {d2['recommended_attempts']}")
    # Timeout(4) = 4.0 (MEDIUM)

    print("--- Test 3: Hard Task ---")
    d3 = estimate_difficulty("TimeoutError", "def a():\n"*20, 1, False)
    print(f"Score: {d3['score']}, Level: {d3['difficulty']}, Budget: {d3['recommended_attempts']}")
    # Timeout(4) + len>15(1) + no_mem(0.5) = 5.5 (MEDIUM)
    
    d4 = estimate_difficulty("TimeoutError", "def a():\n"*40, 1, False)
    print(f"Score: {d4['score']}, Level: {d4['difficulty']}, Budget: {d4['recommended_attempts']}")
    # Timeout(4) + len>30(2) + no_mem(0.5) = 6.5 (HARD)

    print("--- Test 4 & 5 & 10: Recalculation causing 4 attempts with budget 3 ---")
    code = "x = 1"
    for attempt in range(1, 6):
        d = estimate_difficulty("SyntaxError", code, attempt, True)
        budget = d['recommended_attempts']
        print(f"Attempt {attempt}: Score {d['score']} -> Budget {budget}")
        if attempt >= budget:
            print(f"Terminated at attempt {attempt} with budget {budget}!")
            break

if __name__ == "__main__":
    test_difficulty()
