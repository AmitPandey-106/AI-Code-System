from app.main import generate, Request
import app.main
from unittest.mock import patch, MagicMock
from app.config import config

def test_difficulty_observational():
    # Make sure we use a mode that would have activated the bug
    config.set("DIFFICULTY_ALLOCATION_ENABLED", True)
    config.set("MEMORY_ENABLED", False) # skip memory search to keep it fast
    config.set("STRATEGY_LEARNING_ENABLED", False)

    # Mock all the slow AI/execution parts
    with patch("app.main.generate_code", return_value="def a(): syntax error"):
        with patch("app.main.execute_code", return_value={"success": False, "error": "SyntaxError: invalid syntax", "verification": {"safety_passed": True}}):
            with patch("app.main.run_tests", return_value={"success": False, "message": "SyntaxError", "tests": "", "test_summary": {}}):
                with patch("app.main.fix_code", return_value="def a(): still error"):
                    
                    req = Request(prompt="Do something")
                    result = generate(req)
                    
                    feedback = result["feedback_record"]
                    attempts = feedback["attempts"]
                    
                    print(f"Total attempts executed: {len(attempts)}")
                    assert len(attempts) == 5, f"Expected 5 attempts, got {len(attempts)}"
                    
                    # Verify difficulty was still recorded
                    diff_info = attempts[0].get("difficulty")
                    assert diff_info is not None, "Difficulty info missing!"
                    print(f"Attempt 1 recorded difficulty: {diff_info['difficulty']} (Budget: {diff_info['recommended_attempts']})")
                    
                    print("SUCCESS! The system successfully reached 5 attempts while recording observational budget.")

if __name__ == "__main__":
    test_difficulty_observational()
