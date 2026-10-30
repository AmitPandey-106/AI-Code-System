# Phase 8.2.1 execution-gate hardening

Prepared for independent review; execution approval has not been granted. Final deterministic validation: **237 passed, 0 failed, 0 errors, 0 skipped** (152 integration + 17 strategy + 11 original Phase 8.2 + 57 new hardening cases). Coding-model calls: **0**. Actual experiment arms started: **0**. Generated patches applied: **0**.

The current plan is [final_gate_v3/experiment_plan.json](<final_gate_v3/experiment_plan.json>) with canonical JSON digest:

`7430f22335ee09e1f38aa8e6eee1fdd39b1f097058690a00d45bde6f589bc424`

The digest is SHA256 of sorted compact JSON excluding the `plan_sha256` field, using the same convention as the reviewed plan. It is not the pretty-printed file's byte hash. Exact gated commands are in [approval_gated_commands.json](<final_gate_v3/approval_gated_commands.json>); none were executed.

The historical runner and all existing preparation files are preserved byte-for-byte. The new entrypoint is `scripts/phase8_2_1_arm.py`; it never calls the historical worker. The old `scripts/phase8_2_arm.py` still contains the audited defects and must not be used. The old digest `cea4b5a9eaa7b0c763b934f0473ea019efed9d333eeac8f2b82e8adf06c98204` does not authorize the new runner. Two preliminary Phase 8.2.1 plans were preserved, superseded after additional exception-injection review, and now fail current execution-hash validation. See [superseded_plans.json](<superseded_plans.json>).

Branch: `fix/phase8-1-integration`. HEAD: `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395`. No tracked application changes, resets, cleaning, commits, downloads or network requests were performed. The six implementation/test files are new uncommitted files. Existing uncommitted research, source preparation, historical evidence and user data were retained. Fixed handcrafted regression patches operated only in temporary test fixtures; no generated patch was applied.

Historical source fingerprints recorded before work:

- `scripts/phase8_2_arm.py`: `651bd5cd094e3881448ea511220a3db7fe426596862cae0d21f0f147bdfe52fd`
- `scripts/phase8_2_preflight.py`: `c63358bc72eb528d422a04be713cf5a11f0a76dae02c21df53f179b63c116b2f`
- `tests/test_phase8_2_preflight.py`: `6315380c4019afde73c346e2d4a90c8e1ecb537e46352b00d965c74635ff9ec2`

The controls use exclusive creation plus flush/fsync for raw artifacts and unique timestamped events. Worker outcome and parent terminal records live separately; repeated finalization reads the first terminal without rewriting it. Complete plan/arm/revision/task/fixture/prompt/initial-oracle/proposal context is checkpointed before patch review. The fixture is locked through ordinary Python writes until an exact proposal-hash decision is durably recorded; only the target and its atomic-write temporary files can then change. Rejection, invalid proposals, model/API errors, cancellation, test/oracle failures, timeout, child failure and cleanup failures retain their available evidence. Secondary logging/cleanup errors cannot replace the original cancellation or exception. Parent final audit records protected hashes and durable invocation counts even after child failure.

Parent approval precedes output ownership and supervisor creation. On Windows the Job exists before launch, the child starts suspended, and it is assigned before resuming. A secret capability travels only over the child's private stdin pipe; only its hash is stored. It is one-use, expires after 30 seconds, and binds the parent/child PID, run ID, exact plan, task, revision, source, arm and output. A public flag alone cannot authorize a worker. Both CLI and protocol reject arbitrary parameters. Arm B requires Arm A's matching terminal evidence, including a cancelled/failed terminal; success in A is not required.

Each arm independently copies the seven canonical fixture files into its owned workspace, with separate state and temp storage. Both new frozen exports (115 files total) and the master fixture are read-only and have matching before/after hashes. Ordinary Python writes, renames/removals, links, path traversal, reparse/symlink/hardlink aliases, ADS and Windows device/trailing-name aliases fail closed outside the allowed workspace. Evidence permits exclusive creation only. Frozen source and tests are unchanged.

The frozen oracle function and benchmark assertions remain identical. A common guarded pytest transport now supplies the same 30-second supervised execution for both native test calls and the frozen independent oracle. This is an explicit adapter change: the model-free transport test reproduces the original **one passing basic-route test and one failing hyphenated-slug assertion**, without modifying fixture bytes. It does not measure differences between the frozen native subprocess implementations. Actual filesystem-guard tests use a fixed child, and process-job tests use a fixed sleeping child; neither starts an experiment arm. Model/call-limit tests use fixed doubles and token-shaped test objects.

Final control checklist (PASS refers to implementation plus deterministic tests):

