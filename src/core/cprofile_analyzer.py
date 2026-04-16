"""
Profile-driven call-graph analysis using cProfile.

Runs a user-provided entry point under cProfile, extracts per-function
timing stats and caller/callee relationships, identifies hot functions
via a configurable threshold, and builds a bottom-up optimization DAG.
"""
from __future__ import annotations

import functools
import os
import pstats
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field


@dataclass
class FunctionProfile:
    module: str
    name: str
    file_path: str
    lineno: int
    tottime: float
    cumtime: float
    ncalls: int
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)
    hotness_pct: float = 0.0


@dataclass
class ProfileAnalysis:
    functions: dict[str, FunctionProfile]
    call_graph: dict[str, list[str]]
    total_time: float
    entry_point: str
    repo_path: str


@dataclass
class CallDAG:
    levels: list[list[str]]
    nodes: dict[str, FunctionProfile]
    edges: dict[str, list[str]]


def _func_key(filename: str, lineno: int, name: str) -> str:
    return f"{filename}:{lineno}:{name}"


_SKIP_SEGMENTS = frozenset({"site-packages", ".venv", "venv", "__pycache__", ".tox", "node_modules"})


@functools.lru_cache(maxsize=2048)
def _repo_realpath(repo_path: str) -> str:
    return os.path.realpath(repo_path)


@functools.lru_cache(maxsize=4096)
def _normalize_profile_filename(filename: str, repo_path: str) -> str | None:
    """Return an absolute real path for profile entries that refer to source files."""
    if not filename or filename.startswith("<") or filename == "~":
        return None
    candidate = filename if os.path.isabs(filename) else os.path.join(repo_path, filename)
    return os.path.realpath(candidate)


def _is_user_code(filename: str, repo_path: str) -> bool:
    """Return True if *filename* belongs to the repo, not stdlib/site-packages."""
    abs_file = _normalize_profile_filename(filename, repo_path)
    if abs_file is None:
        return False
    abs_repo = _repo_realpath(repo_path)
    try:
        common = os.path.commonpath([abs_file, abs_repo])
    except ValueError:
        return False
    if common != abs_repo:
        return False
    rel = os.path.relpath(abs_file, abs_repo)
    return not any(seg in _SKIP_SEGMENTS for seg in rel.split(os.sep))


def run_cprofile_analysis(
    repo_path: str,
    entry_point: str,
    timeout: int = 300,
    venv_python: str = "",
) -> ProfileAnalysis:
    """Run *entry_point* under cProfile inside *repo_path* and parse the results."""

    with tempfile.NamedTemporaryFile(suffix=".prof", delete=False) as tmp:
        prof_path = tmp.name

    try:
        python_bin = _resolve_python(repo_path, venv_python)
        ep = _rewrite_entry_python(entry_point, python_bin)
        cmd = f"{python_bin} -m cProfile -o {shlex.quote(prof_path)} {ep}"
        subprocess.run(
            cmd,
            shell=True,
            cwd=repo_path,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )

        if not os.path.exists(prof_path) or os.path.getsize(prof_path) == 0:
            raise RuntimeError(
                f"cProfile produced no output. Entry point '{entry_point}' "
                "may have failed or produced no profiling data."
            )

        stats = pstats.Stats(prof_path)
        return _parse_pstats(stats, repo_path, entry_point)
    finally:
        if os.path.exists(prof_path):
            os.unlink(prof_path)


