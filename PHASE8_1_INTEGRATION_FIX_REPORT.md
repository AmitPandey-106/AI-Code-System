# Phase 8.1 integration fix and readiness report

2026-10-25, Asia/Calcutta. **Local stabilization and package preflight: PASS.**
Colab/GPU execution and coding-performance improvement remain unverified. No full
20-task LLM benchmark was run.

## Starting and ending identities

- Historical baseline: `9ef57511e0e25d58d0f1318e9d73ccb58465ec44`.
- Starting commit: `e46b2f1d36beac4f46abd09d6d75ce7bfea7f449`, branch `audit/phase8-evidence`.
- Ending executable-source commit: `920c01aa0d510aa281092e6b55e4ce02b31e584e`.
- Work branch: `fix/phase8-1-integration`.
- Source commit message: `Stabilize Phase 8.1 engineering graph, transactions, learning and Studio integration`.
- A later evidence-only commit contains this report. Its identity is available with
  `git log -1 --format=%H -- PHASE8_1_INTEGRATION_FIX_REPORT.md`; the final chat response
  identifies that commit. No executable changes follow the source commit above.

The starting tree had no tracked changes and extensive untracked user research and
packaging work. No resets, destructive checkout, pushes or historical artifact edits
occurred. Starting app/config source matches the historical baseline. Historical
98-test and 20-task findings remain historical; the selected new pre-edit command
collected **80** tests, not 98. Historical repair/safety rates are not new measurements.

## Architecture and root causes

The existing state-machine architecture was retained; no LangGraph dependency was
added. The actual dependency/data-flow map and phase gates are in
`PHASE8_1_ENGINEERING_PLAN.md`. Full transition inputs/outputs, preconditions,
side effects, errors/retries, cancellation, events and policy are documented in
`PHASE8_1_EXECUTION_GUIDE.md`.

| Root cause | Corrected behavior and evidence |
| --- | --- |
| Direct state assignment, concurrent workers and incomplete failure cleanup | Explicit graph guards; worker serialization; actual inspection/planning/generation stages; structured edit plan; bounded retries; terminal failure/cancellation and separate functional outcomes. |
| Sequential disk writes and retained failed patches | Shared exact-byte/hash/mode snapshots, atomic per-file replacement, stale checks, rollback after later failure and verified restoration; created file/directory cleanup. Concurrent external edits are preserved and reported as rollback conflicts. |
| Permissive pytest blacklist and inherited execution settings | Structured executable/argument allowlist; trusted interpreter/pytest import; plugin autoload disabled; explicit empty config; sanitized environment; bounded capture; timeouts and descendant ownership. |
| Inconsistent patch paths, syntax, source/hash handling | Both formats use the same path/syntax/hash/transaction gates. Strict UTF-8, newline preservation, Python compilation without execution, hunk counts and ambiguous/duplicate/stale target checks. |
| Shared repository index storage and stale snippets | Root namespaces, source hashes bound to extracted snippets, fresh inspection, accurate decorator/line slices and omission of stale results; offline lexical context avoids mandatory model downloads. |
| Fallback selected the first candidate and accepted broad structures | Exactly one supported top-level function from one raw/fenced response; competing candidates, classes, imports, top-level expressions, nested definitions and ambiguous repo matches rejected. Normal dry-run/approval/application gates still apply. |
| Omitted memory/selector enable flags | Explicit session flags passed; session > present environment (including false) > config hierarchy; repository/model/config/test-command state namespaces. |
| Missing verification/provenance and fragile persistence | All memory ingestion is gated; JSON is authoritative; verified records rebuild vectors; provenance retained; corrupt/incompatible records rejected with warnings; atomic locked writes and concurrency tests. |
| Strategy selection/outcomes did not share reliable persistence | Prompt-affecting decisions and rationale; selected error-type bookkeeping; invalid positive outcomes rejected; feedback deduplicated; outcomes/counters reload and concurrent writes survive. |
| Automatic multi-file approval and prompt-only scope restriction | Bounded validated target plan, import dependency order, snapshots before mutation, explicit approval callback for each proposal, enforced target scope, targeted/final tests and whole-transaction rollback. |
| Synchronous API work and missing Studio lifecycle | Background start/approval, pollable IDs, hash-bound approval, accurate HTTP errors, isolated sessions, rejection/cancel, progress, diff/test/rollback display and configuration badges. Proxy works on custom ports. |
| Unreproducible packaging and inferred benchmark counters | Separate allowlisted source archive, version pins and actual per-task metrics/events; research runner defaults to listing and requires proposal review; state/config/source fingerprints and transparent per-task resume. |

