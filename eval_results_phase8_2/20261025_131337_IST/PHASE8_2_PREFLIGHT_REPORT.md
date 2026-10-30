# LITE-Coder Phase 8.2 preflight report

**Status: ready for review of the exact paired plan; model execution requires approval.**
The model-backed comparison has **not run**. Phase 8.1 repair-performance improvement
is **not measured**. No run-result or comparison-report placeholders have been created.

Results directory: `D:\Amit Stuff\ai-code-system\eval_results_phase8_2\20261025_131337_IST`.
Plan SHA256: `cea4b5a9eaa7b0c763b934f0473ea019efed9d333eeac8f2b82e8adf06c98204`.

## 1. Authoritative repository state

- Branch: `fix/phase8-1-integration`.
- Starting/current HEAD: `4cb53fbcbd8c2ce0f9cb7286ac0dcd4377915395` (Phase 8.1 evidence commit).
- Arm A: frozen Phase 8 `9ef57511e0e25d58d0f1318e9d73ccb58465ec44`.
- Arm B: frozen candidate `920c01aa0d510aa281092e6b55e4ce02b31e584e`.
- Both revisions exist. Relevant current app/frontend/tests/Phase 8.1 runner code matches
  the candidate; HEAD adds evidence, not later implementation changes.
- No tracked modifications at entry. Extensive pre-existing untracked research and
  packaging files remain preserved; the tree was not presented as completely clean.
- Canonical dataset/oracle tree is identical across both revisions and current HEAD:
  `816181aa6ba56e52080712c998e67e31e2385a17`.
- No reset, clean, checkout replacement, canonical-data edit or historical-evidence overwrite.
  Exact Git status and preservation records are retained in this directory.

The actual filenames were checked: `PHASE8_1_INTEGRATION_FIX_REPORT.md`,
`PHASE8_1_EXECUTION_GUIDE.md`, `scripts/phase8_1_validate.py`,
`scripts/phase8_1_model_smoke.py`, `colab_phase8_1/run_targeted.py`,
`eval_dataset_v2/tasks.py` and `eval_dataset_v2/repositories.py`.
The model smoke script was **read, not executed** in Phase 8.2.

## 2. Fresh deterministic validation

The validator hardcodes its output to `ROOT/eval_results_phase8_1`. Running it directly
in the original checkout would overwrite historical evidence. Therefore the unchanged
script and frozen candidate sources were exported byte-for-byte into
`D:\Amit Stuff\ai-code-system\eval_results_phase8_2\20261025_131337_IST\exports\candidate` and run there using the documented original venv interpreter.
This is a documented cwd/path adaptation, not a production-code or test modification.

| Fresh run | Passed | Failed | Errors | Skipped | JUnit seconds | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Final integration/regression | 152 | 0 | 0 | 0 | 42.306 | 0 |
| Isolated legacy strategy | 17 | 0 | 0 | 0 | 0.499 | 0 |
| Phase 8.2 control-plane gates | 11 | 0 | 0 | 0 | 1.307 | 0 |
| `node --check frontend/engineering.js` | Syntax check passed | — | — | — | 0.062 wall | 0 |

**169 Phase 8.1 tests freshly passed.** The 11 new checks validate experiment controls,
not repair accuracy. Existing regression coverage includes cached embedding checks;
no coding LLM was loaded/generated. No assertion was weakened, skipped or deleted.

The first isolated export mistakenly omitted `frontend/server.py`: integration had
151 passes and one import failure; strategy had 17 passes. The entire failed run is
preserved under `validation_attempt1/`, with its original launcher log. Adding the exact
missing frozen frontend files fixed the export. The complete unchanged suite was
rerun successfully. This is an export/setup failure, not a candidate regression.

Exact commands included:

```powershell
# cwd: the isolated exports/candidate directory
& 'D:\Amit Stuff\ai-code-system\venv\Scripts\python.exe' scripts/phase8_1_validate.py --suite all
# cwd: original checkout
node --check frontend/engineering.js
& .\venv\Scripts\python.exe -m pytest tests/test_phase8_2_preflight.py -q --junitxml=eval_results_phase8_2/20261025_131337_IST/adapter_native_environment_tests.xml
```

