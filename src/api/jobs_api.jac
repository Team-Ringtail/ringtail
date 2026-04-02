"""
Async job submission and polling endpoints.
"""

import importlib;

import from src.api.optimization_requests { run_optimization_request }


def:pub submit_optimization_job(request: dict) -> dict {
    mod = importlib.import_module("src.core.async_jobs");
    submit_job = getattr(mod, "submit_job");
    return submit_job(request);
}


def:pub get_optimization_job(job_id: str) -> dict {
    mod = importlib.import_module("src.core.async_jobs");
    get_job = getattr(mod, "get_job");
    return get_job(job_id);
}


def:pub run_repo_agent_sync(request: dict) -> dict {
    payload = dict(request);
    payload["operation"] = "run_repo_agent_job";
    return run_optimization_request(payload);
}


def:pub submit_repo_agent_job(request: dict) -> dict {
    payload = dict(request);
    payload["operation"] = "run_repo_agent_job";
    session_token = payload.get("session_token", "");
    auth = payload.get("auth", {});
    if auth is None or not isinstance(auth, dict) {
        auth = {};
    }
    if session_token != "" and "installation_id" not in auth {
        sessions = importlib.import_module("src.core.session_store");
        install = getattr(sessions, "get_installation_for_session")(session_token);
        if install is not None {
            print(
                "[RT-SERVER] submit_repo_agent_job linked installation from session:",
                install["installation_id"]
            );
            auth["installation_id"] = install["installation_id"];
            payload["auth"] = auth;
        } else {
            print("[RT-SERVER] submit_repo_agent_job session has no linked installation");
        }
    } elif "installation_id" in auth {
        print(
            "[RT-SERVER] submit_repo_agent_job received installation_id in auth:",
            auth["installation_id"]
        );
    }
    return submit_optimization_job(payload);
}


def:pub get_repo_agent_job(job_id: str) -> dict {
    return get_optimization_job(job_id);
}


def:pub wait_job_notification(job_id: str, since_seq: int = 0, timeout_s: float = 25.0) -> dict {
    mod = importlib.import_module("src.core.job_stream");
    return getattr(mod, "wait_job_notification")(job_id, since_seq, timeout_s);
}


def:pub get_recent_jobs(limit: int = 10) -> list {
    mod = importlib.import_module("src.core.product_support");
    func = getattr(mod, "list_recent_jobs");
    return func(limit);
}
