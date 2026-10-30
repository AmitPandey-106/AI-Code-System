# LITE-Coder Phase 8.2.2 — Isolated Experiment Readiness Audit Report

- **Date / Timestamp**: 2026-10-26T12:34:57+05:30
- **Auditor Role**: Senior Software Reliability Engineer & Experimental Reproducibility Auditor
- **Repository Root**: `D:\Amit Stuff\ai-code-system`
- **Audit Scope**: Read-only inspection and environment readiness verification. No authorization to execute.

---

## 1. Overall Verdict

**VERDICT: `BLOCKED`**

### Summary Rationale
1. **Mathematical & Cryptographic Verification**: **PASS**. All 9 authoritative Phase 8.2.1 artifacts exist. The canonical plan digest recalculates to the exact reviewed value `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`. All 6 execution and hardening source files match their pinned SHA-256 digests. All 122 protected export and fixture files match their recorded hashes. All 2,164 files in the starting preservation manifest are intact with 0 mismatches and 0 missing files. All 7 model cache files (3.1 GB safetensors + tokenizers) match byte-for-byte. All 7 critical runtime dependencies match the plan.
2. **Execution Restrictions Observed**: **PASS**. Zero coding-model calls have been made, zero experiment arms have started, and zero generated patches have been applied. The historical runner `scripts/phase8_2_arm.py` remains uninvoked and preserved.
3. **OS-Enforced Isolation & Network Restriction**: **BLOCKED (FAIL)**. The current execution environment is a bare-metal Windows host user session (`Windows-10-10.0.22621-SP0`). No disposable virtual machine, kernel-isolated container, or OS-level security boundary is available or active. The original repository, historical evidence, benchmarks, and model cache are within the process's writable filesystem space. Physical network connectivity remains enabled on the host adapter. While Python-level audit hooks (`WritePolicy` in `scripts/phase8_2_1_controls.py`) intercept standard Python file and socket APIs, per Phase 8.2.2 criteria, application-level audit hooks are explicitly **not** an OS security boundary against native extensions or same-account execution.

Under Section 3 criteria, because suitable OS-enforced isolation is unavailable, the readiness verdict must return **`BLOCKED`**.

---

## 2. Authoritative Evidence Artifact Inventory

All required artifacts were resolved from the repository with zero missing evidence:

| Artifact Name | Relative Path | Size (Bytes) | SHA-256 Checksum | Status |
|---|---|---:|---|:---:|
| `PHASE8_2_1_HARDENING_REPORT.md` | `eval_results_phase8_2_1/20261025_142828_IST/PHASE8_2_1_HARDENING_REPORT.md` | 16,301 | `21bfbee5a671a8c8ab6f3ee853b8f9732dc356bf5e27fea742b781af0a2e2c6b` | VERIFIED |
| `final_gate_v3/experiment_plan.json` | `eval_results_phase8_2_1/20261025_142828_IST/final_gate_v3/experiment_plan.json` | 32,650 | `bc0d7585aef6a4f0fb3d7d0194a62cd72c873a4118356ae5dab37de630980c68` | VERIFIED |
| `final_gate_v3/final_readonly_validation.json` | `eval_results_phase8_2_1/20261025_142828_IST/final_gate_v3/final_readonly_validation.json` | 2,394 | `a26de68c1ea0f80dc08e47e5fbbd2eb231d73b6a3d5087e3ebdc1312edbbc103` | VERIFIED |
| `final_gate_v3/source_hash_manifest.json` | `eval_results_phase8_2_1/20261025_142828_IST/final_gate_v3/source_hash_manifest.json` | 824 | `494cc13f9671fe6b0b307cb23cc5346d895cd82657cf25a9deb85a63010c09db` | VERIFIED |
| `final_gate_v3/protected_file_hash_manifest.json` | `eval_results_phase8_2_1/20261025_142828_IST/final_gate_v3/protected_file_hash_manifest.json` | 25,989 | `1b84317f7b48db841c9b92014940c01110de89c961a2fb6bf23a572c28399b48` | VERIFIED |
| `final_gate_v3/approval_gated_commands.json` | `eval_results_phase8_2_1/20261025_142828_IST/final_gate_v3/approval_gated_commands.json` | 1,051 | `1b114b41d6a7d59af2cce4c560e3f24d17109e324d376d66ebd3701af08a7c87` | VERIFIED |
| `final_gate_v3/test_results.json` | `eval_results_phase8_2_1/20261025_142828_IST/final_gate_v3/test_results.json` | 24,362 | `ebba75d18e0905808e2fb62d48b2628eacb7193f828cae3901ffc94e5233bd08` | VERIFIED |
| `environment_manifest.json` | `eval_results_phase8_2_1/20261025_142828_IST/environment_manifest.json` | 9,691 | `e8de02ed18276553e2f67c94dcd3441142c0100c81957dc22072b8cc4e36b173` | VERIFIED |
| `created_changed_files.json` | `eval_results_phase8_2_1/20261025_142828_IST/created_changed_files.json` | 720,924 | `094da1712794046ae875d723a93a352a00111b4b477d7b5eafd98afaff8755ed` | VERIFIED |

