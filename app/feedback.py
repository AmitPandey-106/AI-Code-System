import json
import os

FILE_PATH = "data/feedback.json"

def save_feedback(record):
    try:
        # Validate basic feedback structure
        required_keys = ["task", "initial_code", "attempts", "final_code", "final_status"]
        for key in required_keys:
            if key not in record:
                print(f"Warning: Missing key '{key}' in feedback record.")

        # Ensure directory exists
        os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

        data = []
        if os.path.exists(FILE_PATH):
            try:
                with open(FILE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
            except json.JSONDecodeError:
                print("Warning: Feedback file corrupted. Starting fresh.")
                data = []

        if not isinstance(data, list):
            data = []

        data.append(record)

        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        print("Error saving feedback:", e)