def _parse_pstats(
    stats: pstats.Stats,
    repo_path: str,
    entry_point: str,
) -> ProfileAnalysis:
    """Extract structured data from a pstats.Stats object."""

    repo_root = os.path.realpath(repo_path)
    functions: dict[str, FunctionProfile] = {}
    call_graph: dict[str, list[str]] = {}
    total_time: float = stats.total_tt  # type: ignore[attr-defined]

    # stats.stats maps (filename, lineno, name) -> (ncalls, totcalls, tottime, cumtime, callers)
    raw_stats: dict = stats.stats  # type: ignore[attr-defined]
    for (filename, lineno, name), (
        _primitive_calls,
        ncalls,
        tottime,
        cumtime,
        _callers,
    ) in raw_stats.items():
        normalized_file = _normalize_profile_filename(filename, repo_root)
        if normalized_file is None or not _is_user_code(filename, repo_root):
            continue

        key = _func_key(normalized_file, lineno, name)
        module = os.path.relpath(normalized_file, repo_root).replace(os.sep, ".").removesuffix(".py")

        functions[key] = FunctionProfile(
            module=module,
            name=name,
            file_path=normalized_file,
            lineno=lineno,
            tottime=tottime,
            cumtime=cumtime,
            ncalls=ncalls,
            hotness_pct=(tottime / total_time * 100) if total_time > 0 else 0.0,
        )

    # Build caller/callee edges from stats.all_callees
    # all_callees maps (filename, lineno, name) -> {(callee_file, callee_line, callee_name): stats}
    if hasattr(stats, "all_callees") and getattr(stats, "all_callees", None):
        callees_map: dict = stats.all_callees  # type: ignore[attr-defined]
    else:
        stats.calc_callees()
        callees_map = stats.all_callees  # type: ignore[attr-defined]

    for (caller_file, caller_line, caller_name), callees in callees_map.items():
        normalized_caller = _normalize_profile_filename(caller_file, repo_root)
        if normalized_caller is None:
            continue
        caller_key = _func_key(normalized_caller, caller_line, caller_name)
        if caller_key not in functions:
            continue

        callee_keys = []
        for callee_file, callee_line, callee_name in callees:
            normalized_callee = _normalize_profile_filename(callee_file, repo_root)
            if normalized_callee is None:
                continue
            callee_key = _func_key(normalized_callee, callee_line, callee_name)
            if callee_key in functions:
                callee_keys.append(callee_key)
                if callee_key not in functions[callee_key].callers:
                    functions[callee_key].callers.append(caller_key)

        functions[caller_key].callees = callee_keys
        if callee_keys:
            call_graph[caller_key] = callee_keys

    return ProfileAnalysis(
        functions=functions,
        call_graph=call_graph,
        total_time=total_time,
        entry_point=entry_point,
        repo_path=repo_path,
    )


def compute_hotness_threshold(
    analysis: ProfileAnalysis,
    pct_threshold: float = 5.0,
    pareto_target: float = 0.80,
) -> set[str]:
    """Identify hot functions by percentage-of-total and/or Pareto cutoff.

    Returns the union of:
    - Functions whose tottime exceeds *pct_threshold*% of total time
    - The minimal set of functions covering *pareto_target* fraction of total time
    """
    hot: set[str] = set()

    for key, fp in analysis.functions.items():
        if fp.hotness_pct >= pct_threshold:
            hot.add(key)

    # Pareto: sort by tottime descending, accumulate until we cover pareto_target
    sorted_funcs = sorted(
        analysis.functions.items(),
        key=lambda kv: kv[1].tottime,
        reverse=True,
    )
    accumulated = 0.0
    for key, fp in sorted_funcs:
        if analysis.total_time <= 0:
            break
        accumulated += fp.tottime
        hot.add(key)
        if accumulated / analysis.total_time >= pareto_target:
            break

    return hot


def build_call_dag(
    analysis: ProfileAnalysis,
    hot_functions: set[str],
) -> CallDAG:
    """Build a bottom-up DAG from the call graph, filtered to hot functions.

    Merges strongly connected components (mutual recursion) into single nodes.
    Returns levels where level 0 = leaves (no hot callees).
    """
    nodes = {k: v for k, v in analysis.functions.items() if k in hot_functions}
    edges: dict[str, list[str]] = {}
    for caller, callees in analysis.call_graph.items():
        if caller not in hot_functions:
            continue
        hot_callees = [c for c in callees if c in hot_functions]
        if hot_callees:
            edges[caller] = hot_callees

    # Detect and merge cycles via Tarjan's algorithm
    merged_nodes, merged_edges, _ = _merge_cycles(nodes, edges)

    levels = _topological_levels(merged_nodes, merged_edges)

    return CallDAG(levels=levels, nodes=merged_nodes, edges=merged_edges)


