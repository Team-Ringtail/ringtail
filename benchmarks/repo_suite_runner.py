#!/usr/bin/env python3
"""
Run Ringtail's repo-agent across a suite of Python repositories and emit
JSON/CSV summaries that are easy to graph for demos.

Manifest format:
{
  "repos": [
    {
      "name": "sample-repo",
      "repo_url": "https://github.com/org/repo.git",
      "prompt": "make this faster",
      "base_branch": "main",
      "test_command": "python -m pytest tests",
      "backend_config": {"backend": "blaxel"}
    }
  ]
}
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.core.repo_agent import run_repo_agent_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repo-agent benchmark suite")
    parser.add_argument("manifest", help="Path to suite manifest JSON")
    parser.add_argument("--output-json", default="benchmarks/repo_suite_results.json", help="JSON output path")
    parser.add_argument("--output-csv", default="benchmarks/repo_suite_results.csv", help="CSV output path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    data = json.loads(manifest_path.read_text())
    repos = data.get("repos", [])
    results = []

    for raw_entry in repos:
        entry = dict(raw_entry)
        name = entry.get("name") or _repo_name(entry.get("repo_url", "repo"))
        try:
            result = run_repo_agent_job(entry)
            row = {
                "name": name,
                "repo_url": entry.get("repo_url", ""),
                "status": "success" if result.get("success", False) else "failed",
                "selected_function": result.get("selected_target", {}).get("function_name", ""),
                "selected_source_file": result.get("selected_target", {}).get("source_file", ""),
                "improvement_ratio": result.get("winner_result", {}).get("improvement_ratio", 0.0),
                "is_significant": result.get("winner_result", {}).get("is_significant", False),
                "validation_success": result.get("validation_result", {}).get("success", False),
                "backend": entry.get("backend_config", {}).get("backend", "local"),
                "auth_mode": result.get("auth", {}).get("mode", ""),
                "error": "",
            }
        except Exception as exc:
            row = {
                "name": name,
                "repo_url": entry.get("repo_url", ""),
                "status": "failed",
                "selected_function": "",
                "selected_source_file": "",
                "improvement_ratio": 0.0,
                "is_significant": False,
                "validation_success": False,
                "backend": entry.get("backend_config", {}).get("backend", "local"),
                "auth_mode": "",
                "error": str(exc),
            }
        results.append(row)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps({"results": results}, indent=2, default=str))

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()) if results else [
            "name", "repo_url", "status", "selected_function", "selected_source_file",
            "improvement_ratio", "is_significant", "validation_success", "backend", "auth_mode", "error"
        ])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(json.dumps({"results": results}, indent=2, default=str))


def _repo_name(repo_url: str) -> str:
    cleaned = repo_url.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned.split("/")[-1] if cleaned else "repo"


if __name__ == "__main__":
    main()