The unchanged validator records full subprocess argv, cwd, environment, config hash,
return codes and durations under `exports/candidate/eval_results_phase8_1/`.
`executed_commands.json`, fresh launcher logs and JUnit retain the new evidence.
The wrapper uses offline library settings, disables pytest plugin autoload and
isolates temporary runtime/config storage. Historical evidence remains unchanged.

## 3. Targeted-runner and paired-adapter preflight

The documented no-execution command was run directly:

```powershell
& .\venv\Scripts\python.exe colab_phase8_1/run_targeted.py
```

It exited 0 and listed 20 canonical task IDs with zero model calls. A second guarded
invocation substituted a fail-closed `app.model` before running the same default CLI:
**zero generation attempts** occurred. See `runner_preflight.json` and captured stdout/stderr.

The original listing is **not a paired experiment plan**. Its execution protocol
fingerprints some inputs, but cannot by itself bind both frozen revisions, guarantee
identical model prompts or compensate for baseline's ignored revision environment variable.
It is preserved unchanged. Phase 8.2 adds preparation-only infrastructure and a separately
approval-gated arm adapter, with no new agent capability or strategy.

Both frozen arms were probed without generation. Each used the canonical fixture,
disabled memory/strategy/retrieval and one-attempt budget. `get_model` was replaced
with a fail-closed guard; only a named non-model sentinel captured the actual prompt.
Each probe records one intercepted boundary invocation and **zero real model calls**.
The sentinel is not a generated candidate or a repair result.

Directly verified:

- Both raw model prompts have SHA256 `9f9ed1d8310e6792670551e66c9348e2192b4992a8df2630cab3a77cbb35af6d`.
- All seven starting fixture-file hashes match between arms; both fixtures are unchanged.
- Both independent starting oracles report **one pass, one assertion failure**, exit 1.
- The 11 control tests cover absent/wrong/tampered approvals, adapter drift, evidence
  overwrite refusal, oracle-based outcome classification, environment failures,
  declined review and rollback not being a repair.
- A direct execution attempt with a deliberately wrong digest was rejected before
  source/model loading or actual-run directory creation. This was a gate test, not a model run.

## 4. Chosen canonical task

- ID: `task_01_router_slug_param`.
- Category: `single_function_bugfix`.
- Task: `In micro_http/router.py, fix match_path so that parameter segments like <slug> support hyphens (e.g., 'hello-world-2026') in addition to alphanumeric characters.`
- Target: `micro_http/router.py`, top-level `match_path`.
- Independent oracle: `eval_dataset_v2.tasks.eval_task_01`, invoking
  `python -m pytest tests/test_router.py`.
- Authoritative tests: normal `/users/<id>` matching and a hyphenated article slug,
  with exact matched/parameter assertions. The fresh failure is `matched is False`
  for the hyphenated slug; the normal case passes.
- Rationale: pure-standard-library, network-independent fixture; clear expected
  behavior; one source file; same frozen task/oracle in both arms. No invented task,
  expected answer, replacement oracle or easier benchmark was introduced.

Fingerprints:

- Dataset module SHA256: `493c2c0c3267a9ab7a49ef36d88769d12c6b2af0cdecdc7c470d86576e767e42`.
- Frozen oracle function SHA256: `782350edc491f9a68ab6f0383bea05407e13453eba63998cde32418ce8940893`.
- Authoritative generated test-file SHA256: `1476656eefe48924bbe83ccc07d9d122e906ca7584f2f1aa77c6531fb9804838`.
- Full source export maps, fixture maps, raw prompt, model-cache map and dependency
  fingerprints are in `experiment_plan.json` and the manifests.

## 5. Exact experiment proposed for approval