## Reproduced starting behavior and historical limits

`starting_flag_reproduction.json` exports the original app and config from the starting
commit into a disposable directory. A fake-model repair passed a **real native test**
and completed, yet requested repair memory persisted no experience. Actual starting
config was memory=false and strategy=true: strategy outcomes **did persist** in this
checkout. Both missing flag pass-through paths were corrected without assuming the
historical disabled-strategy defaults still applied.

Analysis of the unchanged historical task JSON reproduces **11 recorded fallback
rejections: 5 `no_python_code_block`, 6 `no_valid_function_ast`**. The available
artifacts do not retain the raw candidates, so exact candidate replay and attribution
of every rejection are **BLOCKED**. Not all rejected outputs should be accepted.
New deterministic cases prove supported extraction and explicit rejection; they do
not establish a higher fallback activation or repair rate.

The frozen stale-source oracle defaults `safe_stop_compliant` to true when evidence
is absent. It is unchanged. The new runner records a separate actual source mutation,
approval rejection and preservation probe. Proposal failure alone cannot pass that probe.

## Phase exit checks and actual results

Phases 0–8 passed their local exit gates in order. Phase 9 local package preflight
passed; remote Colab/GPU behavior is unverified. No failed critical safety gate was
bypassed. Counts below come from saved JUnit. Runs overlap; do not sum phase rows.

| Run | Passed | Failed | Errors | Skips | Seconds | Evidence under eval_results_phase8_1 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Pre-edit baseline | 80 | 0 | 0 | 0 | 89.909 | `baseline.xml` |
| Graph | 4 | 0 | 0 | 0 | 63.128 | `phase1.xml` |
| Patches/retrieval | 34 | 0 | 0 | 0 | 0.828 | `phase2.xml` |
| Command/transaction | 39 | 0 | 0 | 0 | 12.196 | `phase3.xml` |
| Learning | 17 | 0 | 0 | 0 | 3.488 | `phase4.xml` |
| Multi-file | 3 | 0 | 0 | 0 | 1.949 | `phase5.xml` |
| Existing loop/security regressions | 50 | 0 | 0 | 0 | 27.743 | `phase6.xml` |
| Initial whole-loop acceptance | 6 | 0 | 0 | 0 | 5.621 | `phase6_acceptance.xml` |
| Initial API/proxy | 4 | 0 | 0 | 0 | 4.328 | `phase7.xml` |
| Additional safety/integration | 30 | 0 | 0 | 0 | 24.531 | `phase8_extra.xml` |
| Research runner | 6 | 0 | 0 | 0 | 15.609 | `phase9_runner.xml` |
| Final integrated suite | 152 | 0 | 0 | 0 | 64.784 | `final_integration.xml` |
| Isolated legacy strategy | 17 | 0 | 0 | 0 | 0.867 | `isolated_strategy_regression.xml` |
| Extracted package integration | 152 | 0 | 0 | 0 | 62.351 | `packaged_final_integration.xml` |
| Extracted package strategy | 17 | 0 | 0 | 0 | 0.888 | `packaged_isolated_strategy_regression.xml` |

Final unique regression/acceptance total: **169 = 152 + 17**, with zero failures,
errors or skips. The extracted archive reproduced that same total.

- **7/7 headless Chrome checks** passed against committed source, with zero page errors:
  no mutation before approval; verified repair/diff/tests; policy rejection; session
  switching; rejection without mutation; custom-port health/config; no-CDN operation.
  Evidence: `studio_browser_validation.json`, `studio_verified_repair.png`.
- Pinned Instruct model smoke: one offline call, at most 16 output tokens,
  9.359s model/load interval and 22.109s process wall time.
  An earlier base-model transport smoke also made one call: **2 real calls total**.
  These test invocation/response transport only. The short responses are incomplete
  code and are **not counted as validated patches or repairs**.
