"""Code complexity analysis via radon."""

import ast;

"""Compute complexity metrics for Python source code using radon.

Returns dict with cyclomatic_complexity, max_complexity, complexity_rank,
maintainability_index, loc, num_functions, and error.
"""
def compute_complexity(source_code: str) -> dict {

    has_radon = True;
    try {
        import from radon.complexity { cc_visit, cc_rank }
        import from radon.metrics { mi_visit }
        import from radon.raw { analyze }
    } except ImportError {
        has_radon = False;
    }

    if not has_radon {
        return _fallback(source_code);
    }

    try {
        blocks = cc_visit(source_code);
    } except SyntaxError as e {
        return {
            "cyclomatic_complexity": 0,
            "max_complexity": 0,
            "complexity_rank": "?",
            "maintainability_index": 0.0,
            "loc": 0,
            "num_functions": 0,
            "error": str(e)
        };
    }

    complexities = [b.complexity for b in blocks];
    avg_cc = sum(complexities) / len(complexities) if complexities else 1;
    max_cc = max(complexities) if complexities else 1;
    rank = cc_rank(avg_cc);

    num_functions = sum(1 for b in blocks if b.letter in ("F", "M"));

    mi = 0.0;
    try {
        mi = mi_visit(source_code, multi=True);
    } except Exception {
        ;
    }

    loc = 0;
    try {
        raw = analyze(source_code);
        loc = raw.loc;
    } except Exception {
        loc = len([l for l in source_code.splitlines() if l.strip() and not l.strip().startswith("#")]);
    }

    mi_value = 0.0;
    if mi is not None {
        # Approximate rounding to 2 decimal places without using round()
        mi_value = float(int(float(mi) * 100.0)) / 100.0;
    }

    return {
        "cyclomatic_complexity": round(avg_cc),
        "max_complexity": max_cc,
        "complexity_rank": rank,
        "maintainability_index": mi_value,
        "loc": loc,
        "num_functions": num_functions,
        "error": ""
    };
}


"""Minimal fallback when radon is not installed."""
def _fallback(source_code: str) -> dict {
    try {
        tree = ast.parse(source_code);
    } except SyntaxError as e {
        return {
            "cyclomatic_complexity": 0,
            "max_complexity": 0,
            "complexity_rank": "?",
            "maintainability_index": 0.0,
            "loc": 0,
            "num_functions": 0,
            "error": f"radon not installed, fallback failed: {e}"
        };
    }

    decision_points = 0;
    num_functions = 0;
    for node in ast.walk(tree) {
        if isinstance(node, (ast.If, ast.IfExp, ast.For, ast.While, ast.ExceptHandler)) {
            decision_points = decision_points + 1;
        }
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) {
            num_functions = num_functions + 1;
        }
        if isinstance(node, ast.BoolOp) {
            decision_points = decision_points + len(node.values) - 1;
        }
    }

    loc = len([l for l in source_code.splitlines() if l.strip() and not l.strip().startswith("#")]);

    return {
        "cyclomatic_complexity": decision_points + 1,
        "max_complexity": decision_points + 1,
        "complexity_rank": "?",
        "maintainability_index": 0.0,
        "loc": loc,
        "num_functions": num_functions,
        "error": "radon not installed; using basic fallback"
    };
}