| Control | Same treatment for both arms |
| --- | --- |
| Revisions | Arm A baseline 9ef57511…; Arm B candidate 920c01aa… (full hashes above/in plan) |
| Order | Seeded random draw with seed 20261025 produced **A then B**; fresh process per arm |
| Model | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| Immutable revision | `2e1fd397ee46e1388853d2af2c993145b0f1098a` |
| Cached inputs | Seven existing files, 3,098,955,668 bytes; content hashes verified by streaming reads; no weight loading/inference in preflight |
| Hardware/backend | Local Windows CPU, PyTorch `2.11.0+cpu`, Transformers `5.7.0`, float32, eager attention, 4 threads |
| Observed CPU | `Intel64 Family 6 Model 142 Stepping 12, GenuineIntel`; 4 physical/8 logical CPUs; GPU unavailable/unused |
| Prompt | Identical canonical task plus the same read-only source snapshot and existing patch-format instructions; no arm-specific tuning |
| Sampling | Greedy `do_sample=false`, seed 42, repetition penalty 1.1 |
| Budget per arm | **1 attempt, 0 retries, at most 1 call, at most 768 generated tokens** |
| Combined budget | **At most 2 calls and 1,536 generated tokens** |
| Time limits | Native tests/oracle 30 seconds; generation soft limit 180 seconds; supervised child 300 seconds per arm |
| Learning/other components | Memory=false, strategy=false, LoRA=false, retrieval=false; fallback/example formatting enabled equally |
| Network/downloads | **Not required; prohibited**. Force local cached snapshot and offline settings |
| Review | Exact plan hash confirmed before child launch; each proposed patch requires its own reviewer hash; only the target file is permitted |
| Cost | No paid API/GPU service; local compute/electricity cost and actual latency are not estimated |

The CPU marketing-name query was denied. The observed processor identifier, core
counts, RAM and OS are directly captured; no marketing name was fabricated.

A common read-only loader adapter pins both frozen implementations to the **same
cached snapshot**, because the baseline does not honor the revision environment variable.
The baseline native runner also resolved an ambient global pytest, while the candidate uses the current interpreter. The shared adapter now prepends the project venv Scripts directory to PATH for both arms; `native_pytest_binding.json` verifies the exact executable and pytest version. No frozen application source is changed. Actual generation settings, token counts/ID
hashes, raw responses, load/inference/test/review time, errors and termination evidence
will be recorded only if execution is approved. A generation-start checkpoint survives
an enforced process timeout where possible; incomplete results are not invented.

The 300-second child limit includes patch review; pre-child confirmation and hash
checks are separate. A delayed/declined review is inconclusive, not repair failure.
Actual latency is unknown. CPU/model-cache checks are not transport or repair smokes.

Execution commands, in order, are prepared in `approval_gated_commands.json` and
have **not been executed**. They require `--run`, the final plan digest and explicit
reviewer confirmation. Source, adapter, dependency, hardware, model-cache, fixture
and prompt drift block execution. Output directories are exclusive-create and cannot
silently overwrite a previous arm. State/output roots are separate for A and B.

### Acceptance and comparison rules

Functional success requires an explicitly approved applied change, unchanged
independent test/oracle bytes, framework completion and independent frozen oracle
exit 0 against the repaired fixture. A nonempty response, valid syntax, safe stop,
rollback or unrelated test pass is insufficient.

Within-budget patch parse/validation errors or independent assertion failures are
functional failures. Environment/model/cache/import errors, timeouts, missing review,
source/prompt drift and oracle execution problems are inconclusive and must be
reported separately. Functional outcome, framework state, patch validity, safety,
rollback, calls/tokens, and runtime are distinct metrics.

A comparison report may be written **only after both actual arms have run** and
raw/tokenized prompt identity, generation settings and fingerprints are checked.
There are currently no actual-arm run results, no model-backed comparison report,
and no claimed performance difference.

## 6. Minimal changes and proofs

| New file | Concrete blocker addressed | Proof in this phase |
| --- | --- | --- |
| `scripts/phase8_2_preflight.py` | Legacy listing lacked a complete paired plan, common fingerprints and explicit bounds | Real default listing plus fail-closed repeat; frozen tree/hash checks; complete immutable plan; no execution path in this preparer |
| `scripts/phase8_2_arm.py` | Need to import either frozen implementation, keep prompts/weights/budgets common, require approval, and preserve raw evidence | Both real frozen arms probed with model loader blocked; prompt/fixture equality; negative approval execution rejected; no-overwrite and outcome gates tested |
| `tests/test_phase8_2_preflight.py` | Approval drift, evidence overwrite and environment failures could otherwise invalidate evaluation | 11 passing model-free control-plane checks; no changes to existing assertions |