---

## 3. Current Plan Digest & Source-Hash Verification

### Canonical Plan Digest
The plan digest was independently recomputed using canonical JSON formatting (`json.dumps(obj, sort_keys=True, separators=(',', ':'))` excluding `plan_sha256`):

- **Expected Reviewed Digest**: `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
- **Recalculated Canonical Digest**: `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
- **Match Status**: **MATCH (EXACT)**
- **Raw File Byte SHA-256**: `bc0d7585aef6a4f0fb3d7d0194a62cd72c873a4118356ae5dab37de630980c68` (matches `final_gate_v3/plan_file_sha256.txt`)

### Source-Hash Verification
All 6 execution and test files bound to the execution gate were re-hashed from disk:

| Source File | Expected SHA-256 | Recalculated SHA-256 | Status |
|---|---|---|:---:|
| `scripts/phase8_2_1_arm.py` | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` | MATCH |
| `scripts/phase8_2_1_controls.py` | `9b4383f1b9fa4fa94ca0901c07f6db1391831bd71b45ee2746e3dbd163547abd` | `9b4383f1b9fa4fa94ca0901c07f6db1391831bd71b45ee2746e3dbd163547abd` | MATCH |
| `scripts/phase8_2_1_prepare.py` | `e04d68c6197cc3aa8f364ea185fcfcc62c8014142e3e92d4e417a8d81b77d1de` | `e04d68c6197cc3aa8f364ea185fcfcc62c8014142e3e92d4e417a8d81b77d1de` | MATCH |
| `scripts/phase8_2_1_pytest.py` | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` | MATCH |
| `tests/phase8_2_1_control_child.py` | `46e6f1577ebed89670004cdb656b685ddbda61ae05dc840e38226da1f45a1432` | `46e6f1577ebed89670004cdb656b685ddbda61ae05dc840e38226da1f45a1432` | MATCH |
| `tests/test_phase8_2_1_hardening.py` | `bfc9f426e73e3980ae63c2bd6bf2da0bccb65046e062aa273bb230104f83c3ad` | `bfc9f426e73e3980ae63c2bd6bf2da0bccb65046e062aa273bb230104f83c3ad` | MATCH |

### Historical Runner Status
- **Historical Runner**: `scripts/phase8_2_arm.py`
- **Expected SHA-256**: `651bd5cd094e3881448ea511220a3db7fe426596862cae0d21f0f147bdfe52fd`
- **Current SHA-256**: `651bd5cd094e3881448ea511220a3db7fe426596862cae0d21f0f147bdfe52fd`
- **Execution Check**: **NOT INVOKED**. The file remains preserved and intact.

---