def _merge_cycles(
    nodes: dict[str, FunctionProfile],
    edges: dict[str, list[str]],
) -> tuple[dict[str, FunctionProfile], dict[str, list[str]], dict[str, str]]:
    """Merge strongly connected components into single representative nodes."""
    sccs = _tarjan_scc(set(nodes.keys()), edges)

    key_to_group: dict[str, str] = {}
    merged_nodes: dict[str, FunctionProfile] = {}
    for scc in sccs:
        representative = sorted(scc)[0]
        for member in scc:
            key_to_group[member] = representative
        merged_nodes[representative] = nodes[representative]

    merged_edges: dict[str, list[str]] = {}
    for caller, callees in edges.items():
        caller_rep = key_to_group.get(caller, caller)
        callee_reps = []
        for c in callees:
            c_rep = key_to_group.get(c, c)
            if c_rep != caller_rep and c_rep not in callee_reps:
                callee_reps.append(c_rep)
        if callee_reps:
            existing = merged_edges.get(caller_rep, [])
            for cr in callee_reps:
                if cr not in existing:
                    existing.append(cr)
            merged_edges[caller_rep] = existing

    return merged_nodes, merged_edges, key_to_group


def _tarjan_scc(
    vertices: set[str],
    edges: dict[str, list[str]],
) -> list[list[str]]:
    """Tarjan's algorithm for strongly connected components."""
    index_counter = [0]
    stack: list[str] = []
    lowlink: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in edges.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for v in vertices:
        if v not in index:
            strongconnect(v)

    return sccs


def _topological_levels(
    nodes: dict[str, FunctionProfile],
    edges: dict[str, list[str]],
) -> list[list[str]]:
    """Kahn's algorithm producing levels for bottom-up traversal.

    Level 0 contains leaves (no outgoing edges to other hot functions).
    """
    in_degree: dict[str, int] = {k: 0 for k in nodes}
    reverse_edges: dict[str, list[str]] = {k: [] for k in nodes}

    for caller, callees in edges.items():
        if caller not in nodes:
            continue
        for callee in callees:
            if callee in in_degree:
                in_degree[callee] += 1
                reverse_edges[callee].append(caller)

    # Level 0 = nodes with in_degree 0 (leaves — nobody hot calls them that makes THEM a dependency)
    # Actually for bottom-up: leaves are functions that don't call other hot functions.
    # We want out-degree-based leveling: level 0 = no hot callees.
    out_degree: dict[str, int] = {k: 0 for k in nodes}
    for caller, callees in edges.items():
        if caller in nodes:
            out_degree[caller] = len([c for c in callees if c in nodes])

    levels: list[list[str]] = []
    remaining = set(nodes.keys())

    while remaining:
        current_level = [k for k in remaining if out_degree.get(k, 0) == 0]
        if not current_level:
            # Remaining nodes form a cycle we didn't catch; add them all
            current_level = list(remaining)
        levels.append(sorted(current_level))
        for k in current_level:
            remaining.discard(k)
        # Decrease out_degree for callers of removed nodes
        for removed in current_level:
            for caller, callees in edges.items():
                if caller in remaining and removed in callees:
                    out_degree[caller] = max(0, out_degree[caller] - 1)

    return levels


def _resolve_python(repo_path: str, venv_python: str = "") -> str:
    """Return the python binary to use for profiling."""
    if venv_python and os.path.isfile(venv_python) and _python_binary_usable(venv_python):
        return venv_python
    for venv_dir in (".venv", "venv"):
        candidate = os.path.join(repo_path, venv_dir, "bin", "python")
        if os.path.isfile(candidate) and _python_binary_usable(candidate):
            return candidate
    return sys.executable or "python3"


def _python_binary_usable(python_bin: str) -> bool:
    try:
        completed = subprocess.run(
            [python_bin, "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _rewrite_entry_python(entry_point: str, python_bin: str) -> str:
    """Strip 'python' prefix from entry point since we invoke python_bin separately.

    e.g. "python runner.py" -> "runner.py" (python_bin is already the interpreter)
         "pytest tests/"    -> "-m pytest tests/" (run as module)
    """
    stripped = entry_point.strip()
    if stripped.startswith("python "):
        return stripped[len("python "):]
    if stripped.startswith("python3 "):
        return stripped[len("python3 "):]
    # Non-python commands like "pytest tests/" — run via -m
    for tool in ("pytest", "mypy", "black", "ruff"):
        if stripped.startswith(tool):
            return "-m " + stripped
    return stripped

