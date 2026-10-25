# Phase 8.1 engineering plan and durable log

Started 2026-10-25 (Asia/Calcutta). Starting branch `audit/phase8-evidence`,
HEAD `e46b2f1d36beac4f46abd09d6d75ce7bfea7f449`. Historical baseline
`9ef57511e0e25d58d0f1318e9d73ccb58465ec44` exists. Work branch
`fix/phase8-1-integration`. No tracked modifications at entry. Existing untracked
research, datasets, packages and scripts are user work: leave them untouched.
`eval_results_phase8_1/preserved_files.json` records 1,728 original files
(180,711,405 bytes), including the historical Phase 8 archive.

## Actual dependency and data flow

`frontend/index.html` -> `frontend/server.py` proxy -> FastAPI `app/main.py`
-> `SessionManager` -> `EngineeringSession` -> `RepoIndexer` / `RepairMemory`
/ `StrategySelector` -> `app.model.generate_raw` -> patch extraction ->
`PatchEngine` dry run -> human approval (hash-bound) -> disk application ->
`ProjectTestRunner` -> diagnosis and bounded retry -> verification -> learning.
`MultiFileEngineeringOrchestrator` constructs sequential sessions and runs final
tests. The historical benchmark and Colab runner invoke these same classes.

Ownership: manager owns in-memory session lookup; session owns attempts, proposal,
source hashes and public status; patch engine owns parsing/application; runner owns
subprocesses; memory owns JSON/FAISS; selector owns JSON rewards. Sessions currently
disappear on server restart. Global model and embedding caches are process-local.
FAISS and transformers are installed in `venv`; no new graph dependency is needed.

## Prioritized findings (source inspected before edits)

| Priority | Root cause and evidence | Change / dependency |
| --- | --- | --- |
| Critical | Loop directly assigns states; `step()` can run concurrently; errors after mutation do not restore files | Explicit transition graph, worker guard, exact-byte transaction and rollback |
| Critical | Runner denies a few flags but accepts `-p`, arbitrary option prefixes and executable paths; inherits plugin/environment settings; captures unlimited output before truncation | Structured pytest allowlist, trusted executable, isolated config/environment, bounded capture, process-tree cancellation |
| Critical | Multi-file orchestrator auto-approves; target-only instruction is only prompt text; snapshot paths unchecked; rollback errors suppressed | Explicit approval callback, target enforcement, validated transaction, verified rollback |
| Critical | Patch engine writes files one at a time without restoring after later I/O errors; missing-file stale checks skipped; unified diff decodes with replacement and lacks syntax checks | Shared transaction writer, full hash coverage, strict UTF-8 and Python AST checks |
| High | `RepairMemory(storage_dir=...)` and `StrategySelector(storage_dir=...)` omit explicit session flags | Pass explicit flags; session > environment > configuration; isolate repo/config state |
| High | Verified-memory metadata discarded; lower-level ingestion accepts unverified data; loading assumes index/JSON agree | Gate all ingestion, preserve provenance, validate persistence, atomic writes |
| High | RepoIndexer uses one configured index path for all roots; stale persisted snippets not checked; planning does not scan an empty index | Root namespaces, fresh scan and source-bound retrieval |
| High | AST fallback chooses first acceptable code fence, accepts imports/expressions as replacement, mishandles decorators | Exactly one top-level function contract, all-candidate ambiguity rejection, safe source slicing |
| High | API start/approve synchronously run model/tests; frontend has no engineering lifecycle calls and proxy only supports plan/generate | Background session work, pollable status, explicit approval/reject/cancel UI and proxy |
| Medium | Learning errors silently swallowed; status lacks outcome/rollback/model-call evidence | Structured events, warnings, metrics and separate functional/safety outcomes |

Historical results are observations, not rerun results. Phase 8 JSON records rejection
categories `no_python_code_block` and `no_valid_function_ast`; it does not retain all
raw responses. Exact reconstruction of 11 model candidates is therefore unavailable.
Do not claim every rejection was a fallback bug. Test reproducible extraction defects.

## Phase gates and execution record

0. Reconnaissance and baseline: run nine existing fast regression files with
   `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`;
   save actual output/JUnit. PASS: 80 passed, one dependency warning; see baseline.xml.
1. Graph: valid/invalid transitions, exception termination, concurrency, cancellation
   and retry budget tests must pass before continuing.
2. Retrieval/patches: root isolation, fallback success/rejection, stale source,
   encoding, syntax and multi-file dry runs must pass.
3. Commands/transactions: allowlist and environment tests; later-file injected
   failure must restore exact bytes/hashes after a real first-file mutation.
4. Learning: enabled/disabled precedence; verified-only provenance; reload, corrupt
   data and namespace isolation; strategy prompt influence and persisted outcomes.
5. Multi-file: explicit approval; target constraints, sequential success, real
   mutation then failure/rollback, targeted/final tests, cancellation.
6. Closed loop: malformed retry, test failure/rollback/retry, independent verification,
   structured failure context, bounded repeated failures.
7. API/Studio: nonblocking start and approval, isolated sessions, status, rejection,
   cancellation, diff/test presentation. Deterministic backend and UI checks.
8. Acceptance: all ten requested scenarios plus regressions; no failed critical
   safety gate may be bypassed. Record exact commands/results.