## 4. Repository Status & Preservation Results

- **Git Branch**: `fix/phase8-1-integration`
- **Git HEAD Commit**: `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`
- **Tracked Changes**: 0 modified tracked files in Git index. Clean working tree for tracked files.
- **Starting Files Checked**: **2,164 / 2,164** files verified from `starting_preservation_manifest.json` with 0 mismatches and 0 missing.
- **Protected Files Checked**: **122 / 122** files verified across:
  - `eval_results_phase8_2_1/20261025_142828_IST/canonical_fixture`: 7 files (0 mismatches)
  - `eval_results_phase8_2_1/20261025_142828_IST/exports/baseline`: 57 files (0 mismatches)
  - `eval_results_phase8_2_1/20261025_142828_IST/exports/candidate`: 58 files (0 mismatches)
- **Actual Runs Check**:
  - `eval_results_phase8_2_1/20261025_142828_IST/runs/A`: Absent (`exists=False`)
  - `eval_results_phase8_2_1/20261025_142828_IST/runs/B`: Absent (`exists=False`)
  - `eval_results_phase8_2/20261025_131337_IST/arms/A/actual_run`: Absent (`exists=False`)
  - `eval_results_phase8_2/20261025_131337_IST/arms/B/actual_run`: Absent (`exists=False`)

---

## 5. OS-Enforced Isolation & Network-Restriction Evidence

| Evaluation Item | Status / Observation | Security Assessment |
|---|---|---|
| **Host Operating System** | `Windows-10-10.0.22621-SP0` (AMD64) | Bare metal host user session |
| **Disposable VM Available** | **NONE** | No disposable VM configured or active |
| **OS Container / Sandbox** | **NONE** | Not running in a container, WSL, or Windows Sandbox |
| **Separation from Dev Environment** | **FAIL** | Runner operates directly inside normal workspace directory |
| **Filesystem Write Protection** | **FAIL (OS level)** | Entire repo, evidence, and model cache are writable by user process |
| **Network Physical Restriction** | **FAIL (OS level)** | Host network adapter is active; outbound routing is unblocked at OS level |
| **Application-Level Controls** | `WritePolicy` audit hooks + offline flags | Present, but explicitly **not** an OS security boundary |

### Detailed Isolation Finding
Section 3 explicitly mandates:
> *"Determine whether a disposable VM or equivalent OS-enforced isolation environment is available and suitable... Python audit hooks, process supervision, read-only attributes, and application-level path guards are not equivalent to an OS security boundary. If suitable isolation is unavailable, return `BLOCKED` and explain the minimum requirement. Do not compensate by claiming the existing Python controls are a sandbox."*

