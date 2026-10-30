import os
import sys
import time
import json
import shutil
import traceback
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, PeftModel
from filelock import FileLock, Timeout

from app.config import config
from app.training_dataset import build_dataset

TRAINING_STATE_FILE = "models/adapters/training_state.json"
TRAINING_HISTORY_FILE = "models/adapters/training_history.json"
CANDIDATES_DIR = "models/adapters/candidates"
ACTIVE_ADAPTER_DIR = "models/adapters/active"
ARCHIVE_DIR = "models/adapters/archive"
TRAINING_LOCK_FILE = "models/adapters/training.lock"

def check_torchao_compatibility():
    """
    Defensively guard against incompatible torchao versions (< 0.16.0)
    which cause peft.import_utils.is_torchao_available() to raise an ImportError.
    """
    try:
        import importlib.util
        if importlib.util.find_spec("torchao") is not None:
            import importlib.metadata as im
            from packaging import version
            try:
                v = version.parse(im.version("torchao"))
                if v < version.parse("0.16.0"):
                    print(f"[WARN] Incompatible torchao version detected ({v} < 0.16.0). Neutralizing torchao module to avoid peft ImportError.")
                    sys.modules["torchao"] = None
            except Exception:
                pass
    except Exception:
        pass

check_torchao_compatibility()

def get_training_state():
    if os.path.exists(TRAINING_STATE_FILE):
        try:
            with open(TRAINING_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_trained_count": 0,
        "adapter_version_counter": 0,
        "active_adapter_id": None,
        "is_training": False
    }

def save_training_state(state):
    os.makedirs(os.path.dirname(TRAINING_STATE_FILE), exist_ok=True)
    tmp_path = TRAINING_STATE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, TRAINING_STATE_FILE)

def append_training_history(entry):
    os.makedirs(os.path.dirname(TRAINING_HISTORY_FILE), exist_ok=True)
    history = []
    if os.path.exists(TRAINING_HISTORY_FILE):
        try:
            with open(TRAINING_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(entry)
    tmp_path = TRAINING_HISTORY_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, TRAINING_HISTORY_FILE)

def run_training_pipeline(force: bool = False, memory_file: str = None, experiment_id: str = None, trigger_task_id: str = None, trigger_task_index: int = None):
    """
    Executes a verified, gated LoRA training cycle.
    Returns dict with training results and validation status.
    """
    os.makedirs(os.path.dirname(TRAINING_LOCK_FILE), exist_ok=True)
    lock = FileLock(TRAINING_LOCK_FILE, timeout=5)
    try:
        with lock:
            return _run_training_pipeline_internal(
                force=force,
                memory_file=memory_file,
                experiment_id=experiment_id,
                trigger_task_id=trigger_task_id,
                trigger_task_index=trigger_task_index
            )
    except Timeout:
        print("[LORA WORKER] Another training process is active. Lock busy.")
        return {"trained": False, "success": False, "reason": "lock_busy"}

