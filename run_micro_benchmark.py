from benchmark.runner import run_benchmark
from benchmark.reporter import save_report

# Run MODE_A (Baseline)
print("=== RUNNING MODE A ===")
res_a = run_benchmark("EXP_MICRO_A", "MODE_A", size=2)
save_report("EXP_MICRO_A", res_a)

# Run MODE_D (Memory + Strategy)
print("\n=== RUNNING MODE D ===")
res_d = run_benchmark("EXP_MICRO_D", "MODE_D", size=2)
save_report("EXP_MICRO_D", res_d)

print("\nMicro benchmark completed successfully.")
