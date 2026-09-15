from app.repair_difficulty import estimate_difficulty

def test_anomaly():
    print("--- Proving Anomaly ---")
    
    # Attempt 1: TimeoutError (Base 4)
    d1 = estimate_difficulty("TimeoutError", "x = 1", 1, True)
    print(f"Attempt 1: Error=Timeout, Score={d1['score']}, Budget={d1['recommended_attempts']}")
    # 1 >= 3 is False
    
    # Attempt 2: AssertionError (Base 3)
    d2 = estimate_difficulty("AssertionError", "x = 1", 2, True)
    print(f"Attempt 2: Error=Assert, Score={d2['score']}, Budget={d2['recommended_attempts']}")
    # 2 >= 3 is False
    
    # Attempt 3: TimeoutError (Base 4)
    d3 = estimate_difficulty("TimeoutError", "x = 1", 3, True)
    print(f"Attempt 3: Error=Timeout, Score={d3['score']}, Budget={d3['recommended_attempts']}")
    # 3 >= 4 is False
    
    # Attempt 4: SyntaxError (Base 1)
    d4 = estimate_difficulty("SyntaxError", "x = 1", 4, True)
    print(f"Attempt 4: Error=Syntax, Score={d4['score']}, Budget={d4['recommended_attempts']}")
    # 4 >= 3 is True -> BREAKS!
    
    if 4 >= d4['recommended_attempts']:
        print("TERMINATED at Attempt 4 with Final Budget 3 (MEDIUM)!")

if __name__ == "__main__":
    test_anomaly()
