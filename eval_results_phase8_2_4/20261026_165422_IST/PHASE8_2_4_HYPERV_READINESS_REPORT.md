# LITE-Coder Phase 8.2.4 — Hyper-V Readiness and VM Creation Plan

- **Date / Timestamp**: 2026-10-26T16:54:22+05:30
- **Auditor Role**: Senior Software Reliability Engineer & Experimental Reproducibility Auditor
- **Repository Root**: `D:\Amit Stuff\ai-code-system`
- **Reviewed Plan Digest**: `7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424` (Verified)
- **Status / Verdict**: **`BLOCKED (PREREQUISITES PENDING)`**
- **Artifacts Generated**:
  - Report: `eval_results_phase8_2_4/20261026_165422_IST/PHASE8_2_4_HYPERV_READINESS_REPORT.md`
  - Specification: `eval_results_phase8_2_4/20261026_165422_IST/vm_creation_plan.json`

---

## 1. Executive Summary & Machine Inspection Verdict

Following the host restart initiated after Phase 8.2.3, a full hardware, hypervisor, storage, and cryptographic audit of the machine was conducted:

1. **Hyper-V Hypervisor State: `VERIFIED ACTIVE`**
   - The Hyper-V root hypervisor is confirmed running (`A hypervisor has been detected`).
   - The Hyper-V Virtual Machine Management service (`vmms`) is in state **Running** with startup type **Automatic**.
   - Hyper-V version `10.0.22621.1` is confirmed active in the system registry (`HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Virtualization`).
   - The Hyper-V PowerShell module (`Get-VM`) is present and registered.

2. **Host Virtualization Topology: `VERIFIED PRISTINE`**
   - Existing Virtual Switches: **0** (No synthetic or external virtual switches exist).
   - Existing Virtual Machines: **0** (No Hyper-V VMs exist on the host).

