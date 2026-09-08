import os
import time
import json
import shutil
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
from app.training_dataset import build_dataset
from app.evaluator import evaluate_model_on_test_set

TRAINING_STATE_FILE = "models/adapters/training_state.json"
CANDIDATES_DIR = "models/adapters/candidates"
ACTIVE_ADAPTER_DIR = "models/adapters/active"
ARCHIVE_DIR = "models/adapters/archive"
MIN_NEW_EXPERIENCES = 1

def get_training_state():
    if os.path.exists(TRAINING_STATE_FILE):
        with open(TRAINING_STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_trained_count": 0, "is_training": False}

def save_training_state(state):
    os.makedirs(os.path.dirname(TRAINING_STATE_FILE), exist_ok=True)
    with open(TRAINING_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def run_training_pipeline():
    state = get_training_state()
    if state.get("is_training"):
        print("Training lock active. Skipping.")
        return

    # 1. Build Dataset
    print("Building verified experience dataset...")
    dataset_info = build_dataset()
    stats = dataset_info["stats"]
    
    if not stats:
        print("No memory found.")
        return
        
    unique_memories = stats["accepted_unique_count"]
    new_memories = unique_memories - state["last_trained_count"]
    
    print(f"Total unique verified memories: {unique_memories}")
    print(f"New memories since last train: {new_memories}")
    
    if new_memories < MIN_NEW_EXPERIENCES:
        print(f"Threshold not reached ({new_memories} < {MIN_NEW_EXPERIENCES}). Skipping training.")
        return

    # Lock
    state["is_training"] = True
    save_training_state(state)

    try:
        # 2. Train LoRA
        print("Starting LoRA training...")
        train_data = dataset_info["train"]
        if len(train_data) == 0:
            print("No training data.")
            return

        dataset = Dataset.from_list(train_data)
        model_name = "Qwen/Qwen2.5-Coder-1.5B"
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch.float32,
            device_map="auto"
        )
        
        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, lora_config)
        
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        def tokenize_function(example):
            tokens = tokenizer(
                example["text"],
                truncation=True,
                padding="max_length",
                max_length=512
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens
            
        tokenized_dataset = dataset.map(tokenize_function)
        
        training_args = TrainingArguments(
            output_dir="./lora-output",
            per_device_train_batch_size=1,
            num_train_epochs=1,
            logging_steps=10,
            save_steps=50,
            save_total_limit=1,
            fp16=False # keep False for CPU
        )
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset
        )
        
        trainer.train()
        
        candidate_id = f"adapter_{int(time.time())}"
        candidate_path = os.path.join(CANDIDATES_DIR, candidate_id)
        os.makedirs(candidate_path, exist_ok=True)
        
        model.save_pretrained(candidate_path)
        tokenizer.save_pretrained(candidate_path)
        
        # Free memory
        del model
        del trainer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 3. Independent Evaluation
        print("Evaluating Base (Active) Model...")
        test_file = "data/dataset/test.json"
        
        base_metrics = evaluate_model_on_test_set("Qwen/Qwen2.5-Coder-1.5B", ACTIVE_ADAPTER_DIR if os.path.exists(ACTIVE_ADAPTER_DIR) else None, test_file)
        print("Base/Active Metrics:", base_metrics)
        
        print("Evaluating Candidate Model...")
        candidate_metrics = evaluate_model_on_test_set("Qwen/Qwen2.5-Coder-1.5B", candidate_path, test_file)
        print("Candidate Metrics:", candidate_metrics)
        
        # 4. Acceptance Criteria
        # Candidate must equal or exceed active model in execution success
        base_success = base_metrics.get("execution_success", 0)
        cand_success = candidate_metrics.get("execution_success", 0)
        
        accepted = cand_success >= base_success and cand_success > 0
        
        metadata = {
            "adapter_id": candidate_id,
            "base_model": model_name,
            "created_at": time.time(),
            "training_examples": len(train_data),
            "source_experience_count": unique_memories,
            "evaluation_results": {
                "base": base_metrics,
                "candidate": candidate_metrics
            },
            "status": "active" if accepted else "rejected"
        }
        
        with open(os.path.join(candidate_path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        if accepted:
            print("Candidate ACCEPTED! Activating...")
            # Archive old
            if os.path.exists(ACTIVE_ADAPTER_DIR):
                archive_path = os.path.join(ARCHIVE_DIR, f"archive_{int(time.time())}")
                os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                shutil.move(ACTIVE_ADAPTER_DIR, archive_path)
                
            shutil.copytree(candidate_path, ACTIVE_ADAPTER_DIR)
        else:
            print("Candidate REJECTED! Preserving current active model.")
            
        # Update state
        state["last_trained_count"] = unique_memories
        
    except Exception as e:
        print("Training job failed:", e)
    finally:
        state["is_training"] = False
        save_training_state(state)

if __name__ == "__main__":
    run_training_pipeline()
