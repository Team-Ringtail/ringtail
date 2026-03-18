## Ringtail Replay API — Documentation

### Overview

- **Purpose**: Replay-driven optimization API used by the Ringtail CLI / web UI to (a) inspect a target repo via a replay script, (b) rank replay-backed optimization candidates, and (c) run optimization on either the best or a specific target.
- **Owner**: Ringtail team (GM, Lance, Colin, Julian, Shiva)
- **Primary consumers**:
  - Ringtail web UI (`interfaces/web/`)
  - Ringtail CLI (`interfaces/cli/cli.jac`)
- **Environments**:
  - **Local**: `http://localhost:<port>` (dev server)
  - **TBD**: staging / production base URLs once deployed

---

## Architecture & Context

- **API type**: JSON-over-HTTP, request/response.
- **Domain**:
  - Accepts a `source_root` and a replay `script_path`.
  - Runs the replay trace against the repo.
  - Extracts replay-backed function candidates with metrics.
  - Optionally optimizes functions using the optimization loop.
- **Key backend functions**:
  - `inspect_replay_repo(...)`
  - `discover_and_rank_replay_repo(...)`
  - `optimize_best_replay_in_repo(...)`
  - `optimize_replay_function(...)`

---

## Authentication & Authorization

- **Current state**: No authentication specified in MVP contract.
- **Assumption** (MVP): API is only exposed on trusted dev / internal networks.
- **Future** (recommended):
  - Add header-based auth, e.g. `Authorization: Bearer <token>` or an internal API key.
  - Add rate limiting per caller once exposed more broadly.

---

## Conventions

- **Base URL (example)**: `http://localhost:8000`
- **Content type**: `application/json` (both request and response).
- **HTTP methods**: All endpoints are `POST` for now, even read-like actions.
- **Paths**:
  - `/replay/inspect`
  - `/replay/rank`
  - `/replay/optimize-best`
  - `/replay/optimize-one`
- **File paths**:
  - `source_root`, `script_path`, and `source_file` are **absolute paths** on the backend host.

---

## Error Handling

- **Error contract (all endpoints)**:
  - On failure, the response must contain a **top-level** `error` string.
- **Minimum failure shape**:

```json
{
  "error": "Replay trace captured no replay-backed repo candidates"
}
```

- **For optimization endpoints**:
  - They may still return the “normal” result-shaped object, but **must** include a non-empty `error` field when something fails (e.g. replay errors, optimization failure).

---

## Endpoints

### 1. `POST /replay/inspect` — Inspect Replay Repo

**Purpose**: Run the replay trace once and return observed replay-backed candidates and trace information. Typically the first call the UI makes after a user selects a repo + driver script.

**Request body**:

```json
{
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py"
}
```

- **Fields**:
  - `source_root` (string, required): Absolute path to the root of the project or subdir to inspect.
  - `script_path` (string, required): Absolute path to the replay / driver script to execute.

**Success response** (shape):

```json
{
  "source_files": [
    "/abs/repo/pkg/a.py",
    "/abs/repo/pkg/b.py"
  ],
  "replay_script": "/abs/repo/drive.py",
  "observed_source_files": [
    "/abs/repo/pkg/a.py",
    "/abs/repo/pkg/b.py"
  ],
  "observed_function_keys": [
    "/abs/repo/pkg/a.py::alpha",
    "/abs/repo/pkg/b.py::beta"
  ],
  "candidate_count": 2,
  "candidates": [
    {
      "source_file": "/abs/repo/pkg/a.py",
      "function_name": "alpha",
      "function_call": "alpha(1)",
      "replay_trace_count": 1,
      "discovered_test_count": 0
    },
    {
      "source_file": "/abs/repo/pkg/b.py",
      "function_name": "beta",
      "function_call": "beta(2)",
      "replay_trace_count": 2,
      "discovered_test_count": 1
    }
  ],
  "replay_trace": {
    "success": true,
    "total_trace_count": 3,
    "observed_source_files": [
      "/abs/repo/pkg/a.py",
      "/abs/repo/pkg/b.py"
    ],
    "run_error": "",
    "partial_success": false
  },
  "error": ""
}
```

- **Important fields**:
  - `candidates[*].replay_trace_count`: How many times this function was seen in the trace.
  - `candidates[*].discovered_test_count`: How many tests are already known for this function.
  - `replay_trace.partial_success`:
    - `false`: trace ran cleanly.
    - `true`: something failed mid-run but some data was collected.
  - `error`:
    - Empty on success, non-empty on failure.

**Typical UI usage**:

1. Call `/replay/inspect` after the user selects repo + script.
2. Use `candidates` to render the “observed functions” list.
3. Optionally filter/annotate using `observed_function_keys`.

---

### 2. `POST /replay/rank` — Rank Replay Repo Candidates

**Purpose**: Return replay-backed repo candidates sorted best-first using backend-owned ranking (performance, complexity, tests, etc.).

**Request body**:

```json
{
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py"
}
```

**Success response** (shape):

```json
[
  {
    "source_file": "/abs/repo/pkg/b.py",
    "function_name": "beta",
    "function_call": "beta(2)",
    "median_ms": 0.12,
    "peak_memory_kb": 8.0,
    "cyclomatic_complexity": 2,
    "discovered_test_count": 1,
    "replay_trace_count": 2,
    "replay_unique_call_count": 2,
    "replay_partial_success": false,
    "replay_script": "/abs/repo/drive.py",
    "error": ""
  }
]
```

