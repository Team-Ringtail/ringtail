"""
Health, diagnostics, and run registry endpoints.
"""

import importlib;


def:pub health -> dict {
    return {"status": "healthy", "service": "ringtail", "version": "0.1.0"};
}


def:pub hello(name: str = "Ringtail") -> dict {
    return {"message": f"Hello from {name}!", "status": "ok"};
}


def:pub get_auth_readiness -> dict {
    mod = importlib.import_module("src.core.product_support");
    func = getattr(mod, "get_auth_readiness");
    return func();
}


def:pub get_config_doctor -> dict {
    mod = importlib.import_module("src.core.product_support");
    func = getattr(mod, "config_doctor");
    return func();
}


def:pub get_latest_run(kind: str = "any") -> dict {
    mod = importlib.import_module("src.core.run_registry");
    func = getattr(mod, "get_latest_run");
    return func(kind);
}


def:pub list_recent_runs(limit: int = 50, kind: str = "any", surface: str = "any", outcome: str = "any") -> dict {
    mod = importlib.import_module("src.core.run_registry");
    func = getattr(mod, "list_recent_runs");
    rows = func(int(limit), str(kind), str(surface), str(outcome));
    return {"success": True, "runs": rows};
}


def:pub hydrate_run_entry(entry: dict) -> dict {
    mod = importlib.import_module("src.core.run_registry");
    func = getattr(mod, "hydrate_run_entry");
    if entry is None {
        return {"success": False, "error": "missing entry", "activity_log_lines": [], "run_display": {}};
    }
    return func(entry);
}
