from app.config import config

def apply_ablation_mode(mode: str):
    """
    Applies the specified ablation mode by setting the central configuration flags.
    
    MODE_A — BASELINE
    Memory OFF
    Adaptive Strategy Learning OFF
    LoRA OFF
    Difficulty-Aware Allocation OFF
    Static baseline strategy selection and verification remain enabled.

    MODE_D — MEMORY + ADAPTIVE STRATEGY
    Memory ON
    Adaptive Strategy Learning ON
    LoRA OFF
    Difficulty-Aware Allocation ON

    MODE_F — FULL LITE-CODER
    Memory ON
    Adaptive Strategy Learning ON
    LoRA ON
    Difficulty-Aware Allocation ON
    """
    if mode == "MODE_A":
        config.set("MEMORY_ENABLED", False)
        config.set("STRATEGY_LEARNING_ENABLED", False)
        config.set("LORA_ENABLED", False)
        config.set("DIFFICULTY_ALLOCATION_ENABLED", False)
    elif mode == "MODE_B" or mode == "MODE_C":
        config.set("MEMORY_ENABLED", True)
        config.set("STRATEGY_LEARNING_ENABLED", False)
        config.set("LORA_ENABLED", False)
        config.set("DIFFICULTY_ALLOCATION_ENABLED", False)
    elif mode == "MODE_D":
        config.set("MEMORY_ENABLED", True)
        config.set("STRATEGY_LEARNING_ENABLED", True)
        config.set("LORA_ENABLED", False)
        config.set("DIFFICULTY_ALLOCATION_ENABLED", True)
    elif mode == "MODE_E":
        config.set("MEMORY_ENABLED", True)
        config.set("STRATEGY_LEARNING_ENABLED", False)
        config.set("LORA_ENABLED", True)
        config.set("DIFFICULTY_ALLOCATION_ENABLED", False)
    elif mode == "MODE_F":
        config.set("MEMORY_ENABLED", True)
        config.set("STRATEGY_LEARNING_ENABLED", True)
        config.set("LORA_ENABLED", True)
        config.set("DIFFICULTY_ALLOCATION_ENABLED", True)
    else:
        raise ValueError(f"Unknown ablation mode: {mode}")

    print(f"Applied Ablation Mode: {mode}")
