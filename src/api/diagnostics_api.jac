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
