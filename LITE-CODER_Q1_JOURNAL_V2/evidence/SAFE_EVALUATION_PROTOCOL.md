# SAFE EVALUATION PROTOCOL

SAFE mode (AST/Contract validation) fundamentally alters the testing oracle. 

**A. Repair effectiveness:**
Cannot be directly compared to Mode A/D/F for raw success rates because the oracle is stricter. A fix that passes `exec()` in Mode D might fail AST validation in Mode F_SAFE.

**B. Verification integrity:**
SAFE mode is the primary mechanism for establishing verification integrity.

**C. Contamination resistance & D. Security robustness:**
Must be evaluated independently using a dedicated security/adversarial dataset (e.g., `tests/test_fault_injection.py`), not the standard 100-task benchmark.

**Protocol:** 
Treat SAFE as a separate research dimension determining *trust*. Do not use SAFE success rates as evidence of memory effectiveness without a `MODE_A_SAFE` baseline.