9. Reproducibility: only after critical gates pass; new allowlisted package, manifest
   without self-hash circularity, checksum verification and execution/ablation guide.
   No full 20-task LLM benchmark is authorized.

## Decisions and limitations to track

- Preserve public state strings; add intermediate states and additive status fields.
- Keep synchronous manager behavior for Python callers; API explicitly dispatches
  asynchronous work. No broad state lock during model or subprocess work.
- Tests are executable repository code. Command restriction is not OS sandboxing;
  document that trust boundary. Do not claim isolation from malicious Python tests.
- Every retry needs fresh approval. Failed edits are restored before replanning;
  update existing expectations for retained failed edits, never weaken assertions.
- Existing audit test intentionally asserts `pytest -p` is allowed. Replace that
  assertion with prohibition and evidence of blocked plugin loading.
- Git metadata is read-only in the sandbox; branch creation required and received
  tool escalation. Commit may also require escalation.
- Durable per-phase outcomes and exact command records will be appended here and
  consolidated in `PHASE8_1_INTEGRATION_FIX_REPORT.md` and targeted validation JSON.

## Completed phase evidence and decisions

| Phase | Exit result | Evidence / meaningful failures resolved |
| --- | --- | --- |
| 0 | PASS | Baseline 80/80, before production edits. Original app+config exported from starting commit later reproduced requested memory not persisting; strategy did persist because actual starting config enabled it. This differs from the historical disabled-strategy configuration. |
| 1 | PASS | 4 graph tests: transition guards, unverified completion, worker serialization, exception and cancellation termination, measured retry bound. |
| 2 | PASS | 34 patch/graph cases. Initial 3 failures: two malformed legacy hunk-count fixtures and legacy new-file-header compatibility; fixed headers without weakening assertions and preserved safe additions. |
| 3 | PASS | 39 execution/transaction/patch cases. Initial new-test f-string collection error corrected before proceeding. Real A-write/B-failure restored exact bytes/hashes; cancellation stopped a native test and descendant. |
| 4 | PASS | 17 initial learning/graph cases. Explicit flags, precedence, persistence/retrieval, provenance, independent-verifier rejection, corrupt schema and configuration isolation. Added concurrent-writer coverage later. |
| 5 | PASS | 3 deterministic multi-file workflows. Initial evidence assertion compared two-target hashes to a three-file directory; corrected to compare all original file hashes and target evidence separately. Successful two-file repair and real-mutation rollback are separate cases. |
| 6 | PASS | 50 existing loop/reliability/security cases plus 6 initial new whole-loop cases. Seven initial regressions fixed: failed-edit fixtures now search restored originals; plugin-loading expectation now rejects; explicit multi-file approval; bounded retries retain configured attempts/error compatibility. Manual state assignment in one test replaced by real validation. |
| 7 | PASS | 4 initial API/proxy tests, later direct-patch hash/stale checks. Final rendered browser has 7 checks, including custom proxy port health and no-CDN operation; screenshot inspected. In-app tool runtime failed initialization, so bundled Playwright/Chrome was used. A later browser run caught an unguarded Tailwind CDN global; fixed with guarded initialization and local panel layout, then reran successfully. |
| 8 | PASS | Final isolated run: 152/152 integration/regression cases and 17/17 legacy strategy cases, no warnings/skips. Exact argv/cwd/env in final command JSON. All ten requested scenarios are covered, with cancellation, timeout, rollback conflicts and concurrent learning added. |
| 9 | LOCAL PREFLIGHT PASS; COLAB/GPU UNVERIFIED | New source-only allowlisted builder, pinned model/embedding revisions, targeted runner, dependency snapshot and execution/ablation guide created. No full 20-task LLM benchmark run. Remote Colab/CUDA validation remains unavailable locally. |

Final validation uses isolated cwd/config/state. The initial baseline used the
existing tests' historical runtime behavior in the original cwd; those tests can
write ignored global learning/cache files. The initial preservation manifest covers
historical tracked artifacts, visible pre-existing untracked work and the explicit
Phase 8 archive; it does not establish byte preservation of ignored runtime stores.
No attempt is made to reconstruct or overwrite pre-existing ignored state without
an original snapshot. New engineering sessions use repo/model/config namespaces;
future experiments must always supply isolated state directories.

Frozen-oracle limitation discovered during Phase 9 inspection: `eval_task_20`
defaults `safe_stop_compliant` to true. The frozen oracle is preserved. The new
runner records a separate actual stale-source mutation/rejection/preservation probe
and never treats an early proposal failure as demonstrating that control.

Security limits are explicit in the execution guide: trusted executable test code,
no OS sandbox/crash journal, in-process repository reservations, external-writer
TOCTOU limitations and delayed cancellation of uninterruptible model inference.
The offline one-call real-model smoke passed generation transport only; its output
is not evidence of a valid patch or increased coding performance.


Final source commit: `920c01aa0d510aa281092e6b55e4ce02b31e584e`. New package: 66 verified members, SHA256 `cfc072c4f63b98a44d08fc09db4929002951226271824e0a5d97dabe843a70f3`. Extracted package reproduced 152 integration and 17 strategy passes; no failures/errors/skips. Final browser: 7 checks, no page errors. Preservation: 1,728 entries unchanged. Remote Colab/GPU and full LLM benchmark remain unrun. See the integration fix report and targeted validation JSON.