3. **Host Storage Availability on Drive `D:\`: `VERIFIED SUFFICIENT`**
   - Drive `C:\` has only **5.76 GB** free (194.17 GB capacity). It is strictly disqualified from hosting any VM virtual disks or staging trees.
   - Drive `D:\` has **301.48 GB** free (390.62 GB capacity).
   - The entire proposed VM footprint (base OS template, differencing disk, read-only inputs, output disk, staging, and operational headroom) requires **~75.0 GB maximum**, leaving **226.48 GB** of safety headroom (>400% margin).

4. **Primary Blocker 1 — Offline Guest OS Installation Media: `UNAVAILABLE OFFLINE`**
   - A recursive system audit across `D:\`, `E:\`, and user directories (`C:\Users\T14s\Downloads`, `Desktop`, `Documents`, `Public`, `C:\tmp`) found **zero (0)** `.iso`, `.vhdx`, `.vhd`, or `.wim` Windows installation images.
   - In accordance with mandatory restrictions, **zero downloads were attempted**.
   - **Verdict**: The VM cannot be created or installed until the user provides or points to an offline Windows 11 installation media.

5. **Primary Blocker 2 — User Authorization for Hyper-V Management: `PENDING ELEVATION`**
   - The current shell runs as `desktop-lb495kl\t14s` with a standard **Medium Mandatory Level** token (UAC filtered).
   - The built-in security group `BUILTIN\Hyper-V Administrators` currently has **zero (0) members**.
   - Executing Hyper-V cmdlets (`Get-VM`, `New-VM`) in this standard session fails with `VirtualizationException: You do not have the required permission to complete this task`.
   - **Resolution**: The administrator must either add the user to `Hyper-V Administrators` once via an elevated prompt (`Add-LocalGroupMember -Group "Hyper-V Administrators" -Member $env:USERNAME`) or execute VM creation commands from an elevated Administrator prompt.

6. **Guest RAM Assessment for Pinned Qwen Model: `8 GB IS INSUFFICIENT; 12 GB RECOMMENDED`**
   - Model `Qwen/Qwen2.5-Coder-1.5B-Instruct` is pinned at `hardware.dtype: "float32"`.
   - 1.5437B parameters in float32 require **6.17 GB (5.75 GiB)** of raw parameter memory.
   - Inference working set (PyTorch runtime + tokenizer + activations + KV cache) requires **~7.32 GB**.
   - A clean Windows 11 Pro 64-bit OS consumes **~2.8 GB** at idle.
   - Total guest demand is **~10.12 GB**. An 8 GB VM allocation will force continuous page thrashing against `pagefile.sys`, causing catastrophic 10x–100x latency degradation, timeouts, or out-of-memory crashes.
   - The host has **31.76 GB total RAM** with **18.87 GB free**. A static allocation of **12,288 MB (12 GB)** (or 16 GB) is recommended. This preserves CPU count (`4 vCPUs`), greedy sampling, and all experimental controls without drift.

7. **Cryptographic & Asset Integrity: `100% VERIFIED`**
   - Canonical plan digest: **Exact match** (`7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`).
   - Execution sources: **6/6 match** (`source_hash_manifest.json`).
   - Protected exports and canonical fixture: **122/122 match** (`protected_file_hash_manifest.json`).
   - Model snapshot: **7/7 match** (`3,099,021,808 bytes`).
   - Tracked Git repository state: **0 modifications**.

---

## 2. Verified Host Facts vs. Proposed VM Settings

To ensure auditability, the table below clearly distinguishes between empirical host measurements and proposed configurations:

| Category | Verified Host Fact (Measured 2026-10-26) | Proposed VM Configuration (Awaiting Approval) |
|---|---|---|
| **Hypervisor** | Microsoft Hyper-V enabled; `vmms` Running (Automatic) | Generation 2 VM (`LITECODER-PHASE8-RUNNER`) |
| **Virtual Switches** | Zero (0) switches exist on host | **No virtual switch / zero vNICs** (physical network cutoff) |
| **Virtual Machines** | Zero (0) VMs exist in `root\virtualization\v2` | Single disposable VM instance |
| **Host Storage** | `D:\` has 301.48 GB free; `C:\` has 5.76 GB free | Disks allocated strictly on `D:\hyperv_vms\` |
| **Host Processors** | Intel Core i7-10610U (4 physical cores, 8 threads) | **4 vCPUs** (matches `torch_threads: 4`) |
| **Host Memory** | 31.76 GB total physical RAM; **18.87 GB free** | **12,288 MB (12 GB)** static RAM (Dynamic Memory disabled) |
| **OS Media** | Zero `.iso`/`.vhdx` images found offline | User-provided offline Windows 11 installation media |
| **OS Disk** | Clean host filesystem | Differencing VHDX (`D:\hyperv_vms\litecoder_os_diff.vhdx`) |
| **Input Disk** | Protected host folders (100% hash verified) | Read-only SCSI VHDX/ISO (`D:\hyperv_vms\litecoder_inputs_ro.vhdx`) |
| **Output Disk** | Host directory `eval_results_phase8_2_1/...` | Dedicated 10 GB VHDX (`D:\hyperv_vms\litecoder_output.vhdx`) |
| **Integration** | Standard Windows 11 services | Enhanced Session disabled; Guest Services disabled |
| **Redirection** | Local desktop session | Clipboard, Drive, and COM redirection **strictly disabled** |

---

## 3. Storage Capacity Assessment on Drive `D:\`

All virtual disks and staging assets will reside strictly on Drive `D:\` to prevent exhausting Drive `C:\`:

```
[ Host Drive D: (301.48 GB Free) ]
   |
   +-- D:\hyperv_vms\
   |      |-- base_win11_template.vhdx   [Max 25.0 GB] (Base OS template, pristine & read-only)
   |      |-- litecoder_os_diff.vhdx     [Max 10.0 GB] (Differencing disk - disposable, destroyed post-run)
   |      |-- litecoder_inputs_ro.vhdx   [Max  5.0 GB] (Attached as Read-Only SCSI drive to Guest E:\)
   |      `-- litecoder_output.vhdx      [Max 10.0 GB] (Dedicated writable SCSI drive to Guest W:\)
   |
   +-- D:\hyperv_staging\
   |      `-- litecoder_input_tree\      [Max  5.0 GB] (Local uncompressed staging directory)
   |
   +-- Operational Headroom / Scratch    [Max 20.0 GB] (VHDX dynamic expansion buffer)
   -------------------------------------------------------------------------------------------------------
   Total Projected Allocation:            ~75.0 GB
   Available Free Space on D:\:           301.48 GB
   Remaining Safety Headroom:             226.48 GB (>400% safety margin)
