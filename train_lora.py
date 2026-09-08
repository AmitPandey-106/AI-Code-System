import json
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
import torch

with open("data/feedback.json", "r") as f:
    raw_data = json.load(f)

train_data = []

for item in raw_data:
    # Support for legacy format
    if "error" in item and item.get("success"):
        if item.get("error") and item.get("fixed_code"):
            train_data.append({
                "text": f"Fix this Python code:\n\n{item['generated_code']}\n\nError:\n{item['error']}\n\nCorrect Code:\n{item['fixed_code']}\n"
            })
    # Support for new format (Phase 1)
    elif "attempts" in item and item.get("final_status") == "success":
        for attempt in item["attempts"]:
            if attempt.get("error_message") and attempt.get("repair_applied"):
                train_data.append({
                    "text": f"Fix this Python code:\n\n{attempt['code']}\n\nError:\n{attempt['error_message']}\n\nCorrect Code:\n{attempt['repair_applied']}\n"
                })

dataset = Dataset.from_list(train_data)

print("Dataset size:", len(dataset))

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

# Fix padding token (Qwen fix)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

def tokenize_function(example):
    tokens = tokenizer(
        example["text"],
        truncation=True,
        padding="max_length",
        max_length=512
    )

    # 🔥 IMPORTANT: add labels
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
    fp16=False   # keep False for CPU
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset   # 👈 THIS LINE IS CRITICAL
)

trainer.train()

model.save_pretrained("lora-finetuned")
tokenizer.save_pretrained("lora-finetuned")