The current execution environment relies on:
1. Python `sys.addaudithook` intercepting standard library calls (`open`, `socket.connect`, `os.rename`).
2. Read-only filesystem attributes on exported staging files.
3. Windows Job Object limits and child process suspension.
4. Process environment variables (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1`).

As explicitly documented in `scripts/phase8_2_1_controls.py:184`:
> *"Never a hostile-code sandbox: native extensions and the owning OS account can bypass Python audit hooks. No filesystem or network isolation claim is made."*

Therefore, the OS-enforced isolation requirement is **UNSATISFIED**, and the gate is **BLOCKED**.

---

## 6. Model-Cache & Dependency Availability

### Pinned Model Snapshot
- **Model Identifier**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- **Pinned Revision**: `2e1fd397ee46e1388853d2af2c993145b0f1098a`
- **Local Snapshot Path**: `D:\Amit Stuff\ai-code-system\.hf_cache\models--Qwen--Qwen2.5-Coder-1.5B-Instruct\snapshots\2e1fd397ee46e1388853d2af2c993145b0f1098a`

All 7 required model files are present on local disk with 100% byte-for-byte SHA-256 match:

| File Name | Size (Bytes) | SHA-256 Checksum | Verification Status |
|---|---:|---|:---:|
| `config.json` | 660 | `88f9a17863c05fb313515d2ff74b1098e0c35579f99068e32beda00618508ae0` | MATCH |
| `generation_config.json` | 242 | `1a628a5775bc69cde01c6749a531150ca4d3189652c618a174f7077923acf3b1` | MATCH |
| `merges.txt` | 1,671,839 | `599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3` | MATCH |
| `model.safetensors` | 3,087,467,144 | `c1b9b30e907950516ba3c646bdf570d8084c25a6410a0cdca80cf04b11bc13a8` | MATCH |
| `tokenizer.json` | 7,031,645 | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` | MATCH |
| `tokenizer_config.json` | 7,305 | `959e7f1d9a1b7641a6d6ce05ca97b75c7894fcb66cbe5a040406458fb1128ee4` | MATCH |
| `vocab.json` | 2,776,833 | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` | MATCH |

### Common Model Prompt
- **Path**: `eval_results_phase8_2_1/20261025_142828_IST/common_model_prompt.txt`
- **SHA-256**: `9f9ed1d8310e6792670551e66c9348e2192b4992a8df2630cab3a77cbb35af6d`
- **Verification Status**: **MATCH**

### Critical Runtime Dependencies
Inspected in active Python environment (`D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe`):

| Dependency | Expected Version | Installed Version | Status |
|---|---|---|:---:|
| `accelerate` | `1.13.0` | `1.13.0` | MATCH |
| `numpy` | `2.2.6` | `2.2.6` | MATCH |
| `peft` | `0.19.1` | `0.19.1` | MATCH |
| `pytest` | `9.1.1` | `9.1.1` | MATCH |
| `safetensors` | `0.7.0` | `0.7.0` | MATCH |
| `torch` | `2.11.0` | `2.11.0` | MATCH |
| `transformers` | `5.7.0` | `5.7.0` | MATCH |

---

## 7. Execution Gate Verification Matrix

| Gate # | Control Name | Status | Evidence & References |
|:---:|---|:---:|---|
| **G-01** | Plan Identity & Reviewed Digest | **PASS** | Canonical digest recalculation matches `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`. Raw file SHA matches `bc0d7585...`. |
| **G-02** | Runner & Execution Source Integrity | **PASS** | All 6 source files match recorded SHA-256 in `source_hash_manifest.json`. `phase8_2_1_arm.py` verified. |
| **G-03** | Historical Runner Inactivity | **PASS** | `scripts/phase8_2_arm.py` uninvoked, hash verified (`651bd5cd...`). |
| **G-04** | Fixture & Export Tree Preservation | **PASS** | All 122 protected files across `canonical_fixture`, `exports/baseline`, and `exports/candidate` verified byte-for-byte. |
| **G-05** | Repository Preservation (2,164 files) | **PASS** | 2,164 / 2,164 starting repository files verified unchanged with 0 missing files. Clean tracked git status. |
| **G-06** | Task & Revision Pinned Identity | **PASS** | Task `task_01_router_slug_param`. Arm A: `9ef57511...`. Arm B: `920c01aa...`. Order: `["A", "B"]`. |
| **G-07** | Offline Model Snapshot Integrity | **PASS** | 7 files (3.1 GB weights + configs) present in local cache; all SHA-256 digests match exactly. |
| **G-08** | Python Runtime & Dependency Alignment | **PASS** | Python 3.10.11 on Intel64. All 7 critical libraries match pinned versions. |
| **G-09** | Execution Budget & Hardware Limits | **PASS** | Max 1 call/arm, 768 max tokens/arm, 0 retries, CPU float32, eager attention, 4 torch threads, seed 42. |
| **G-10** | Oracle Transport & Assertion Integrity | **PASS** | Frozen `tests/test_router.py` SHA `1476656e...` and `eval_task_01` function SHA `782350ed...` intact. |
| **G-11** | Blocking Patch Approval Capability | **PASS** | Protocol enforces one-use capability via private pipe; target fixture locked until hash-confirmed approval. |
| **G-12** | Absence of Prior Actual Runs | **PASS** | `runs/A` and `runs/B` absent. Historical Phase 8.2 actual runs absent. |
| **G-13** | OS-Enforced Isolation & Network Sandbox | **FAIL (BLOCKED)** | No disposable VM or kernel sandbox. Host repo is writable by user process; host network interface is physically active. |
| **G-14** | Coding-Model Calls & Arm Execution | **UNVERIFIED** | Intentionally unexecuted. 0 model calls made; 0 experiment arms run. |

---

## 8. Environment Details & Intended Workspace

- **Host Environment**: `Windows-10-10.0.22621-SP0` (Windows 11 Build 22621), Intel64 Family 6 Model 142 Stepping 12, 8 logical CPUs, 4 physical CPUs.
- **Python Executable**: `D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe` (`3.10.11`)
- **Pytest Executable**: `D:\Amit Stuff\ai-code-system\venv\Scripts\pytest.EXE` (`9.1.1`)
- **Intended Run Root**: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2_1\20261025_142828_IST\runs`
  - **Arm A Workspace**: `...\runs\A\workspace`, Fixture: `...\runs\A\fixture`, Temp: `...\runs\A\tmp`, Output: `...\runs\A`
  - **Arm B Workspace**: `...\runs\B\workspace`, Fixture: `...\runs\B\fixture`, Temp: `...\runs\B\tmp`, Output: `...\runs\B`
- **Approval Gated Commands** (from `final_gate_v3/approval_gated_commands.json`):
  - **Arm A**: `python.exe -B scripts/phase8_2_1_arm.py --run --plan final_gate_v3/experiment_plan.json --arm A --approved-plan-sha256 7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
  - **Arm B**: `python.exe -B scripts/phase8_2_1_arm.py --run --plan final_gate_v3/experiment_plan.json --arm B --approved-plan-sha256 7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
  *(Neither command was executed).*

---

## 9. Remaining Risks, Blockers & Corrective Actions

### Blocker: Absence of OS-Enforced Sandbox & Network Boundary
- **Risk**: Python audit hooks and file permissions can be bypassed by native extensions, child processes, or concurrent same-account scripts. If a generated patch or model invocation were to exhibit unconstrained behavior, host repository files, benchmarks, or credentials could be accessed or modified. Furthermore, network requests cannot be independently verified as blocked at the OS packet filter / routing level.
- **Minimum Requirement to Unblock**:
  1. **Provision Disposable Isolation**:
     - Execute inside a disposable Virtual Machine (e.g., Hyper-V / KVM / cloud VM) or an unprivileged container environment.
     - Ensure the environment can be destroyed and reconstructed deterministically from an image.
  2. **Enforce OS-Level Read-Only Mounts**:
     - Mount the original repository root, historical evidence directories, and `.hf_cache` as strict read-only (`:ro`) mounts at the OS/hypervisor level.
     - Expose only the specific arm run directory (`runs/A`, `runs/B`) and a designated scratch temp directory as writable mounts.
  3. **Enforce Kernel / Hypervisor Network Cutoff**:
     - Disconnect the virtual NIC or run container with `--network none`.
     - Execute independent network probes (e.g. `ping`, DNS resolution, curl) from outside Python before launch to demonstrate packet drop at the boundary.

---

## 10. Execution Certification Statement

I hereby certify as experimental reproducibility auditor:

1. **Zero (0) coding-model calls** were executed.
2. **Zero (0) experiment arms** (Arm A or Arm B) were started.
3. **Zero (0) candidate patches** were applied or approved.
4. **Zero (0) network requests** were initiated.
5. The historical runner `scripts/phase8_2_arm.py` was **never invoked**.
6. All 2,164 baseline repository files, 122 protected files, and 7 model cache files remain byte-for-byte preserved.