| Control | Status | Evidence / reference |
|---|---|---|
| Plan identity and pinned inputs | PASS | Read-only final validation; unchanged task/revisions/model/fixtures/prompt/oracle/settings; final execution file hashes bound. [phase8_2_1_arm.py::validate_plan](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:49>) |
| Independent fixtures and per-arm state | PASS | Exclusive arm ownership; byte copies of canonical fixture; separate workspace/fixture/state/tmp/evidence/control. [phase8_2_1_arm.py::experiment_worker](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:215>) |
| Independent hyphenated-slug oracle | PASS | Trusted canonical oracle transport reproduces one pass and one slug assertion failure without changing fixture bytes; syntax/model text alone cannot pass. [phase8_2_1_arm.py::classify](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:202>) |
| One call, 768 tokens, zero retries | PASS | Boundary and real-generation guards; 769 rejected before invocation; second call rejected; max_attempts=1; fallback reuses response. [phase8_2_1_arm.py::GenerationBudget](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:149>) |
| Offline local loader; ordinary Python network guard | PASS | Cached snapshot verified (7 files); local_files_only; offline flags; connect/bind/DNS denied by audit policy. No network service. [phase8_2_1_controls.py::WritePolicy](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py:181>) |
| Blocking patch approval and durable checkpoint | PASS | Complete context/initial oracle/fixture/prompt/proposal hashes fsynced before review request. Fixture writes locked; exact hash unlocks target only. [phase8_2_1_controls.py::review_proposal](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py:335>) |
| Append-only raw evidence and terminal lifecycle | PASS | Exclusive raw prompt/response/proposal records and timestamped events; errors/rejection/failure retained; repeated finalize leaves prior bytes unchanged. [phase8_2_1_controls.py::Evidence](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py:110>) |
| Cancellation/error/timeout/cleanup preservation | PASS | Distinct terminal states and original BaseExceptions preserved, including secondary logging/cleanup failures and cancellation during final audit. [phase8_2_1_arm.py::run_parent](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:376>) |
| Internal-worker authorization and supervision | PASS | Exact typed parent approval before claim/job/launch; Windows job created first, child attached suspended; private one-use expiring PID/run/plan-bound capability. [phase8_2_1_controls.py::consume_authorization](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py:158>) |
| Ordinary write isolation and protected hashes | PASS | Traversal/ADS/device/short/symlink/reparse/hardlink aliases rejected; actual guarded-child cross-arm/protected writes denied; new exports read-only; before/after hashes equal. [phase8_2_1_controls.py::canonical](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py:49>) |
| Fixed opt-in and no broader benchmark | PASS | Default inert; public --child rejected; only A/B and canonical task/revisions/output paths accepted; B requires bound A terminal; no benchmark invocation. [phase8_2_1_arm.py::main](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:481>) |
| Historical data and uncommitted preparation preserved | PASS | 2164 starting files, 1934 original-preservation entries and 247 old preparation files rehashed unchanged; no tracked edits; old and new actual arm outputs absent. [phase8_2_1_prepare.py::assert_preserved](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_prepare.py:24>) |
| Hardened OS filesystem/network sandbox | UNVERIFIED | Not implemented or claimed. Python hooks, file attributes, local capability and process jobs do not resist arbitrary malicious native code or a same-account attacker. [phase8_2_1_controls.py::WritePolicy](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py:181>) |
| Real model loading/inference/applied repair outcomes | UNVERIFIED | Intentionally unexecuted. Deterministic controls tests use fixed doubles; no coding-model or actual arm execution is authorized in this task. [phase8_2_1_arm.py::experiment_worker](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:215>) |
| Independent review and execution approval | PENDING | No approval granted. Review this final digest and complete evidence before separately authorizing execution. [phase8_2_1_arm.py::run_parent](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py:376>) |


There is no hardened OS filesystem or network sandbox. Python audit hooks and read-only attributes can be bypassed by arbitrary native code or a malicious local account with the same rights. The pipe capability closes accidental CLI bypass; it is not an OS security boundary. Network requests are disabled in the ordinary Python runner/test path and local Hugging Face loaders use offline/cache-only settings; network isolation has not been independently demonstrated. Trusted canonical tests and any future human-reviewed target code still execute on the host. Parent console input may remain waiting after its watchdog kills a timed-out child; final parent audit resumes when that prompt returns or is cancelled. The child's 300-second cap includes patch review.

Power loss can leave a partial exclusive evidence file; readers fail closed rather than repair/overwrite it. A forced kill between a durable pre-call event and model entry cannot establish exact entry/return atomically: started events are attempted-call upper bounds, returned events and token counts are reported only when available. No successful repair is inferred from interruption, syntax validity, rollback or model text.

Fresh commands, exits, counts, all intermediate failures and source hashes are in [test_results.json](<final_gate_v3/test_results.json>). Phase 8.1 ran its unchanged validator from a new Git-exported candidate copy (`validation_export_01`) so its fixed output names could not replace historical evidence. Its 152 integration and 17 strategy tests both passed; the export source hashes remained unchanged. The last controls command ran both original and new test files: **68 passed** (11 + 57), exit 0. Original Phase 8.1 validation was not repeated after adapter-only edits because its tested frozen sources did not change.