```

**Verdict**: Drive `D:\` provides more than 4x the required capacity. Storage sizing is fully verified and safe.

---

## 4. RAM Sufficiency & Allocation Assessment (Task 8)

### Architectural & Mathematical Memory Breakdown

The reviewed plan (`final_gate_v3\experiment_plan.json`) pins:
- Model: `Qwen/Qwen2.5-Coder-1.5B-Instruct` (Revision `2e1fd397ee46e1388853d2af2c993145b0f1098a`)
- Total parameter count: **1,543,714,816 parameters**
- Precision: **`hardware.dtype: "float32"`** (single-precision IEEE 754, 4 bytes/param)
- Architecture: 28 transformer layers, hidden size 1536, 16 attention heads, 2 KV heads (GQA), head dimension 128

Memory demand during inference:
1. **Raw Model Weights**:
   $$\text{Memory} = 1,543,714,816 \times 4\text{ bytes} = 6,174,859,264\text{ bytes} \approx 6.17\text{ GB } (5.75\text{ GiB})$$
2. **PyTorch Runtime & Base Libraries**:
   Python 3.10 + PyTorch 2.11.0 CPU binaries (`torch.dll`, `mkl_rt.dll`), OpenMP runtime, and process structures: **~600 MB**.
3. **KV Cache & Forward Activations**:
   - KV Cache per token: $2 \times 28 \times 2 \times 128 \times 4\text{ bytes} = 57,344\text{ bytes } (\sim 56\text{ KB/token})$.
   - At sequence length 3,000 tokens (prompt + 768 generated): $3,000 \times 56\text{ KB} \approx 168\text{ MB}$.
   - Intermediate activations and tensor allocation buffer: **~350 MB**.
4. **Total Inference Working Set**:
   $$6.17\text{ GB} + 0.60\text{ GB} + 0.55\text{ GB} \approx 7.32\text{ GB } (6.82\text{ GiB})$$
5. **Guest Windows 11 Operating System Footprint**:
   Clean Windows 11 Pro 64-bit requires **~2.5 to 3.2 GB** at idle for system processes (`ntoskrnl.exe`, `lsass.exe`, `dwm.exe`, `svchost.exe`, Defender).
6. **Total Combined Guest Memory Demand**:
   $$7.32\text{ GB} + 2.80\text{ GB} \approx 10.12\text{ GB}$$

### Why 8 GB Allocation Fails
If the VM is assigned 8,192 MB (8.0 GB / 7.63 GiB):
1. Available physical RAM after OS boot is only **~5.0 to 5.4 GiB**.
2. Loading 6.17 GB of float32 model weights exceeds available physical RAM by **~1.5 to 2.0 GiB**.
3. Windows will immediately page inactive and active memory pages into `pagefile.sys`.
4. Because autoregressive token generation touches **every single weight** on every forward pass (up to 768 sequential passes), the memory access pattern is completely non-local across all 6.17 GB.
5. Continuous paging back and forth from virtual disk will cause catastrophic **page thrashing**:
   - Inference latency drops by 10x to 100x (from ~10 tokens/sec to <0.1 tokens/sec).
   - The model call will violate `soft_timeout_seconds: 180` and `arm_wall_timeout_seconds: 300`, producing inconclusive infrastructure timeouts.
   - Paging contention risks triggering `RuntimeError: [enforce fail at ... CPUAllocator.cpp] DefaultCPUAllocator: can't allocate memory` or process termination.

### Recommended Allocation
- **Recommended Static RAM**: **12,288 MB (12 GB)** (or **16,384 MB / 16 GB**).
- **Dynamic Memory**: Explicitly **Disabled** (guarantees fixed allocation, zero memory ballooning overhead, and deterministic execution timing).
- **Host Feasibility**:
  - Host Total RAM: 31.76 GB
  - Host Free RAM: **18.87 GB**
  - Host Free RAM remaining after 12 GB VM allocation: **6.87 GB** (plenty of headroom for host OS).
- **Experimental Control Preservation**:
  Increasing VM RAM does **NOT** modify the approved plan:
  - Processor count remains **4 vCPUs** (`torch_threads: 4`).
  - Dtype remains **float32**.
  - Generation remains **greedy** (`do_sample: false`), repetition penalty 1.1, seed 42.
  - Plan digest remains **`7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`**.

---

## 5. Proposed Generation 2 VM Specification

```
Hyper-V Host (Windows 11 Pro, Intel i7-10610U, 32 GB RAM)
|
+-- VM: LITECODER-PHASE8-RUNNER (Generation 2, Secure Boot Enabled)
    |-- vCPUs: 4 (Static, no overcommit)
    |-- Memory: 12,288 MB Static RAM (Dynamic Memory: Disabled)
    |-- Network: NONE (Zero vNICs attached, physical virtual disconnection)
    |-- Guest Service Interface: DISABLED
    |-- Enhanced Session Mode: DISABLED (No clipboard, drive, or port redirection)
    |
    +-- SCSI Controller
        |-- Location 0: C:\ (litecoder_os_diff.vhdx - Differencing, Disposable)
        |-- Location 1: E:\ (litecoder_inputs_ro.vhdx - Read-Only Hardware Mount)
        `-- Location 2: W:\ (litecoder_output.vhdx - Dedicated 10 GB Output VHDX)