def _run_training_pipeline_internal(force: bool = False, memory_file: str = None, experiment_id: str = None, trigger_task_id: str = None, trigger_task_index: int = None):
    start_time = time.time()
    state = get_training_state()
    buffer_threshold = config.get("LORA_BUFFER_SIZE", 4)
    last_trained = state.get("last_trained_count", 0)

    # 1. Build and validate experience dataset with Experience Replay
    print("[LORA WORKER] Building verified experience dataset with Experience Replay...")
    dataset_info = build_dataset(
        memory_file=memory_file,
        last_trained_count=last_trained
    )
    stats = dataset_info.get("stats", {})
    if not stats or stats.get("accepted_unique_count", 0) == 0:
        print("[LORA WORKER] No verified repair experiences found.")
        return {"trained": False, "success": False, "reason": "no_memories"}

    unique_memories = stats["accepted_unique_count"]
    new_memories = stats.get("new_examples_count", unique_memories - last_trained)
    replay_count = stats.get("replay_examples_count", 0)

    print(f"[LORA WORKER] Total unique verified memories: {unique_memories}")
    print(f"[LORA WORKER] New memories: {new_memories} (Buffer target: {buffer_threshold}), Replayed memories: {replay_count}")

    if not force and new_memories < buffer_threshold:
        print(f"[LORA WORKER] Threshold not reached ({new_memories} < {buffer_threshold}). Skipping training.")
        return {
            "trained": False,
            "success": True,
            "reason": "buffer_not_reached",
            "new_memories": new_memories,
            "buffer_target": buffer_threshold
        }

    # Prepare training set (includes newly arrived + replayed experiences)
    train_data = dataset_info.get("train", [])
    if len(train_data) == 0:
        # If train split is empty, use all accepted examples
        train_data = [item for item in dataset_info.get("test", [])]
    if len(train_data) == 0:
        print("[LORA WORKER] No usable training examples.")
        return {"trained": False, "success": False, "reason": "empty_training_data"}

    version = state.get("adapter_version_counter", 0) + 1
    candidate_id = f"adapter_v{version}_{int(time.time())}"
    candidate_path = os.path.join(CANDIDATES_DIR, candidate_id)
    output_dir = f"./lora-output-v{version}"
    model_name = "Qwen/Qwen2.5-Coder-1.5B"
    cycle_id = f"cycle_v{version}_{int(start_time)}"

    history_entry = {
        "training_cycle_id": cycle_id,
        "trigger_task_id": trigger_task_id,
        "trigger_task_index": trigger_task_index,
        "training_example_count": len(train_data),
        "new_examples_count": stats.get("new_examples_count", len(train_data)),
        "replay_examples_count": stats.get("replay_examples_count", 0),
        "replay_strategy": stats.get("replay_strategy", "all"),
        "replay_size": stats.get("replay_size", 0),
        "previous_adapter": state.get("active_adapter_id"),
        "candidate_adapter": candidate_id,
        "training_started_at": start_time,
        "training_finished_at": None,
        "training_status": "pending",
        "training_loss": None,
        "adapter_id": candidate_id,
        "candidate_adapter_path": candidate_path,
        "adapter_config_exists": False,
        "adapter_weights_exists": False,
        "adapter_weights_size": 0,
        "validation_status": "pending",
        "promotion_status": "pending",
        "rollback": False,
        "canary_tasks": None,
        "canary_success_rate": None,
        "active_adapter_id": None,
        "reload_status": "pending",
        "error_message": None,
        "candidate_id": candidate_id,
        "version": version,
        "experiment_id": experiment_id,
        "timestamp": start_time,
        "source_memory_count": unique_memories,
        "training_examples_count": len(train_data),
        "status": "pending",
        "error": None
    }

    try:
        # 2. Tokenizer & Dataset Preparation with Label Masking
        print(f"[LORA WORKER] Initializing training for candidate {candidate_id}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        def tokenize_function(example):
            prompt_text = example.get("prompt", "")
            completion_text = example.get("completion", "")
            if not prompt_text:
                # Fallback if raw prompt not split
                text = example.get("text", "")
                parts = text.split("Return corrected executable Python code:\n")
                if len(parts) == 2:
                    prompt_text = parts[0] + "Return corrected executable Python code:\n"
                    completion_text = parts[1]
                else:
                    prompt_text = text
                    completion_text = ""

            prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False, truncation=True, max_length=512)
            completion_ids = tokenizer.encode(completion_text, add_special_tokens=False, truncation=True, max_length=512)
            eos_id = [tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else []

            input_ids = prompt_ids + completion_ids + eos_id
            attention_mask = [1] * len(input_ids)

            # Mask prompt tokens with -100 so loss is computed solely on the repair completion
            labels = ([-100] * len(prompt_ids)) + completion_ids + eos_id

            return {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels
            }

        raw_dataset = Dataset.from_list(train_data)
        tokenized_dataset = raw_dataset.map(tokenize_function, remove_columns=raw_dataset.column_names)

        # 3. Model Loading & PEFT Setup
        selected_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        target_device_map = "auto" if torch.cuda.is_available() else None
        base_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=selected_dtype,
            device_map=target_device_map
        )

        r = config.get("LORA_RANK", 8)
        alpha = config.get("LORA_ALPHA", 16)
        dropout = config.get("LORA_DROPOUT", 0.05)
        lora_config = LoraConfig(
            r=r,
            lora_alpha=alpha,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=dropout,
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(base_model, lora_config)

        # 4. Training Arguments
        epochs = config.get("LORA_EPOCHS", 3)
        lr = config.get("LORA_LEARNING_RATE", 2e-4)
        seed = config.get("BENCHMARK_SEED", 42)

        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=1,
            num_train_epochs=epochs,
            learning_rate=lr,
            logging_steps=1,
            save_strategy="no",
            fp16=torch.cuda.is_available(),
            seed=seed,
            report_to="none"
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset
        )

        print(f"[LORA WORKER] Running Trainer for {epochs} epochs over {len(train_data)} examples...")
        train_result = trainer.train()
        train_loss = float(train_result.training_loss)
        print(f"[LORA WORKER] Training completed. Final Loss: {train_loss:.4f}")

        # 5. Save Candidate Adapter
        os.makedirs(candidate_path, exist_ok=True)
        model.save_pretrained(candidate_path)
        tokenizer.save_pretrained(candidate_path)

        # Clean training structures from VRAM / RAM
        del model
        del base_model
        del trainer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)

        # 6. Adapter Validation & Acceptance Gate (Phase 8)
        print(f"[LORA WORKER] Validating candidate adapter artifacts at {candidate_path}...")
        config_file = os.path.join(candidate_path, "adapter_config.json")
        weights_safetensors = os.path.join(candidate_path, "adapter_model.safetensors")
        weights_bin = os.path.join(candidate_path, "adapter_model.bin")

        has_config = os.path.exists(config_file)
        has_weights = (os.path.exists(weights_safetensors) and os.path.getsize(weights_safetensors) > 0) or \
                      (os.path.exists(weights_bin) and os.path.getsize(weights_bin) > 0)

        if not (has_config and has_weights):
            raise RuntimeError(f"Candidate adapter files missing or incomplete in {candidate_path}.")

        # In-memory inference verification check
        print("[LORA WORKER] Performing verification load and inference test...")
        val_base = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=selected_dtype,
            device_map=target_device_map
        )
        val_peft = PeftModel.from_pretrained(val_base, candidate_path)
        val_peft.eval()

        test_prompt = "def add(a, b):\n    return"
        inputs = tokenizer(test_prompt, return_tensors="pt").to(val_peft.device)
        with torch.no_grad():
            outputs = val_peft.generate(**inputs, max_new_tokens=10, do_sample=False)
        test_out = tokenizer.decode(outputs[0], skip_special_tokens=True)

        if not test_out:
            del val_peft
            del val_base
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise RuntimeError("Candidate adapter generated empty output during validation inference test.")

        # 7. Canary Regression Gate (MODE-F SAFE)
        canary_results = None
        canary_passed = True
        if config.get("LORA_CANARY_ENABLED", True):
            from app.canary import evaluate_canary_gate
            canary_thresh = config.get("LORA_CANARY_PASS_THRESHOLD", 1.0)
            canary_results = evaluate_canary_gate(
                val_peft,
                tokenizer,
                threshold=canary_thresh
            )
            canary_passed = canary_results.get("gate_passed", False)

        del val_peft
        del val_base
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        prev_active_id = state.get("active_adapter_id")
        duration = time.time() - start_time

        # Check if candidate failed Canary Gate -> Trigger Rollback
        if not canary_passed:
            print(f"[LORA WORKER WARNING] Candidate {candidate_id} FAILED Canary Gate! Initiating Adapter Rollback...")
            metadata = {
                "adapter_id": candidate_id,
                "version": version,
                "base_model": model_name,
                "created_at": time.time(),
                "duration_seconds": round(duration, 2),
                "training_examples": len(train_data),
                "new_examples_count": stats.get("new_examples_count", len(train_data)),
                "replay_examples_count": stats.get("replay_examples_count", 0),
                "source_experience_count": unique_memories,
                "train_loss": round(train_loss, 4),
                "peft_config": {
                    "r": r,
                    "lora_alpha": alpha,
                    "lora_dropout": dropout,
                    "target_modules": ["q_proj", "v_proj"]
                },
                "status": "rejected",
                "promotion_status": "rejected",
                "rollback": True,
                "rejection_reason": "canary_regression_detected",
                "retained_active_adapter_id": prev_active_id,
                "previous_adapter": prev_active_id,
                "canary_results": canary_results
            }

            with open(os.path.join(candidate_path, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)

            # Previous stable adapter in ACTIVE_ADAPTER_DIR is preserved intact (never destroyed)
            # Active adapter is not modified; state retains previous active_adapter_id
            save_training_state(state)

            # Record in history
            history_entry["training_finished_at"] = time.time()
            history_entry["training_status"] = "success"
            history_entry["status"] = "rejected"
            history_entry["training_loss"] = round(train_loss, 4)
            history_entry["train_loss"] = round(train_loss, 4)
            history_entry["adapter_config_exists"] = has_config
            history_entry["adapter_weights_exists"] = has_weights
            weights_file = weights_safetensors if os.path.exists(weights_safetensors) else weights_bin
            history_entry["adapter_weights_size"] = os.path.getsize(weights_file) if os.path.exists(weights_file) else 0
            history_entry["validation_status"] = "passed"
            history_entry["promotion_status"] = "rejected"
            history_entry["rollback"] = True
            history_entry["canary_status"] = "failed"
            history_entry["canary_success_rate"] = canary_results.get("canary_success_rate", 0.0) if canary_results else 0.0
            history_entry["canary_tasks"] = canary_results.get("canary_tasks_count", 0) if canary_results else 0
            history_entry["rejection_reason"] = "canary_regression_detected"
            history_entry["previous_adapter"] = prev_active_id
            history_entry["active_adapter_id"] = prev_active_id
            history_entry["candidate_adapter"] = candidate_id
            history_entry["reload_status"] = "rollback_retained"
            history_entry["duration_seconds"] = round(duration, 2)
            history_entry["metadata"] = metadata
            history_entry["canary_results"] = canary_results
            append_training_history(history_entry)

            print(f"[LORA WORKER] Candidate {candidate_id} rejected. Retaining stable active adapter: {prev_active_id}")
            return {
                "trained": True,
                "success": False,
                "promotion_status": "rejected",
                "rollback": True,
                "rejection_reason": "canary_regression_detected",
                "training_cycle_id": cycle_id,
                "adapter_id": candidate_id,
                "active_adapter_id": prev_active_id,
                "version": version,
                "train_loss": train_loss,
                "examples": len(train_data),
                "duration_seconds": duration,
                "canary_results": canary_results
            }

        # 8. Promotion to Active Adapter (Canary Gate Passed)
        print(f"[LORA WORKER] Canary Gate passed! Promoting candidate {candidate_id} to active...")
        # Archive previous active adapter if present (never destroy)
        if os.path.exists(ACTIVE_ADAPTER_DIR):
            archive_path = os.path.join(ARCHIVE_DIR, f"archive_{prev_active_id}_{int(time.time())}")
            os.makedirs(os.path.dirname(archive_path), exist_ok=True)
            shutil.copytree(ACTIVE_ADAPTER_DIR, archive_path, dirs_exist_ok=True)
            shutil.rmtree(ACTIVE_ADAPTER_DIR, ignore_errors=True)

        # Copy candidate to active
        shutil.copytree(candidate_path, ACTIVE_ADAPTER_DIR, dirs_exist_ok=True)

        metadata = {
            "adapter_id": candidate_id,
            "version": version,
            "base_model": model_name,
            "created_at": time.time(),
            "duration_seconds": round(duration, 2),
            "training_examples": len(train_data),
            "new_examples_count": stats.get("new_examples_count", len(train_data)),
            "replay_examples_count": stats.get("replay_examples_count", 0),
            "source_experience_count": unique_memories,
            "train_loss": round(train_loss, 4),
            "peft_config": {
                "r": r,
                "lora_alpha": alpha,
                "lora_dropout": dropout,
                "target_modules": ["q_proj", "v_proj"]
            },
            "status": "active",
            "promotion_status": "promoted",
            "rollback": False,
            "previous_adapter": prev_active_id,
            "canary_results": canary_results
        }

        with open(os.path.join(ACTIVE_ADAPTER_DIR, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
        with open(os.path.join(candidate_path, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        # Update persistent state
        state["last_trained_count"] = unique_memories
        state["adapter_version_counter"] = version
        state["active_adapter_id"] = candidate_id
        save_training_state(state)

        # Record in history
        history_entry["training_finished_at"] = time.time()
        history_entry["training_status"] = "success"
        history_entry["status"] = "success"
        history_entry["training_loss"] = round(train_loss, 4)
        history_entry["train_loss"] = round(train_loss, 4)
        history_entry["adapter_config_exists"] = has_config
        history_entry["adapter_weights_exists"] = has_weights
        weights_file = weights_safetensors if os.path.exists(weights_safetensors) else weights_bin
        history_entry["adapter_weights_size"] = os.path.getsize(weights_file) if os.path.exists(weights_file) else 0
        history_entry["validation_status"] = "passed"
        history_entry["promotion_status"] = "promoted"
        history_entry["rollback"] = False
        history_entry["canary_status"] = "passed"
        history_entry["canary_success_rate"] = canary_results.get("canary_success_rate", 1.0) if canary_results else 1.0
        history_entry["canary_tasks"] = canary_results.get("canary_tasks_count", 0) if canary_results else 0
        history_entry["previous_adapter"] = prev_active_id
        history_entry["active_adapter_id"] = candidate_id
        history_entry["candidate_adapter"] = candidate_id
        history_entry["reload_status"] = "ready_for_reload"
        history_entry["duration_seconds"] = round(duration, 2)
        history_entry["metadata"] = metadata
        history_entry["canary_results"] = canary_results
        append_training_history(history_entry)

        print(f"[LORA WORKER] Adapter {candidate_id} (v{version}) successfully trained, passed canary gate, and activated.")
        return {
            "trained": True,
            "success": True,
            "promotion_status": "promoted",
            "rollback": False,
            "training_cycle_id": cycle_id,
            "training_status": "success",
            "adapter_id": candidate_id,
            "active_adapter_id": candidate_id,
            "version": version,
            "train_loss": train_loss,
            "examples": len(train_data),
            "duration_seconds": duration,
            "canary_results": canary_results
        }

    except Exception as e:
        duration = time.time() - start_time
        err_msg = str(e)
        tb_str = traceback.format_exc()
        print(f"[LORA WORKER ERROR] Training cycle failed: {err_msg}")
        print(tb_str)

        history_entry["training_finished_at"] = time.time()
        history_entry["training_status"] = "failed"
        history_entry["status"] = "failed"
        history_entry["validation_status"] = "failed"
        history_entry["promotion_status"] = "aborted"
        history_entry["reload_status"] = "aborted"
        history_entry["error_message"] = err_msg
        history_entry["error"] = err_msg
        history_entry["traceback"] = tb_str
        history_entry["duration_seconds"] = round(duration, 2)
        append_training_history(history_entry)

        # Free GPU/CPU memory on failure
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return {
            "trained": False,
            "success": False,
            "training_cycle_id": cycle_id,
            "training_status": "failed",
            "error": err_msg,
            "traceback": tb_str
        }

if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    result = run_training_pipeline(force=force_flag)
    sys.exit(0 if result.get("success") else 1)
