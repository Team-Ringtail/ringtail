"""
GitHub OAuth, App installation, session, and repo access endpoints.
"""

import importlib;


def:pub get_github_app_install_info(state: str = "") -> dict {
    mod = importlib.import_module("src.core.github_repo_service");
    install_info = getattr(mod, "get_github_app_install_info");
    return install_info(state if state != "" else None, None);
}


def:pub handle_github_app_install_callback(
    installation_id: int,
    setup_action: str = "",
    state: str = ""
) -> dict {
    mod = importlib.import_module("src.core.github_repo_service");
    callback = getattr(mod, "handle_github_app_install_callback");
    return callback(
        installation_id,
        setup_action if setup_action != "" else None,
        state if state != "" else None,
        None
    );
}


def:pub verify_github_repo_access(request: dict) -> dict {
    mod = importlib.import_module("src.core.github_repo_service");
    verify_access = getattr(mod, "verify_repo_access");
    auth = request.get("auth", {});
    if auth is None or not isinstance(auth, dict) {
        auth = {};
    }
    return verify_access(
        str(request.get("repo_url", "")),
        dict(auth),
        request.get("token", None)
    );
}


def:pub get_github_login_url(redirect_uri: str = "") -> dict {
    mod = importlib.import_module("src.core.github_oauth");
    return getattr(mod, "get_login_url")(redirect_uri);
}


def:pub exchange_github_code(code: str, state: str, redirect_uri: str = "") -> dict {
    oauth = importlib.import_module("src.core.github_oauth");
    sessions = importlib.import_module("src.core.session_store");
    result = getattr(oauth, "exchange_code")(code, state, redirect_uri);
    if "error" in result {
        return result;
    }
    session = getattr(sessions, "create_session")(result["github_user"]);
    return {
        "session_token": session["session_token"],
        "github_login": session["github_login"],
        "github_user_id": session["github_user_id"],
        "github_avatar_url": session.get("github_avatar_url", "")
    };
}


def:pub get_session(session_token: str) -> dict {
    mod = importlib.import_module("src.core.session_store");
    session = getattr(mod, "validate_session")(session_token);
    if session is None {
        return {"error": "Invalid or expired session"};
    }
    install = getattr(mod, "get_installation")(session["github_user_id"]);
    if install is None {
        install = {};
    }
    return {
        "github_login": session["github_login"],
        "github_user_id": session["github_user_id"],
        "github_avatar_url": session.get("github_avatar_url", ""),
        "installation": install
    };
}


def:pub logout(session_token: str) -> dict {
    mod = importlib.import_module("src.core.session_store");
    getattr(mod, "delete_session")(session_token);
    return {"success": True};
}


def:pub list_github_repos(session_token: str) -> dict {
    sessions = importlib.import_module("src.core.session_store");
    session = getattr(sessions, "validate_session")(session_token);
    if session is None {
        return {"error": "Invalid or expired session", "repositories": []};
    }
    install = getattr(sessions, "get_installation")(session["github_user_id"]);
    if install is None or install.get("installation_id") is None {
        return {"error": "No GitHub App installation found. Install the app first.", "repositories": []};
    }
    try {
        repo_service = importlib.import_module("src.core.github_repo_service");
        list_repos = getattr(repo_service, "list_installation_repositories");
        return list_repos(int(install["installation_id"]));
    } except Exception as e {
        return {"error": str(e), "repositories": []};
    }
}


def:pub save_github_installation(session_token: str, installation_id: int, account_login: str = "") -> dict {
    sessions = importlib.import_module("src.core.session_store");
    session = getattr(sessions, "validate_session")(session_token);
    if session is None {
        return {"error": "Invalid or expired session"};
    }
    record = getattr(sessions, "save_installation")(
        session["github_user_id"],
        installation_id,
        account_login
    );
    return {"success": True, "installation": record};
}