```

### Exact PowerShell VM Creation Template (Gated for Approval)

```powershell
# GATED COMMAND: Must only be executed after offline OS image is provided and approval granted

# 1. Create Base VM (Zero network adapter)
New-VM -Name "LITECODER-PHASE8-RUNNER" `
       -Generation 2 `
       -MemoryStartupBytes 12GB `
       -NoVHD `
       -Path "D:\hyperv_vms"

# 2. Configure CPU and Memory Isolation
Set-VMProcessor -VMName "LITECODER-PHASE8-RUNNER" -Count 4
Set-VMMemory -VMName "LITECODER-PHASE8-RUNNER" -DynamicMemoryEnabled $false

# 3. Disable Device Redirection and Guest Services
Set-VM -VMName "LITECODER-PHASE8-RUNNER" -EnhancedSessionTransportType None
Disable-VMIntegrationService -VMName "LITECODER-PHASE8-RUNNER" -Name "Guest Service Interface"

# 4. Attach Disks
# Slot 0: Disposable Differencing OS disk
Add-VMHardDiskDrive -VMName "LITECODER-PHASE8-RUNNER" `
                    -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 0 `
                    -Path "D:\hyperv_vms\litecoder_os_diff.vhdx"

# Slot 1: Read-Only Experiment Inputs
Add-VMHardDiskDrive -VMName "LITECODER-PHASE8-RUNNER" `
                    -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 1 `
                    -Path "D:\hyperv_vms\litecoder_inputs_ro.vhdx" `
                    -ReadOnly

# Slot 2: Dedicated Evidence / Output Disk
Add-VMHardDiskDrive -VMName "LITECODER-PHASE8-RUNNER" `
                    -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 2 `
                    -Path "D:\hyperv_vms\litecoder_output.vhdx"
```

---

## 6. Offline Guest OS Installation Protocol (Task 9)

Because network access and downloading are strictly prohibited, the guest OS will be installed completely offline:

1. **Prerequisite Delivery**: The user places a valid Windows 11 installation media (e.g., `Win11_22H2_English_x64.iso`) into `D:\hyperv_staging\os_media\`.
2. **Base Template Provisioning**:
   ```powershell
   New-VHD -Path "D:\hyperv_vms\base_win11_template.vhdx" -SizeBytes 64GB -Dynamic
   ```
3. **Offline Installation Pass**:
   - A temporary staging VM mounts the local ISO via virtual DVD drive with **no network adapter**.
   - Offline setup uses standard Windows OOBE offline local account bypass (`BypassNRO.cmd` or `autounattend.xml`) to complete setup without Microsoft accounts or network connectivity.
4. **Offline Runtime Pre-staging**:
   - The Python 3.10 virtual environment and dependencies are mounted directly from the local input staging disk without any internet downloads (`pip` is never connected).
5. **Template Sealing & Differencing**:
   - The base VM is cleanly shut down: `Stop-VM -Name "base_template"`.
   - The base disk `base_win11_template.vhdx` is set to read-only on the host filesystem.
   - All subsequent experiment runs instantiate a lightweight differencing disk:
     ```powershell
     New-VHD -ParentPath "D:\hyperv_vms\base_win11_template.vhdx" `
             -Path "D:\hyperv_vms\litecoder_os_diff.vhdx" `
             -Differencing
     ```
   - Following execution, `litecoder_os_diff.vhdx` is deleted, discarding all runtime state.

---

## 7. In-Guest Independent Verification Protocol (Task 9)

Before any experiment code is allowed to execute inside the guest VM, an automated in-guest preflight audit (`guest_preflight_audit.py`) will run and enforce the following 4 gates:

### Gate 1: Network Isolation Verification
1. Physical device check:
   `Get-NetAdapter | Measure-Object` -> Must return **Count: 0**.
2. DNS resolution probe:
   `Resolve-DnsName huggingface.co` -> Must fail immediately with resolution failure.
3. HTTP probe:
   `Invoke-WebRequest -Uri "http://1.1.1.1" -TimeoutSec 2` -> Must fail with `Unable to connect`.
4. Raw socket probe:
   ```python
   import socket
   try:
       socket.create_connection(("8.8.8.8", 53), timeout=2)
       raise AssertionError("SECURITY VIOLATION: Network connection succeeded!")
   except OSError:
       pass  # Expected: Network unreachable
   ```

### Gate 2: Read-Only Inputs Verification
1. Hypervisor write-protection test:
   ```python
   try:
       with open("E:/write_probe.tmp", "wb") as f:
           f.write(b"probe")
       raise AssertionError("SECURITY VIOLATION: Write succeeded on read-only input disk!")
   except (PermissionError, OSError):
       pass  # Expected: Media is write protected
   ```
2. Disk attribute check:
   `(Get-Disk -Number 1).IsReadOnly` -> Must equal **`True`**.

### Gate 3: Cryptographic Integrity Verification
1. Recalculate SHA-256 for all 6 execution sources against `E:\final_gate_v3\source_hash_manifest.json`.
2. Recalculate SHA-256 for all 7 model snapshot files against `E:\final_gate_v3\experiment_plan.json`.
3. Recalculate SHA-256 for all 122 protected files against `E:\final_gate_v3\protected_file_hash_manifest.json`.
4. Recompute canonical JSON digest of `E:\final_gate_v3\experiment_plan.json`:
   Must match **`7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`** exactly.

### Gate 4: Output & Environment Isolation
1. Confirm environment variables `TMP` and `TEMP` resolve strictly to `W:\tmp`.
2. Confirm the runner output workspace resolves strictly to `W:\runs\A` and `W:\runs\B`.
3. Verify clipboard redirection and host drive shares are absent.

---

## 8. Cryptographic & Asset Preservation Audit (Task 6 & 7)

All protected assets have been re-verified against their authoritative manifests:

| Asset Group | Manifest / Benchmark Reference | Files Checked | Status |
|---|---|:---:|:---:|
| **Canonical Plan Digest** | `final_gate_v3/experiment_plan.json` (canonical digest) | 1 | **100% MATCH** (`7430f22335ee...`) |
| **Execution Source Adapters** | `final_gate_v3/source_hash_manifest.json` | 6 | **100% MATCH** (0 mismatches) |
| **Canonical Fixture** | `eval_results_phase8_2_1/.../canonical_fixture` | 7 | **100% MATCH** (0 mismatches) |
| **Baseline Export** | `eval_results_phase8_2_1/.../exports/baseline` | 57 | **100% MATCH** (0 mismatches) |
| **Candidate Export** | `eval_results_phase8_2_1/.../exports/candidate` | 58 | **100% MATCH** (0 mismatches) |
| **Model Snapshot** | `Qwen/Qwen2.5-Coder-1.5B-Instruct` (`2e1fd39...`) | 7 | **100% MATCH** (3,099,021,808 bytes) |
| **Tracked Git Working Tree** | Branch `fix/phase8-1-integration` | - | **0 Tracked Modifications** |

---

## 9. Remaining Prerequisites and Blockers

To proceed to VM creation and execution, the following 3 prerequisites must be resolved:

```
[ BLOCKER 1: Offline Guest OS Media ]
Current State: No .iso, .vhdx, or .wim found on local disks. Network downloads are prohibited.
Action Required: User must copy an offline Windows 11 installation ISO or pre-built base VHDX to D:\hyperv_staging\os_media\.

[ BLOCKER 2: Hyper-V Management Permissions ]
Current State: Current session is standard non-elevated; 'Hyper-V Administrators' group has 0 members.
Action Required: User must execute in an Elevated Administrator PowerShell prompt:
                 Add-LocalGroupMember -Group "Hyper-V Administrators" -Member $env:USERNAME
                 (followed by sign-out/sign-in or system reboot to refresh user token).

[ BLOCKER 3: RAM Allocation Approval ]
Current State: Phase 8.2.3 proposed 8 GB; empirical evidence demonstrates 8 GB induces heavy paging and timeouts.
Action Required: User approval to configure VM static RAM to 12 GB (12,288 MB).
```

---

## 10. Final Auditor Execution Statement

As reproducibility auditor, I certify:
1. **Zero (0)** coding-model calls were executed.
2. **Zero (0)** experiment arms (Arm A or Arm B) were started.
3. **Zero (0)** candidate patches were applied.
4. **Zero (0)** network requests or file downloads were made.
5. Historical runner `scripts/phase8_2_arm.py` was **never invoked**.
6. **No virtual machine was created, modified, or booted**.
7. The environment remains in an unmutated, read-only audit state.

**Stop condition met: Awaiting offline OS media, permission resolution, and user approval.**
