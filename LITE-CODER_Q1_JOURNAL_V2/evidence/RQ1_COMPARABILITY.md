# RQ1 COMPARABILITY: MODE A vs MODE D

**RQ1: Does experience memory improve repair effectiveness?**

**Are they comparable?**
YES, structurally. 

**What is identical?**
- Model (Base Qwen2.5-Coder-1.5B)
- Benchmark tasks (100)
- Execution mechanism (`exec()`)
- Seed (42)

**What differs?**
- Memory retrieval enabled in Mode D.

**Caveat for legitimate comparison:**
We must verify that Mode D's memory started *empty* or was pre-populated exclusively with *training/non-evaluation* tasks. If Mode D was given a pre-populated memory of the test set, the comparison is invalid. Assuming memory started empty and populated dynamically (online learning), Mode A vs Mode D perfectly answers RQ1.