- Python source compilation, JavaScript syntax and Git whitespace checks passed.
- No full 20-task LLM benchmark or LoRA training campaign was run; no functional
  repair-rate or learning improvement is claimed.

### Required acceptance coverage

- **simple function repair:** `test_phase8_1_loop.py::test_malformed_retry_then_native_repair; test_phase8_1_learning.py::test_verified_repair_persists_and_is_retrieved_in_later_session`
- **malformed then bounded retry:** `test_phase8_1_loop.py::test_malformed_retry_then_native_repair`
- **failing tests rollback:** `test_phase8_1_loop.py::test_test_failure_restored_before_new_approval`
- **stale source:** `test_phase8_1_loop.py::test_stale_source_and_traversal_fail_without_overwriting`
- **prohibited command:** `test_phase8_1_execution.py::test_narrow_command_policy; test_phase8_1_api.py::test_start_is_nonblocking_progress_and_cancel_are_isolated`
- **traversal:** `test_phase8_1_patches.py::test_platform_independent_path_rejections`
- **verified memory across sessions:** `test_phase8_1_learning.py::test_verified_repair_persists_and_is_retrieved_in_later_session`
- **strategy prompt and persistence:** `test_phase8_1_learning.py::test_verified_repair_persists_and_is_retrieved_in_later_session`
- **multifile rollback after real mutation:** `test_phase8_1_multi.py::test_later_model_failure_rolls_back_actual_first_mutation; test_phase8_1_execution.py::test_real_first_write_then_second_failure_restores_bytes`
- **in progress cancel or timeout:** `test_phase8_1_loop.py::test_cancellation_during_tests_restores_patch; test_phase8_1_loop.py::test_timeout_is_not_success_and_restores_patch; test_phase8_1_execution.py::test_cancel_owns_test_descendants`

Additional cases cover independent-oracle rejection, corrupt/disabled memory,
corrupt strategy data, concurrent learning writes, changed/duplicate approval,
same-root concurrency, rollback conflicts, new-file cleanup, environment/plugin
poisoning, Windows argv, API errors and native process descendants.

### Failures resolved without weakening assertions

- Phase 2 initially had 3 failures. Two old fixtures declared three hunk lines but
  contained four; their headers were corrected and assertions retained. Safe legacy
  zero-source addition syntax remained supported.
- A new Phase 3 test initially had an f-string collection error; fixed before its gate.
- A Phase 5 evidence assertion compared two-target hashes to a three-file directory;
  it now independently checks all original bytes/hashes and target-level evidence.
- `phase6_initial.xml` records 7 failed / 43 passed. Retry fixtures now search restored
  originals; plugin loading is now prohibited; multi-file fixtures explicitly approve;
  configured attempt-budget/error compatibility was retained; manual approval-state
  assignment in a test was replaced by actual validation.
- A later browser run caught `tailwind is not defined` when its CDN failed. Guarded
  initialization and local panel styling fixed this. Final browser assertions also
  block external CDN resources deliberately and still pass.

No assertions were weakened to mask defects, independent oracles bypassed or failed
repairs reported as successes. Intermediate failures and final reruns are recorded
in the engineering plan, JUnit/log artifacts and tool transcript.

## Exact commands and reproducibility records

