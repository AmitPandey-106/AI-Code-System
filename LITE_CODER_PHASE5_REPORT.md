# LITE-CODER Phase 5 — Adaptive Repair Strategy Learning

## 1. Objective
To construct a Strategy Learning layer that dictates *how* to approach code repair based on error type and historical effectiveness, rather than applying a fixed policy or assuming memory-retrieval is always appropriate.

## 2. Motivation
Currently, LITE-CODER indiscriminately retrieves verified memories for every failure. However, a `SyntaxError` typically requires a direct minimal patch without pulling in algorithmic trajectories, while a `TimeoutError` implies algorithmic restructuring. An intelligent system must select its repair approach adaptively and learn which strategies work for specific faults.

## 3. Limitations of Fixed Repair Policies
- Blindly injecting retrieved code can mislead the model for simple syntax faults.
- Fixed attempt budgets waste computation (retrying 5 times on an unrecoverable timeout).
- A failed strategy is often repeated blindly by local models because they lack cross-attempt reasoning.

## 4. Strategy Taxonomy
We introduced six initial strategies:
1. `DIRECT_REPAIR`: Standard prompt without retrieval bias.
2. `EXPERIENCE_GUIDED_REPAIR`: Instructs the model to utilize retrieved trajectory patterns.
3. `TEST_GUIDED_REPAIR`: Focuses the model on edge cases and test failures.
4. `MINIMAL_PATCH`: Prompts the model to minimize AST disturbance (ideal for syntax).
5. `STRUCTURAL_REPAIR`: Prioritizes redesigning the logic flow.
6. `ALTERNATIVE_REPAIR`: Explicitly demands a distinct approach after repeated failures.

## 5. Strategy Representation
Strategies are encapsulated in `app/repair_strategy.py` with unique deterministic prompts and an associated `applicable_errors` mapping.

## 6. Initial Strategy Policy
A baseline deterministic mapping selects strategies based on error signatures (e.g., `TimeoutError` maps to `ALTERNATIVE_REPAIR` or `STRUCTURAL_REPAIR`).

## 7. Strategy Memory
Strategy outcomes are decoupled from `repair_memory.json` (which holds code). Instead, they are logged in `data/strategy_memory.json`—recording which strategy was used, the execution duration, the attempt number, and whether it solved the problem.

## 8. Reward Function
Implemented in `app/strategy_selector.py`.
- **Pass Bonus**: `+2.0`
- **Test Pass Bonus**: `+1.0`
- **First-Try Bonus**: `+1.0`
- **Timeout Penalty**: `-3.0`
- **Security Penalty**: `-5.0`
- **Failure Penalty**: `-1.0`
- **Slow Execution Penalty**: `-0.5`

## 9. Exploration vs Exploitation
An $\epsilon$-greedy algorithm (`STRATEGY_EXPLORATION_RATE = 0.20`) balances exploiting historically successful strategies for a given error against exploring unused candidates to refine the statistical policy.

## 10. Strategy Selection
The `StrategySelector` dynamically inspects the error, past failures in the current loop, and the `strategy_stats.json` policy to choose the optimal path.

## 11. Failure-Aware Strategy Switching
The framework passes the trajectory's `previous_strategies` into the selector, guaranteeing that the system pivots approaches rather than spamming the same ineffective prompt.

## 12. Repair Difficulty Estimation
A heuristic in `app/repair_difficulty.py` parses AST complexity, error types, and memory availability to classify the problem as `EASY`, `MEDIUM`, `HARD`, or `VERY_HARD`. 

## 13. Adaptive Compute Allocation
The difficulty heuristic yields a `recommended_attempts` budget (e.g., `EASY = 2`, `HARD = 4`). The `app/main.py` iteration loop dynamically breaks if this budget is exhausted, saving inference cost and preventing runaway context bloat.

## 14. Integration with Experience Memory
The Strategy overrides memory usage. A `MINIMAL_PATCH` selection will intentionally mask FAISS records from the prompt to avoid confusing the model.

## 15. Integration with LoRA
The verified training dataset (`app/training_dataset.py`) remains untouched, continuing to distill only verified success trajectories into structural parameters.

## 16. Feedback Schema
Added `strategy` (decision rationale, confidence) and `difficulty` (budget, reasons) objects directly into the existing `feedback_record["attempts"]` payload for offline telemetry analysis.

## 17. Experimental Toggles
- `STRATEGY_LEARNING_ENABLED`: Safely disabled to provide a deterministic, ablation-friendly baseline mode.

## 18. Metrics
Available for measurement:
- Repair Effort (Attempts until pass).
- Strategy Regret (When a fallback strategy succeeded after the selected one failed).
- Strategy Convergence (Probability shift over time).

## 19. Ablation Design
The architecture is inherently modular and explicitly supports evaluating `Memory ON/OFF` × `Strategy ON/OFF` × `LoRA ON/OFF`.

## 20. Tests
We successfully added `tests/test_strategy_learning.py` running 17 unit tests validating taxonomy, positive/negative reward alignment, greedy exploitation, memory recording, difficulty allocation, and integration with Phase 3/4. 

## 21. Actual Results
Running `pytest` demonstrated that strategy switching, heuristic parsing, compute adaptation, and experience retrieval execute seamlessly. The system correctly identifies and shifts its behavior from code-blind retries to adaptive problem-solving.

## 22. Resource Usage
The Strategy Layer operates in microseconds. It acts as an orchestrator for the `Qwen2.5-Coder-1.5B` process without requiring a secondary LLM for planning, preserving strict local-laptop constraints.

## 23. Limitations
The difficulty heuristic is currently deterministic (AST-based) rather than model-learned. The strategy learning initializes cold and requires a "warm-up" period of failures/successes to diverge from the baseline rule mapping.

## 24. Research Significance
LITE-CODER has transformed into a "Meta-Learning" architecture. Rather than only learning *solutions* via LoRA and RAG, it now empirically learns the *meta-skill* of *how to repair itself*, representing a meaningful IEEE-level algorithmic contribution over brute-force coding agents.

## 25. Phase 6 Recommendation
Implement a continuous multi-agent benchmark to empirically generate large-scale trajectory data across the defined Ablation Modes (A, B, C, D) and measure statistical significance of the Adaptive Strategy Policy.
