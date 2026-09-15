import json
from unittest.mock import patch, MagicMock
from app.main import generate, Request
from app.config import config

def test_prompt_logging():
    config.set("LORA_ENABLED", False)
    config.set("MEMORY_ENABLED", True)
    
    # We will mock generate_code to fail tests so it calls fix_code
    # We will also mock fix_code to return a tuple (code, debug_prompt)
    
    with patch("app.main.generate_code", return_value=("def a(): pass", "Initial Generation Prompt Text")):
        with patch("app.main.execute_code", return_value={"success": True, "error": None, "verification": {"safety_passed": True}}):
            with patch("app.main.run_tests", return_value={"success": False, "message": "AssertionError", "tests": "", "test_summary": {}}):
                # mock search to return 1 memory
                with patch("app.repair_memory.repair_memory.search_similar_experiences", return_value=[{"memory": {"memory_id": "mem_1", "error_message": "Some error", "broken_code": "bad code", "successful_fix": "good code"}, "similarity": 0.9}]):
                    # mock fix_code itself to not actually call ML, but just format the prompt exactly as it would
                    import app.model
                    original_fix_code = app.model.fix_code
                    
                    def mock_generate_raw(prompt):
                        return prompt # Just return the prompt so extract_code gives something harmless or we just skip it
                        
                    with patch("app.model.generate_raw", side_effect=mock_generate_raw):
                        with patch("app.model.is_code_valid", return_value=True):
                            req = Request(prompt="Do something")
                            result = generate(req)
                            
                            feedback = result["feedback_record"]
                            # Check generation_prompt
                            assert feedback["generation_prompt"] == "Initial Generation Prompt Text", "Initial prompt not logged"
                            
                            # Check debug_prompt for attempt 1
                            attempt1 = feedback["attempts"][0]
                            assert "debug_prompt" in attempt1, "debug_prompt missing"
                            prompt_text = attempt1["debug_prompt"]
                            assert "Some error" in prompt_text, "Memory injected not in debug_prompt"
                            assert "good code" in prompt_text, "Memory injected not in debug_prompt"
                            
                            # Check memory_injected
                            assert attempt1["memory_injected"] is True, "memory_injected boolean is wrong"
                            
                            print("PROMPT LOGGING TEST PASSED!")

if __name__ == "__main__":
    test_prompt_logging()