Direct command cwd: `D:\Amit Stuff\ai-code-system`.

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git show --no-patch --format=fuller 9ef57511e0e25d58d0f1318e9d73ccb58465ec44
git switch -c fix/phase8-1-integration
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\venv\Scripts\python.exe -m pytest tests/test_patch_engine.py tests/test_patch_engine_search_replace.py tests/test_phase7b_patch_reliability.py tests/test_project_test_runner.py tests/test_engineering_loop.py tests/test_engineering_loop_safety.py tests/test_engineering_loop_retries.py tests/test_phase8_architecture.py tests/test_audit_security_boundaries.py -q --junitxml=eval_results_phase8_1/baseline.xml
& .\venv\Scripts\python.exe scripts/phase8_1_reproduce_flags.py
& .\venv\Scripts\python.exe scripts/phase8_1_validate.py --suite all
& .\venv\Scripts\python.exe scripts/phase8_1_validate.py --suite integration
& .\venv\Scripts\python.exe scripts/phase8_1_validate.py --suite strategy
node --check frontend/engineering.js
git diff --check
git commit -m 'Stabilize Phase 8.1 engineering graph, transactions, learning and Studio integration'
& .\venv\Scripts\python.exe scripts/build_phase8_1_package.py
$env:LITECODER_MODEL_NAME='Qwen/Qwen2.5-Coder-1.5B-Instruct'
$env:LITECODER_MODEL_REVISION='2e1fd397ee46e1388853d2af2c993145b0f1098a'
& .\venv\Scripts\python.exe scripts/phase8_1_model_smoke.py
```

`executed_validation_commands.json` records each phase's pytest argv and the latest
browser server/test commands, including temporary repository and Node runtime path.
The exact final subprocess argv/cwd/environment/config digest/return code/duration
are in `final_integration_command.json`, `isolated_strategy_regression_command.json`
and their `packaged_` counterparts. `packaged_validation.json` records the exact
interpreter/script/cwd used for extracted-copy validation. The isolated strategy
suite enables its required learning fixture only inside its temporary config.
Read-only reconnaissance used Git status/log/show, `rg`, `Get-Content` and dependency
inspection. Staging was restricted to the source files below. The in-app browser and
Node tools could not initialize kernel assets; existing bundled Playwright/Chrome
provided the browser fallback. QA servers were stopped after validation.

## Package and historical preservation

- New archive: `eval_results_phase8_1/LITE_CODER_PHASE8_1_SOURCE.zip`, 193,632 bytes.
- Archive SHA256: `cfc072c4f63b98a44d08fc09db4929002951226271824e0a5d97dabe843a70f3`.
- Manifest SHA256: `b76f7bedf8c3dda851b92af37037cd8e1050645d69a92291e744bab78594bb4c`.
- **66 verified members**: exact allowlist, CRC and all SHA256 entries. Manifest
  self-hash is excluded to avoid circularity; external checksum covers the archive.
- Contents are canonical Git bytes from the ending executable-source commit, never
  untracked user files, weights, caches, credentials or private research outputs.
- Frozen dataset tree: `816181aa6ba56e52080712c998e67e31e2385a17`, identical at the
  historical baseline and ending source commits.
- Coding model: `Qwen/Qwen2.5-Coder-1.5B-Instruct` at
  `2e1fd397ee46e1388853d2af2c993145b0f1098a`.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` at
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Principal installed package versions are pinned in `requirements-phase8_1.txt`;
  this is not a fully hash-locked, remotely validated CUDA environment.
- **1,728/1,728 starting manifest files unchanged**, including historical artifacts,
  datasets, source snapshots, reports and visible pre-existing untracked user work.
  Historical archive SHA256 remains
  `7a9ec59feed6a327d2ed0c9c2cffd198afbd3314a14b786c02e20ecba884ab40`.

The initial original tests used their historical cwd/runtime behavior and can update
ignored global learning/cache files. Ignored runtime stores were not in the initial
manifest, so their byte preservation is **not established**. No unsupported
reconstruction or overwrite of existing ignored state was attempted. Final tests
isolate cwd/config/runtime storage. Future experiments must use fresh state directories.
The new archive contains the committed prebuild plan; this report records the finished preflight.

## Remaining security limitations and blocked work

- Tests and repository conftest/pytest plugin declarations are **trusted executable
  Python** with host filesystem/network/process access. Command restriction is not
  an OS sandbox for hostile repositories or compromised dependencies.
- Windows Jobs were exercised; POSIX/Colab process groups were not run here. Windows
  has a short launch-to-job-assignment interval; deliberate POSIX group escape needs
  OS/container isolation. Disk/resource exhaustion needs deployment-level limits.
- Repository reservations coordinate one process, not multiple API workers or
  arbitrary external writers. Hash checks do not eliminate every malicious TOCTOU
  race. No power-loss/crash-recovery filesystem journal is provided.