| Controls attempt | Tests | Passed | Failures | Errors | Exit |
|---|---:|---:|---:|---:|---:|
| controls_attempt01 | 51 | 51 | 0 | 0 | 0 |
| controls_attempt02 | 56 | 55 | 1 | 0 | 1 |
| controls_attempt03 | 56 | 55 | 1 | 0 | 1 |
| controls_attempt04 | 56 | 56 | 0 | 0 | 0 |
| controls_attempt05 | 63 | 63 | 0 | 0 | 0 |
| controls_attempt06 | 65 | 65 | 0 | 0 | 0 |
| controls_attempt07 | 68 | 68 | 0 | 0 | 0 |

Attempts 02 and 03 each retained one transport-test failure: pytest capture first attempted the ambient temp directory, then its default logging handler attempted the null device. Both were rejected by the guard. Capture/temp and logging output are now explicitly bound to the owned temp directory. Logs, JUnit, commands and failed fixtures remain in the timestamped directory. No failures remain in final validation.

All required hardening scenarios are covered: unauthenticated direct worker; arbitrary task/revision/output; stale/token/PID/parent/replay/malformed authorization; approval before launch; durable checkpoint before review/apply; rejection without unlocking; cancellation (including final audit); model/API/child/timeout errors; original exceptions with secondary storage/cleanup failure; immutable repeated finalization; existing output collision; cross-arm/protected write attempts; traversal/symlink/hardlink/Windows aliases; unchanged frozen content/modes; preserved oracle defect; actual-call guard and 769-token rejection. No coding-model object was loaded by the hardening tests.

Final execution source bindings:

| Source | SHA256 |
|---|---|
| [phase8_2_1_arm.py](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_arm.py>) | `3d6163bd22da1b8e1268888c6e03b6e477bf994a7d880591c9046df806b933a6` |
| [phase8_2_1_controls.py](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_controls.py>) | `9b4383f1b9fa4fa94ca0901c07f6db1391831bd71b45ee2746e3dbd163547abd` |
| [phase8_2_1_prepare.py](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_prepare.py>) | `e04d68c6197cc3aa8f364ea185fcfcc62c8014142e3e92d4e417a8d81b77d1de` |
| [phase8_2_1_pytest.py](<D:/Amit Stuff/ai-code-system/scripts/phase8_2_1_pytest.py>) | `0f026f6054aeb1194d854f9e36f11d95680018a15b9d1ba0cd73719ec2dfdee0` |
| [phase8_2_1_control_child.py](<D:/Amit Stuff/ai-code-system/tests/phase8_2_1_control_child.py>) | `46e6f1577ebed89670004cdb656b685ddbda61ae05dc840e38226da1f45a1432` |
| [test_phase8_2_1_hardening.py](<D:/Amit Stuff/ai-code-system/tests/test_phase8_2_1_hardening.py>) | `bfc9f426e73e3980ae63c2bd6bf2da0bccb65046e062aa273bb230104f83c3ad` |

The final read-only gate checked the current Python, dependency versions, OS/processor, all cached model bytes, protected trees, source hashes, fixed paths and inherited controls. It verified 2,164 starting files, the earlier 1,934-file preservation manifest and all 247 earlier preparation entries; these overlapping inventories all have zero mismatches. Both historical and new actual-run directories are absent. See [final_readonly_validation.json](<final_gate_v3/final_readonly_validation.json>), [source hashes](<final_gate_v3/source_hash_manifest.json>), [protected hashes](<final_gate_v3/protected_file_hash_manifest.json>), [environment](<environment_manifest.json>) and [created/changed files](<created_changed_files.json>).

The canonical task is `task_01_router_slug_param`. Arm A remains `9ef57511e0e25d58d0f1318e9d73ccb58465ec44`; Arm B remains `920c01aa0d510aa281092e6b55e4ce02b31e584e`. Model: `Qwen/Qwen2.5-Coder-1.5B-Instruct` at revision `2e1fd397ee46e1388853d2af2c993145b0f1098a`. Prompt hash: `9f9ed1d8310e6792670551e66c9348e2192b4992a8df2630cab3a77cbb35af6d`. All seven fixture hashes, frozen oracle function/test hashes, model-cache fingerprints and hardware/generation controls are unchanged from the reviewed plan; only execution infrastructure, evidence location and plan bindings changed.

The proposed trial remains **A then B; exactly one permitted coding-model invocation per arm; at most 768 generated tokens per arm; zero retries; at most two invocations and 1,536 generated tokens total**. Greedy generation, seed 42, repetition penalty 1.1, CPU/float32/eager attention and four Torch threads remain fixed. Native/oracle timeout: 30 seconds; soft generation limit: 180 seconds; supervised child cap: 300 seconds per arm, 600 child-seconds combined. Memory, strategy, LoRA and retrieval remain disabled. Every produced candidate still requires separate hash-confirmed patch review before application.

Implementation hardening is complete for independent review under the stated ordinary-operation limits. Real model loading, inference, patch application and paired outcomes remain intentionally unverified. **Do not execute until independent review and explicit approval of the final digest.**
