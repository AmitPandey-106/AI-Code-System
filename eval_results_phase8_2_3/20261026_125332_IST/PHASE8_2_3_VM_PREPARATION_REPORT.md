# LITE-Coder Phase 8.2.3 — Disposable Windows VM Preparation Report

- **Date / Timestamp**: 2026-10-26T12:53:32+05:30
- **Auditor Role**: Senior Software Reliability Engineer & Experimental Reproducibility Auditor
- **Repository Root**: `D:\Amit Stuff\ai-code-system`
- **Reviewed Plan Digest**: `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`
- **Objective**: Resolve the single confirmed Phase 8.2.2 blocker (absence of OS-enforced isolation) without modifying protected assets, making network requests, or executing experiment arms.

---

## 1. Executive Summary & Verdict

**CURRENT SYSTEM VERDICT: `BLOCKED (PENDING ADMINISTRATOR ACTION)` / `ALTERNATIVE REQUIRED`**  
**UPON ADMINISTRATOR HYPER-V ACTIVATION: `READY FOR VM CREATION`**

### Summary of System Inspection
1. **Hardware Virtualization**: **VERIFIED ACTIVE**. The host CPU (Intel Core i7-10610U, 4 physical cores, 8 threads, 32 GB RAM) has hardware virtualization (`VirtualizationFirmwareEnabled: True`), VM Monitor Mode Extensions, Second Level Address Translation (SLAT), and Data Execution Prevention (DEP) enabled in UEFI firmware.
2. **Windows Edition**: **VERIFIED COMPATIBLE**. The host OS is **Microsoft Windows 11 Pro** (Version `10.0.22621`, SKU 48 / `Professional`), which natively includes Microsoft Hyper-V and Windows Sandbox capabilities without requiring third-party hypervisors.
3. **Current Hyper-V Status**: **DISABLED / UNAVAILABLE**. The Hyper-V hypervisor is currently not running in the root partition (`HypervisorPresent: False`). The `vmms` service, Hyper-V PowerShell module, and Windows Sandbox are not installed.
4. **Elevation Constraint**: Activating Windows Hyper-V requires an elevated Administrator PowerShell prompt to execute `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All` followed by a system restart. In the current unprivileged user session, DISM operations fail with Error 740 (`Elevated permissions are required`).
5. **Disk Storage Observation**: Drive `C:\` has only **5.81 GB** free space. Drive `D:\` has **301.50 GB** free space, and Drive `E:\` has **287.85 GB** free space. All VM disks and staging data must be allocated on Drive `D:\` (`D:\hyperv_vms\`) to avoid system drive exhaustion.

---

## 2. Hyper-V Availability & Alternatives Analysis

| Isolation Architecture | Kernel & Security Boundary | Windows 11 Pro Support | Current Host State | Feasibility & Trade-offs |
|---|---|:---:|:---:|---|
| **Option 1: Native Hyper-V VM (Recommended)** | Type-1 Hardware Hypervisor; isolated OS kernel; zero host device access | Native | **Feature disabled; hardware ready** | **Best for reproducibility**: Preserves exact Windows platform runtime (`Windows-10-10.0.22621-SP0`), discrete hardware vNIC detachment, and true hypervisor-level read-only disk mounts. Requires 1 administrator command + reboot. |
| **Option 2: Windows Sandbox (`.wsb`)** | Lightweight containerized desktop VM; auto-disposable | Native | **Feature disabled** | Also requires elevation to enable feature (`Containers-DisposableClientVM`). Runs in interactive user session; ephemeral state is destroyed immediately on window close, risking loss of run evidence if not mapped to an external output folder. |
| **Option 3: WSL 2 (Linux Container)** | Linux kernel namespace isolation (`--network none`, `:ro`) | Requires WSL | **WSL not installed** | **Incompatible / Severe Drift**: Violates the reviewed platform specification. The tested baseline and candidate code, Windows Job Object controls, and Python runtime are tailored for Windows. Switching to Linux invalidates the plan digest. |
| **Option 4: Type-2 Hypervisor (VirtualBox/VMware)** | Type-2 Hypervisor running in user space | Third-party | **Not installed** | Unnecessary third-party software download and installation when Windows 11 Pro natively includes enterprise-grade Type-1 Hyper-V. |

**Conclusion**: Native Windows Hyper-V (Option 1) is the only option that simultaneously provides an OS security boundary, satisfies network cutoff at the virtual hardware layer, and preserves byte-for-byte platform compatibility with the reviewed experiment plan.

---

## 3. Proposed Disposable Hyper-V VM Specification

### VM Hardware Configuration
- **VM Name**: `LITECODER-PHASE8-RUNNER`
- **Generation**: Generation 2 (UEFI, Secure Boot enabled)
- **Virtual Processors**: **4 vCPUs** (matches `torch_threads: 4` and physical core count)
- **Memory**: **8,192 MB** static RAM (Dynamic Memory explicitly **Disabled** to eliminate memory paging latency fluctuations)
- **Virtual Network Adapters**: **NONE** (No virtual switch, no network adapter attached; network disconnection is enforced at the virtual hardware bus)
- **Integration Services**: Heartbeat and Shutdown only. **Guest Service Interface (VMBus file copy) disabled**; Enhanced Session Mode disabled (no host drive redirection, clipboard sharing, or RDP device access).

### Storage Topology & Isolation Architecture
The VM will be configured with three completely separated virtual drives:

```
[ Host Storage (Drive D:) ]
   |
   +-- D:\hyperv_vms\base_win11_template.vhdx  (Base pristine OS template, untouched)
   |      ^
   |      +-- D:\hyperv_vms\litecoder_os_diff.vhdx  (Differencing disk - disposable, destroyed post-run)
   |
   +-- D:\hyperv_vms\litecoder_inputs_ro.vhdx  (Attached as READ-ONLY SCSI disk / ISO to Guest E:\)
   |      * Hash-verified model snapshot (.hf_cache, 3.10 GB)
   |      * Python 3.10 venv & 7 critical dependencies (1.23 GB)
   |      * Canonical fixture & source exports (baseline & candidate)
   |      * Execution adapters & experiment plan
   |
   +-- D:\hyperv_vms\litecoder_output.vhdx  (Attached as dedicated writable SCSI disk to Guest W:\)
          * W:\runs\A (Arm A exclusive workspace)
          * W:\runs\B (Arm B exclusive workspace)
          * W:\tmp    (Temporary scratch directory)
