# EXPERIMENT PROTOCOL MATRIX

| Parameter | MODE_A | MODE_D | MODE_F | MODE_F_SAFE |
|---|---|---|---|---|
| **Model** | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-1.5B |
| **Model Checkpoint** | Base | Base | LoRA-Finetuned | LoRA-Finetuned |
| **Benchmark Version** | v1.0 | v1.0 | v1.0 | v1.0 |
| **Task Count** | 100 | 100 | 100 | 100 |
| **Random Seed** | 42 | 42 | 42 | 42 |
| **Test Mechanism** | `exec()` / Native | `exec()` / Native | `exec()` / Native | AST/Contract Validation |
| **Memory State (Start)** | Empty (Disabled) | UNKNOWN (File shows 8 records) | UNKNOWN (File shows 8 records) | UNKNOWN (File shows 8 records) |
| **Retrieval Config** | None | Top-K=3, Thresh=0.5 | Top-K=3, Thresh=0.5 | Top-K=3, Thresh=0.5 |
| **Safety Config** | None | None | None | AST Sandbox Enabled |

*Note: Specific hyperparameters (temperature, max attempts) require explicit extraction from each `experiment_manifest.json`, but are intended to be identical across these runs.*