- **Fields**:
  - `median_ms` (number): Median execution time in milliseconds.
  - `peak_memory_kb` (number): Peak memory usage in kilobytes.
  - `cyclomatic_complexity` (integer): Complexity score from `src/utils/complexity.py`.
  - `replay_trace_count` / `replay_unique_call_count`: Volume and uniqueness of trace coverage.
  - `replay_partial_success` (bool): Whether the underlying replay run had partial failures.
  - `error` (string): Empty on success, non-empty on failure (if you choose to wrap this list into an object, keep `error` top-level).

- **Notes**:
  - The **ranking formula is owned by the backend** and can evolve without changing the contract, as long as the output fields remain.
  - The UI should not attempt to recompute ranks; it should display them as-is, potentially with small visual explanations.

---

### 3. `POST /replay/optimize-best` — Optimize Best Replay Target

**Purpose**: One-click flow for the UI. Internally: trace, rank, select the top candidate, run the optimization loop, and return both baseline and optimized metrics.

**Request body**:

```json
{
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py"
}
```

**Success response** (shape):

```json
{
  "selected_source_file": "/abs/repo/pkg/b.py",
  "selected_function": "beta",
  "replay_trace_count": 2,
  "optimized_code": "def beta(...): ...",
  "iteration_number": 1,
  "metrics": {
    "execution_time": 0.12,
    "memory_usage": 8.0,
    "cpu_usage": null,
    "code_complexity": 2,
    "test_coverage": 100.0
  },
  "baseline_metrics": {
    "execution_time": 0.14,
    "memory_usage": 8.5,
    "cpu_usage": null,
    "code_complexity": 3,
    "test_coverage": 100.0
  },
  "test_passed": true,
  "improvement_ratio": 1.16,
  "termination_reason": "execution time within target",
  "converged": true,
  "error": ""
}
```

- **Key semantics**:
  - `optimized_code`:
    - A full code string for the optimized function (ready to apply / show in diff).
  - `metrics` vs `baseline_metrics`:
    - `metrics`: after-optimization metrics.
    - `baseline_metrics`: before-optimization metrics.
  - `test_passed`:
    - True only if the optimized function passes the test suite + property-based tests.
  - `improvement_ratio`:
    - Backend-owned scalar summarizing overall improvement (e.g. speedup factor).
  - `converged`:
    - True when the optimization loop decided to stop (e.g. target reached, or no further safe improvement).
  - `termination_reason`:
    - Human-readable reason, e.g. `"execution time within target"`.

**UI behavior**:

- Display before/after metrics side by side.
- Show the `optimized_code` diff against the original.
- If `error` is non-empty, surface it prominently and do not apply `optimized_code` automatically.

---

### 4. `POST /replay/optimize-one` — Optimize Specific Replay Target

**Purpose**: Optimize a specific replay-backed function chosen by the user (usually selected from the inspect/rank screens).

**Request body**:

```json
{
  "source_file": "/absolute/path/to/file.py",
  "function_name": "target_fn",
  "script_path": "/absolute/path/to/driver.py"
}
```

- **Fields**:
  - `source_file` (string, required): Absolute path to the Python file containing the target function.
  - `function_name` (string, required): Name of the function to optimize.
  - `script_path` (string, required): Absolute path to the replay driver script.

**Response**:

- **Same shape** as `POST /replay/optimize-best`, with the additional guarantee that:
  - `selected_source_file === source_file`
  - `selected_function === function_name`

**UI behavior**:

- The UI should call this endpoint when the user explicitly picks a candidate from:
  - The `/replay/inspect` list, or
  - The `/replay/rank` results.

---

## Suggested UI Flow (End-to-End)

1. **Inspect**:
   - Call `POST /replay/inspect`.
   - Display observed candidates and basic replay info.
2. **Rank (optional but recommended)**:
   - Call `POST /replay/rank` to get best-first ordering.
   - Show rank, metrics, and hints (e.g. complexity, tests).
3. **Optimize**:
   - Either:
     - Call `POST /replay/optimize-best` for a one-click “do the thing” workflow, or
     - Let the user pick a candidate and call `POST /replay/optimize-one` with `source_file` + `function_name`.
4. **Review & apply**:
   - Show before/after metrics, diff of `optimized_code`, and `termination_reason`.
   - Only allow applying changes when `test_passed` is `true` and `error` is empty.

---

## Local Development & Testing Notes

- **Backend entrypoints**:
  - The endpoints above map to:
    - `inspect_replay_repo(...)`
    - `discover_and_rank_replay_repo(...)`
    - `optimize_best_replay_in_repo(...)`
    - `optimize_replay_function(...)`
- **Testing**:
  - Use `test_simple.jac` and other sample scripts as minimal smoke tests for the API.
  - Ensure all endpoints always include an `error` field (empty string on success).

---

## Future Extensions (Non-Contractual)

- **Pagination / limits** for large repos (e.g. limit number of candidates).
- **Filtering**:
  - By complexity, coverage, trace counts, or file patterns.
- **Auth & multi-tenant**:
  - Per-user isolation if running as a shared service.
- **Additional metrics**:
  - CPU usage, I/O counts, allocation rate, etc., surfaced from the profiler.