```

1. **Guest OS Drive (`C:\`)**: Differencing VHDX. All operating system writes, Windows event logs, and pagefile changes remain isolated to this differencing disk. Post-experiment, this disk is deleted.
2. **Guest Input Drive (`E:\`)**: Attached as a **Read-Only SCSI disk** or ISO-9660 volume at the Hyper-V level. The guest OS and runner process cannot modify the source exports, model weights, or fixtures even if compromised.
3. **Guest Output Drive (`W:\`)**: A dedicated 10 GB VHDX. The experiment worker writes solely to `W:\runs\A` and `W:\runs\B`.

---

## 4. Offline Input Transfer Plan (Zero-Download Verification)

Every byte required for execution is transferred directly from local host storage on Drive `D:\` without making any network requests:

1. **Asset Staging Directory**: Create local staging directory `D:\hyperv_staging\litecoder_input_tree\`:
   - Copy model snapshot from `D:\Amit Stuff\ai-code-system\.hf_cache\models--Qwen--Qwen2.5-Coder-1.5B-Instruct\snapshots\2e1fd397ee46e1388853d2af2c993145b0f1098a\` (7 files, 3,099,021,808 bytes).
   - Copy Python virtual environment from `D:\Amit Stuff\ai-code-system\venv\` (1.23 GB).
   - Copy canonical fixture from `eval_results_phase8_2_1\20261025_142828_IST\canonical_fixture\` (7 files).
   - Copy baseline export from `eval_results_phase8_2_1\20261025_142828_IST\exports\baseline\` (57 files).
   - Copy candidate export from `eval_results_phase8_2_1\20261025_142828_IST\exports\candidate\` (58 files).
   - Copy execution adapters: `phase8_2_1_arm.py`, `phase8_2_1_controls.py`, `phase8_2_1_pytest.py`, `phase8_2_1_control_child.py`.
   - Copy reviewed plan and manifests: `experiment_plan.json`, `source_hash_manifest.json`, `protected_file_hash_manifest.json`, `approval_gated_commands.json`, `common_model_prompt.txt`.
2. **Packaging**: Generate read-only VHDX `D:\hyperv_vms\litecoder_inputs_ro.vhdx` (or ISO image) using PowerShell / diskpart.
3. **Integrity Validation**: Recalculate SHA-256 for all staged files prior to packaging. Confirm 100% hash parity with host records.
4. **Preservation**: The original host repository, `.hf_cache`, and historical evidence directories are **never** shared, mounted, or exposed to the VM.

---

## 5. In-Guest Independent Verification Protocol

Prior to authorizing or running either experiment arm inside the guest VM, an automated in-guest preflight script (`guest_preflight_audit.py`) will execute:

1. **Network Disconnection Enforcement**:
   - `Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }` -> Must return **zero adapters**.
   - `Test-NetConnection -ComputerName 8.8.8.8 -WarningAction SilentlyContinue` -> Must fail.
   - `Resolve-DnsName huggingface.co -ErrorAction SilentlyContinue` -> Must fail.
   - Socket creation probe (`socket.create_connection(('8.8.8.8', 80), timeout=2)`) -> Must raise `OSError: Network unreachable`.
2. **Read-Only Input Verification**:
   - Attempt write to input drive: `[System.IO.File]::WriteAllText("E:\probe.tmp", "test")`.
   - Must fail with `IOException: The media is write protected`.
3. **Cryptographic Checksum Verification**:
   - Recompute SHA-256 for all 6 execution sources against `source_hash_manifest.json`.
   - Recompute SHA-256 for all 7 model snapshot files against `experiment_plan.json`.
   - Recompute canonical JSON digest of `E:\final_gate_v3\experiment_plan.json`. Confirm exact match with `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`.
4. **Environment Isolation Verification**:
   - Confirm `TMP` and `TEMP` environment variables resolve strictly to `W:\tmp`.
   - Confirm `runs` directory resolves strictly to `W:\runs`.

---

## 6. Preservation of Reviewed Experimental Controls

The proposed VM architecture preserves all reviewed parameters without drift:
- **Canonical Task**: `task_01_router_slug_param`
- **Arm A Revision**: `9ef57511e0e25d58d0f1318e9d73ccb58465ec44` (Baseline)
- **Arm B Revision**: `920c01aa0d510aa281092e6b55e4ce02b31e584e` (Candidate)
- **Model Revision**: `Qwen/Qwen2.5-Coder-1.5B-Instruct` at `2e1fd397ee46e1388853d2af2c993145b0f1098a`
- **Model Prompt Hash**: `9f9ed1d8310e6792670551e66c9348e2192b4992a8df2630cab3a77cbb35af6d`
- **Generation Settings**: Greedy (`do_sample: false`), max 768 new tokens, repetition penalty 1.1, seed 42, CPU float32, eager attention, 4 torch threads.
- **Budgets & Caps**: Maximum 1 model call per arm, zero retries, maximum 2 model calls total, 30s test timeout, 300s arm timeout.
- **Plan Digest**: Fixed at `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`.

---

## 7. VM Disposal & Evidence Extraction Procedure

1. **Power Off Guest**:
   ```powershell
   Stop-VM -Name "LITECODER-PHASE8-RUNNER" -TurnOff
   ```
2. **Mount Output Disk on Host in Read-Only Mode**:
   ```powershell
   Mount-VHD -Path "D:\hyperv_vms\litecoder_output.vhdx" -ReadOnly
   ```
3. **Extract Runs & Hash Verification**:
   - Copy `runs/A` and `runs/B` from the mounted VHD volume into `eval_results_phase8_2_1\20261025_142828_IST\runs\`.
   - Verify terminal records, prompt/response SHA-256 hashes, and generated patch approvals against the plan.
4. **Dismount Output VHD**:
   ```powershell
   Dismount-VHD -Path "D:\hyperv_vms\litecoder_output.vhdx"
   ```
5. **Disposable VM Destruction**:
   ```powershell
   Remove-VM -Name "LITECODER-PHASE8-RUNNER" -Force
   Remove-Item -Path "D:\hyperv_vms\litecoder_os_diff.vhdx" -Force
   ```
   *(The base template `base_win11_template.vhdx` and read-only inputs image `litecoder_inputs_ro.vhdx` remain unmodified).*

---

## 8. Required Administrator Actions (Prior to VM Creation)

Because Hyper-V is currently not enabled in Windows, the following administrative commands must be executed by the user in an **Elevated Administrator PowerShell Prompt**:

```powershell
# Run in Administrator PowerShell:
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All -NoRestart
Restart-Computer
```

*Note: No privileged commands have been executed. The environment remains completely untouched in read-only audit state.*

---

## 9. Final Execution Statement

As reproducibility auditor, I certify:
1. Zero (0) coding-model calls were executed.
2. Zero (0) experiment arms were started.
3. Zero (0) candidate patches were applied.
4. Zero (0) network requests were made.
5. Historical runner `scripts/phase8_2_arm.py` was **never invoked**.
6. No virtualization features were modified, no software was installed, and no VM was created or destroyed during this inspection.

**Stop condition met: Awaiting user approval and direction.**