- Model/adapter access is serialized, but cancellation cannot forcibly interrupt
  in-process inference/GPU work. Status remains cancelling until it returns.
- Sessions are in memory; restart loses lookup. The local API retains no authentication
  or multi-tenant authorization. Bind it locally.
- Default verification is fresh native tests plus source integrity. Stronger semantic
  correctness needs an external/held-out oracle; insufficient tests cannot prove a task.
- Multi-file target scope remains caller-provided. Static import ordering is not a
  complete dependency analyzer; dynamic/relative imports and cycles need reviewed plans.
- Strategy event/counter JSON files are atomic individually, not a crash-atomic pair.
  Persistence/retrieval does not demonstrate learning benefit. Legacy generation
  routes retain their historical global state, separate from engineering namespaces.
- Historical raw fallback replay is blocked by missing retained candidates. Permissive
  frozen oracle semantics are preserved and supplemented, never silently rewritten.
- **Colab/GPU execution remains unverified:** the local Windows CPU host cannot prove
  CUDA wheel compatibility, remote installation, GPU memory or notebook behavior.
- **Full 20-task LLM benchmark is not authorized and was not run.** No performance
  improvement is claimed from deterministic fixtures, persistence or transport smoke.

All critical local safety gates passed. Universal repository support, production
sandboxing, remote GPU readiness and better coding success remain unproven.

## Smallest next experiment

After review and explicit authorization, run one paired frozen-dataset function task,
e.g. `task_01_router_slug_param`, on the frozen source and corrected source with the
same pinned model, seed, generation/attempt limits, fixture, independent oracle and
hardware. Disable learning for this first pair; isolate all state. Keep patch validity,
functional outcome, safety/rollback evidence, actual calls and runtime separate. One
pair is a functional check, not general performance evidence. Next add a class-method
and multi-file task, then baseline/core/fallback/memory/strategy/all ablations as laid
out in the execution guide. Do not run all 20 tasks without separate authorization.

## Changed files and required deliverables

The source commit changes these **40 files**:

- `PHASE8_1_ENGINEERING_PLAN.md`
- `PHASE8_1_EXECUTION_GUIDE.md`
- `app/engineering_api.py`
- `app/engineering_loop.py`
- `app/file_transaction.py`
- `app/main.py`
- `app/model.py`
- `app/multi_file_orchestrator.py`
- `app/patch_engine.py`
- `app/process_control.py`
- `app/project_test_runner.py`
- `app/repair_memory.py`
- `app/repo_index.py`
- `app/strategy_selector.py`
- `colab_phase8_1/config.json`
- `colab_phase8_1/run_targeted.py`
- `frontend/engineering.js`
- `frontend/index.html`
- `frontend/server.py`
- `requirements-phase8_1.txt`
- `scripts/build_phase8_1_package.py`
- `scripts/phase8_1_model_smoke.py`
- `scripts/phase8_1_reproduce_flags.py`
- `scripts/phase8_1_studio_browser.cjs`
- `scripts/phase8_1_studio_smoke.py`
- `scripts/phase8_1_validate.py`
- `tests/test_audit_security_boundaries.py`
- `tests/test_engineering_loop.py`
- `tests/test_engineering_loop_safety.py`
- `tests/test_patch_engine.py`
- `tests/test_phase7b_patch_reliability.py`
- `tests/test_phase8_1_api.py`
- `tests/test_phase8_1_execution.py`
- `tests/test_phase8_1_graph.py`
- `tests/test_phase8_1_learning.py`
- `tests/test_phase8_1_loop.py`
- `tests/test_phase8_1_multi.py`
- `tests/test_phase8_1_patches.py`
- `tests/test_phase8_1_research.py`
- `tests/test_phase8_architecture.py`

Evidence additions: `PHASE8_1_INTEGRATION_FIX_REPORT.md`, the completed engineering
plan note, and `eval_results_phase8_1/` containing logs/JUnit, command records,
`source_changed_files.json`, preservation manifests, starting-flag reproduction,
historical fallback analysis, browser JSON/screenshot, model smoke records, source
archive/checksum, package/extracted-package evidence and required
`targeted_validation.json`. These are new Phase 8.1 artifacts; historical outputs are untouched.
