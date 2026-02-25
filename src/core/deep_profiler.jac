"""Deep per-line profiling via Scalene.

Runs Scalene in a subprocess to produce per-line CPU and memory data,
then parses the JSON output into structured LineProfile / DetailedProfile objects.
"""

import json;
import os;
import subprocess;
import sys;
import tempfile;
import from typing { Any, Dict, List }

import from src.models.types { DetailedProfile, LineProfile }


glob _WRAPPER_TEMPLATE: str = """\
import sys
sys.path.insert(0, ".")
from solution import *

for _i in range({num_iterations}):
    {function_call}
""";


def _make_error(msg: str) -> DetailedProfile {
    return DetailedProfile(
        line_profiles=[],
        hotspots=[],
        python_vs_native_ratio=1.0,
        total_cpu_seconds=0.0,
        total_memory_mb=0.0,
        success=False,
        error=msg
    );
}


def _parse_scalene_json(data: dict, solution_filename: str) -> DetailedProfile {
    """Parse Scalene's JSON output into a DetailedProfile."""
    files_data = data.get("files", {});

    target_key = None;
    for key in files_data {
        if solution_filename in key {
            target_key = key;
            break;
        }
    }

    if target_key is None {
        return _make_error(
            f"Solution file not found in Scalene output (keys: {list(files_data.keys())})"
        );
    }

    file_data = files_data[target_key];
    lines = file_data.get("lines", []);

    total_cpu = 0.0;
    total_python = 0.0;
    total_native = 0.0;
    total_memory = 0.0;

    line_profiles: list = [];
    for entry in lines {
        lineno = entry.get("lineno", 0);
        cpu_pct_python = entry.get("n_cpu_percent_python", 0.0);
        cpu_pct_c = entry.get("n_cpu_percent_c", 0.0);
        cpu_pct = cpu_pct_python + cpu_pct_c;
        mem_mb = entry.get("n_avg_mb", 0.0) or entry.get("n_peak_mb", 0.0);

        python_frac = 1.0;
        if cpu_pct > 0 {
            python_frac = cpu_pct_python / cpu_pct;
        }

        total_cpu = total_cpu + cpu_pct;
        total_python = total_python + cpu_pct_python;
        total_native = total_native + cpu_pct_c;
        total_memory = total_memory + mem_mb;

        if cpu_pct > 0 or mem_mb > 0 {
            line_profiles.append(
                LineProfile(
                    lineno=lineno,
                    cpu_percent=cpu_pct,
                    memory_mb=mem_mb,
                    python_fraction=python_frac
                )
            );
        }
    }

    hotspots = sorted(line_profiles, key=lambda lp: lp.cpu_percent, reverse=True)[:5];

    overall_python_ratio = 1.0;
    if total_cpu > 0 {
        overall_python_ratio = total_python / total_cpu;
    }

    elapsed = data.get("elapsed_time_sec", 0.0);

    return DetailedProfile(
        line_profiles=line_profiles,
        hotspots=hotspots,
        python_vs_native_ratio=overall_python_ratio,
        total_cpu_seconds=elapsed,
        total_memory_mb=total_memory,
        success=True,
        error=""
    );
}


def deep_profile(
    code: str,
    function_call: str,
    num_iterations: int = 5,
    timeout_seconds: int = 60
) -> DetailedProfile {
    """Run Scalene on a Python function and return per-line profiling data."""
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_deep_");
    solution_path = os.path.join(tmp_dir, "solution.py");
    wrapper_path = os.path.join(tmp_dir, "_wrapper.py");
    output_path = os.path.join(tmp_dir, "_scalene_out.json");

    try {
        with open(solution_path, "w") as f {
            f.write(code);
        }

        wrapper_src = _WRAPPER_TEMPLATE.format(
            num_iterations=num_iterations,
            function_call=function_call
        );
        with open(wrapper_path, "w") as f {
            f.write(wrapper_src);
        }

        result = subprocess.run(
            [
                sys.executable,
                "-m", "scalene",
                "--json",
                "--outfile", output_path,
                "--no-browser",
                "--cpu", "--memory",
                "_wrapper.py"
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir
        );

        if not os.path.exists(output_path) {
            stderr = result.stderr.strip() or result.stdout.strip();
            return _make_error(f"Scalene produced no output: {stderr}");
        }

        with open(output_path, "r") as f {
            scalene_data = json.load(f);
        }

        return _parse_scalene_json(scalene_data, "solution.py");

    } except subprocess.TimeoutExpired {
        return _make_error(f"Scalene timed out after {timeout_seconds}s");
    } except json.JSONDecodeError as e {
        return _make_error(f"Failed to parse Scalene JSON: {e}");
    } except FileNotFoundError {
        return _make_error("Scalene not installed. Run: pip install scalene");
    } except Exception as e {
        return _make_error(str(e));
    } finally {
        for fname in os.listdir(tmp_dir) {
            fpath = os.path.join(tmp_dir, fname);
            if os.path.isfile(fpath) {
                os.remove(fpath);
            }
        }
        try {
            os.rmdir(tmp_dir);
        } except OSError {
            ;
        }
    }
}
