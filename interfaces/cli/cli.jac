#!/usr/bin/env python3
"""
Command-line interface for Ringtail

Usage:
    python cli.py path/to/file.py function_name
"""

import argparse
import ast
import sys


def extract_function_source(file_path: str, function_name: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            # Python 3.8+ provides end_lineno
            if hasattr(node, "end_lineno"):
                lines = source.splitlines()
                func_lines = lines[node.lineno - 1 : node.end_lineno]
                return "\n".join(func_lines)
            else:
                raise RuntimeError("Python 3.8+ required (end_lineno not available).")

    raise ValueError(f"Function '{function_name}' not found in {file_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract a function from a Python file.")
    parser.add_argument("file", help="Path to the Python file")
    parser.add_argument("function", help="Function name to extract")

    args = parser.parse_args()

    try:
        result = extract_function_source(args.file, args.function)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()