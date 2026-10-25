# Phase 8.1 execution, graph and experiment protocol

## Local verification

Use Python 3.10 or a separately validated compatible environment. The verified local
environment is Windows, Python 3.10.11, PyTorch 2.11.0+cpu, transformers 5.7.0,
pytest 9.1.1. `requirements-phase8_1.txt` pins the principal installed distributions;
it is not a fully resolved, hash-locked cross-platform dependency lock. Colab GPU
installation and execution have not been verified here.

From the repository root, with the environment interpreter:

```powershell
& .\venv\Scripts\python.exe scripts/phase8_1_validate.py --suite all
node --check frontend/engineering.js
```

The validator runs 152 integration/regression cases and 17 legacy strategy cases in
separate temporary working directories, preserving the original config and runtime
storage. Counts may grow with future tests. It records exact argv, cwd, selected
environment, return code, duration, logs and JUnit under `eval_results_phase8_1/`.
Do not indiscriminately run `pytest` at the repository root: historical experiments,
training tests and standalone scripts have side effects and model requirements.
The legacy memory/index regressions require the cached MiniLM embedding model;
the new acceptance cases use deterministic embedding adapters. Provision
`sentence-transformers/all-MiniLM-L6-v2` at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` before an offline run.

Optional bounded transport smoke (one offline model call, 16 generated tokens):

```powershell
& .\venv\Scripts\python.exe scripts/phase8_1_model_smoke.py
```

This does not verify an engineering repair. Missing cached weights or a 90-second
limit is an explicit failure/block, never a repair success.

## Studio and API

Run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`, then
`python run_frontend.py --no-browser`. Use the **Engineering task** control. Submit
the task, local repository path and supported pytest command. Every validated
proposal requires explicit approval, including retries. Cancellation may show
`cancelling` until model work returns, tests stop and rollback is resolved.

`POST /engineering/start` returns HTTP 202 and an immediately pollable session ID.
Poll `GET /engineering/status/{id}`. Approve using
`POST /engineering/approve/{id}?expected_patch_hash={reviewed_hash}`; rejection and
cancellation are `POST /engineering/reject/{id}` and `/engineering/cancel/{id}`.
Unknown sessions return 404; stale proposal state/hash returns 409. Python callers
of `SessionManager.start_session` retain synchronous behavior unless `background=True`.
Public Phase 8 state names remain valid; intermediate states and evidence are additive.
Approval API callers must now supply the hash. Direct `/apply_patch` callers must
supply `expected_patch_hash` and `expected_hashes` from `/propose_patch`.

Sessions remain in process memory. Restart loses session lookup; browser session IDs
then return 404. Durable crash recovery, server authentication and multi-process
worker coordination are outside this stabilization. Bind locally and run trusted
repositories; the API is not a multi-tenant security boundary.

## State graph contract

Each transition emits `{from,to,attempt,timestamp}` and an immutable history snapshot.
Status exposes model-call counts/duration, exact test output/status, selected strategy
and rationale, retry context, verification and rollback evidence. Slow model calls
and subprocesses run outside the session state lock. A nonblocking worker guard
prevents duplicate step/application workers. A repository reservation rejects
conflicting in-process mutations while tests own the applied transaction.