Original application, strategies, learning, UI, canonical benchmark and Phase 8.1
runner sources remain unchanged. No new dependencies were installed. The adapter's
actual model-backed path is deliberately not exercised before approval; successful
weight loading, generation, patch application and paired outcomes remain untested.

## 7. Evidence scope, limitations and deviations

**Verified directly now:** Git identities/unchanged dataset, fresh 169-test suite,
JS syntax, 11 control checks, zero-call listing/probes, identical fixtures/prompts,
initial independent oracle failures, cached-model hashes and current environment.

**Inherited only:** prior Phase 8 benchmark outcomes, Phase 8.1 browser checks and
model transport smokes. They were read for context and are not fresh Phase 8.2 results.

**Not tested:** actual coding-model generation, real model-backed patch application,
functional improvement, retry/learning gains, other task categories, full benchmark,
and GPU/Colab execution. Input token counts are not guessed; they will be measured
from the actual common tokenizer during an approved run.

**Approval required:** the two-arm model-backed comparison. Your Phase 8.2 brief,
section 6, explicitly requires a presented exact plan and approval before model
execution. Preparing or fingerprinting the plan does not grant that approval.

Deviations/limits:

1. Validation ran in an unchanged isolated export to protect historical evidence.
   The omitted frontend export file caused the preserved first failed attempt;
   correcting that export and rerunning fixed it without changing the candidate.
2. The original no-run mode provides a list, not a plan. A separate paired preparer
   avoids changing the frozen runner or either application revision.
3. Retrieval is disabled and a common read-only source snapshot is supplied to
   both arms so their actual prompts match. This is a controlled repair-pipeline
   comparison, not a benchmark of each arm's default repository understanding.
4. One attempt per arm deliberately excludes retries. One selected task cannot
   establish general accuracy, statistical significance or learning benefit.
5. Identical runtime loader pins compensate for baseline's missing revision support.
   This is a new controlled trial, not a recreation of unpinned historical timing.
6. Native pytest was explicitly pinned to the same project venv in both arms after the ambient executable was found outside it. This fixes an interpreter/dependency confound without changing the oracle.
7. Tests execute trusted canonical Python on the host. Pytest/process restrictions
   are not an OS security sandbox. Arbitrary untrusted repositories were not run.
8. The local CPU's marketing name is unknown; processor/core/OS identifiers are
   recorded. Actual inference latency, peak model memory and tokens remain unknown.
9. Plan drafts and intermediate gate logs are preserved; none contain real paired
   model outcomes. The current final digest binds the final adapter and controls.

## 8. Files and approval status

New preparation files (uncommitted; current branch and existing work preserved):

- `D:\Amit Stuff\ai-code-system\scripts\phase8_2_preflight.py`
- `D:\Amit Stuff\ai-code-system\scripts\phase8_2_arm.py`
- `D:\Amit Stuff\ai-code-system\tests\test_phase8_2_preflight.py`
- `D:\Amit Stuff\ai-code-system\PHASE8_2_PREFLIGHT_REPORT.md`
- `D:\Amit Stuff\ai-code-system\eval_results_phase8_2\20261025_131337_IST` containing this report, `experiment_plan.json`,
  `environment_manifest.json`, `preflight_validation.json`, exact commands,
  frozen export/source manifests, actual no-model probes and initial oracle output,
  fresh logs/JUnit, failed-attempt evidence, plan drafts and preservation checks.

`created_files.json` enumerates exact created file paths. Historical Phase 8/8.1
artifacts and starting user files are verified by content hashes. There are no new
commits, no tracked changes to the frozen application and no discarded user work.

**Actual model-backed comparison: NOT RUN. Approval: NOT GRANTED.**
Review `experiment_plan.json` with SHA256 `cea4b5a9eaa7b0c763b934f0473ea019efed9d333eeac8f2b82e8adf06c98204` before approving
Arm A then Arm B under the limits above. No comparison result exists yet.
