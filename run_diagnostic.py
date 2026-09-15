from app.main import generate, Request
import json

def run_diagnostic():
    with open("data/benchmark/v1.0/dataset.json", "r") as f:
        dataset = json.load(f)
        
    task_data = None
    for t in dataset:
        if t["task_id"] == "TASK_FB475E1F":
            task_data = t
            break
            
    if not task_data:
        print("Task not found.")
        return
        
    print("Running diagnostic on TASK_FB475E1F...")
    
    # Run the repair loop isolatedly
    req = Request(**task_data)
    result = generate(req)
    
    print("\n=== DIAGNOSTIC REPORT ===")
    print(f"Success: {result.success}")
    print(f"Attempts: {result.attempts}")
    print(f"Final error: {result.error_type}")
    
    # Save the full result for inspection
    with open("scratch/diagnostic_result.json", "w") as f:
        json.dump(result.dict(), f, indent=4)
        
    print("Saved result to scratch/diagnostic_result.json")

if __name__ == "__main__":
    run_diagnostic()