| Transition | Preconditions and input -> output | Side effects, failure/retry and cancellation |
| --- | --- | --- |
| received -> inspecting -> planning | Existing repo; task/config -> inspectable request | No mutation; invalid repo fails; cancellation terminates safely |
| planning -> generating | Attempt budget available; fresh repository symbols, prior failure, verified memories and strategy -> prompt/raw response | One measured model call; model exception fails; cancellation remains pending until inference returns |
| generating -> patch_proposed | Recognized patch or supported fallback -> candidate | No disk writes; malformed output enters bounded retry planning |
| patch_proposed -> awaiting_approval | Parser, paths, exact source matching and Python compile/dry-run succeed -> hashes and validated proposal | No writes; validation errors retry within budget; unsafe paths stop immediately |
| awaiting_approval -> applying | Explicit approval, unchanged proposal digest, validated flag, matching full source hashes and repository reservation -> byte snapshot | Any stale/changed/deleted/created target fails; duplicate approval rejected; cancel cannot race an uncontrolled write |
| applying -> patch_applied | All candidate files validate; source snapshot still current -> verified postimages | Per-file atomic replace; a later write error restores prior writes; rollback errors are explicit |
| patch_applied -> testing | Applied transaction owned -> structured native result | Restricted pytest subprocess; timeout and cancellation stop its process tree; output capture bounded |
| testing -> verifying | Native tests pass -> fresh source-integrity check and independent configured verification | Default is a second fresh pytest invocation; an external oracle callback can replace it; never an LLM judging itself |
| verifying -> completed | Required verifier succeeds and postimages remain unchanged -> functional outcome and committed transaction | Only here may verified experience/positive learning be stored; learning errors are warnings, not invented persistence |
| testing/verifying -> diagnosing -> rolling_back | Failure -> structured category/output/attempt/source/strategy context | Exact bytes restored before replanning; timeout/environment failures stop; test failures may retry |
| rolling_back/generation/validation -> retry_planning -> inspecting -> planning | Rollback verified if applied; remaining budget -> incremented attempt and failure feedback | No repeated writes without another approval; bounded 1–10 attempts (default 3); repeated failures recorded |
| active -> failed | Unrecoverable error or exhausted budget -> precise category/error | Applied transaction must roll back; preserve concurrent external edits and report rollback failure |
| active -> cancelling -> rolling_back -> cancelled | Cancel signal -> stopped subprocess and verified cleanup | No success while work remains active; uninterruptible in-process inference can delay completion; rollback failure ends failed |

An invalid transition raises an error. Terminal states do not restart. A task with
no handler fails explicitly. A safe rejection/cancellation is not a functional repair.

## Patch and filesystem contract

Both unified diffs and SEARCH/REPLACE patches use the same path, stale-source,
Python compilation, dry-run and transaction checks. UTF-8 and CRLF/LF are supported;
other encodings are rejected. Unified rename/deletion operations are unsupported.
Targets are regular independent files beneath the resolved repository root;
traversal, drives/UNC/ADS, reserved device names, protected control directories,
symlinks/reparse escapes and hardlinks are rejected.

Fallback accepts raw Python, or exactly one Python/unlabelled code fence surrounded
by prose. Its complete body must contain exactly one top-level function/async
function, with no imports, top-level expressions, classes or nested definitions.
Exactly one existing top-level function of the same name must exist in the repository.
Decorator slices are handled explicitly. Multiple functions, competing fences,
ambiguous repository matches and unsupported structures are rejected. The synthesized
patch still needs normal validation and approval. Historical candidate raw responses
were not retained, so the exact 11 Phase 8 rejected candidates cannot be replayed.

Transactions snapshot exact bytes and SHA256 before mutation, recheck source at
application and verification, use temporary-file replacement, and verify rollback
bytes. New files and directories are removed when owned by the transaction. Concurrent
external edits are preserved rather than overwritten; such rollback conflicts are
reported as failures. There is no power-loss journal or cross-process filesystem
lock. Filesystem TOCTOU races against a malicious external writer remain possible.

## Test execution policy and trust boundary

Supported executable forms are literal `pytest`, `pytest.exe`, `python -m pytest`,
`python3 -m pytest`, or `python.exe -m pytest`. They map to the current trusted
interpreter and installed pytest, imported before repository paths are added. No
user executable path, arbitrary Python script, shell, plugin/config override, output
destination or arbitrary pytest flag is accepted. Structured argv is preferred;
string commands use `shlex` portable quoting. Quote Windows backslash paths in
strings, or use structured argv/forward slashes.

Allowed flags: `-q`, `-qq`, `-v`, `-vv`, `-s`, `-x`, `--exitfirst`,
`--disable-warnings`, `--no-header`, `--no-summary`, `--strict-markers`,
restricted `-k`/`-m` expressions, `--maxfail` (1–999), and enumerated `--tb` styles.
Test paths/nodes must remain inside the repository. Plugin autoload is disabled;
`PYTEST_PLUGINS`, `PYTEST_ADDOPTS`, inherited Python paths, startup hooks, loader
injections and secrets in the environment are not passed through. An empty explicit
pytest config and repository confcutdir prevent inherited configuration. Cache and
bytecode writes are disabled. Output is bounded to roughly 10 KB during capture,
not after accumulating arbitrary output. Timeouts default to 30 seconds, capped at
600 seconds. Windows uses kill-on-close Job Objects; POSIX uses a process group.

**Residual execution risks:** tests and repository `conftest.py`/`pytest_plugins`
declarations are executable trusted Python; they can use filesystem/network/process
APIs and access host files. Installed pytest/plugins and dependencies are trusted.
This is command restriction and process ownership, not OS sandboxing. Windows has
a short process-launch-to-job-assignment interval; assignment failure aborts execution.
POSIX descendants deliberately escaping their group require OS/container isolation.
Malicious test code, process escape, disk exhaustion, crash recovery and compromised
dependencies require a separate sandbox deployment. Colab/Linux process ownership
has not been executed on this Windows host.

## Learning configuration and provenance

Hierarchy is explicit session setting > explicitly present environment variable
(including `false`) > global config > documented default. Explicit enable flags
are passed to each memory/selector instance. Engineering storage is namespaced by
resolved repo root, test command and component configuration under the supplied
storage directory (or `data/engineering`). New experiments must supply separate
directories. Different temporary repository roots intentionally do not share memory.
The configured coding-model name and revision also participate in the namespace.

All memory ingestion entry points reject missing, negative or contradictory
verification. JSON is authoritative; validated verified records rebuild the vector
index. Corrupt/incompatible records are ignored with warnings; provenance includes
task, original code, successful patch, source/patch hashes, session and verification.
Similarity results are prompt context and still require normal validation/approval.
Writes use locks and atomic JSON replacement. Strategy decisions affect the prompt,
preserve rationale and update outcomes for the selected error type. Duplicate
feedback is ignored; invalid positive outcomes are rejected. Counters and event
history persist under isolated paths. Legacy non-engineering generation APIs retain
their separate historical global memory/strategy storage.

Locks coordinate threads/processes sharing the same state directory, but the two
strategy JSON files are not a crash-atomic database transaction. Learning updates
are not evidence that repair performance improved.

## Packaging and Colab preflight

After committing source, run `python scripts/build_phase8_1_package.py`. It reads
only allowlisted files from the source commit, scans credential patterns, packages
canonical Git bytes with deterministic member metadata, and verifies CRC and all
SHA256 entries. The manifest excludes its own hash; the external archive checksum
covers it. Historical packages/manifests are never rebuilt. No user untracked files,
credentials, weights, caches, research outputs or private experiments are included.

In a fresh Colab runtime, upload the **new** archive and SHA256 sidecar, verify the
archive against the reported checksum, extract into a dedicated directory, inspect
`PHASE8_1_PACKAGE_MANIFEST.json`, and install `requirements-phase8_1.txt`. Validate
the GPU-compatible torch build separately; the pinned local CPU environment does
not establish CUDA compatibility. Set the model and revision to the manifest values,
run deterministic acceptance tests first, and save platform/package/GPU provenance.
Use isolated task/config directories. Listing
`python colab_phase8_1/run_targeted.py` makes zero model calls.

The runner requires `--run --task-id ...` and permits at most three initial tasks.
Each proposal is displayed and requires its exact hash typed by the reviewer.
`--reviewed-full-run` is reserved for a later explicitly authorized full experiment;
it does not authorize execution in this session. Per-task records are written
atomically, include graph events, actual model calls/attempts, timings, oracle details,
and separate functional/safety outcomes. Resume preserves existing records and uses
source/dataset/config fingerprints. Failed runner tasks record their traceback.
Negative safety controls never populate repair memory.

The frozen stale-source task oracle returns true by default when evidence is absent.
Keep its result unchanged for historical comparison; report the new runner's actual
stale-source mutation/rejection/preservation probe separately. Do not call a proposal
failure a successful stale-source demonstration.

## Smallest next controlled experiment (not run)

After review, select one single-function task, one class-method task and one
coordinated multi-file task from the frozen dataset. Run the frozen Phase 8 source
at `9ef57511e0e25d58d0f1318e9d73ccb58465ec44` and the manifest's Phase 8.1 source
with the same pinned model revision, prompts, generation budget, repository fixtures,
independent oracles and hardware. Give each run isolated state. Preserve task-level
records and classify environment failures separately. Report human review time
separately from inference/test runtime.

Then expand only after authorization: baseline, corrected core with learning off,
core+fallback, core+memory, core+strategy, and all enabled. Keep each ablation's
repository roots/state separate; persistence alone is not a learning-benefit test.
For memory transfer, design an explicitly approved train/evaluation split and stable
repository identity rather than reusing arbitrary temporary directories. Keep
functional repair, safety enforcement, patch validity, verified rollback after real
mutation, model calls and runtime as separate metrics. Do not aggregate safety stops
as repairs or claim improvement from the deterministic fixtures or transport smoke.
