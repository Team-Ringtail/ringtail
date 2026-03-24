# Ringtail - AI Agent-Based Code Optimizer
# Main application entry point

import importlib;

import from src.api.optimization_requests { run_optimization_request, get_optimization_operation_contract }
cl import "./styles.css";

# Public functions become REST endpoints automatically with jac start
def:pub health -> dict {
    return {"status": "healthy", "service": "ringtail", "version": "0.1.0"};
}

def:pub hello(name: str = "Ringtail") -> dict {
    return {"message": f"Hello from {name}!", "status": "ok"};
}


def:pub optimize_sync(request: dict) -> dict {
    return run_optimization_request(request);
}


def:pub get_optimization_contract -> dict {
    return get_optimization_operation_contract();
}


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
    # Auto-resolve installation_id from session when not explicitly provided
    session_token = payload.get("session_token", "");
    auth = payload.get("auth", {});
    if auth is None or not isinstance(auth, dict) {
        auth = {};
    }
    if session_token != "" and "installation_id" not in auth {
        sessions = importlib.import_module("src.core.session_store");
        install = getattr(sessions, "get_installation_for_session")(session_token);
        if install is not None {
            auth["installation_id"] = install["installation_id"];
            payload["auth"] = auth;
        }
    }
    return submit_optimization_job(payload);
}


def:pub get_repo_agent_job(job_id: str) -> dict {
    return get_optimization_job(job_id);
}


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


def:pub exchange_github_code(code: str, state: str) -> dict {
    oauth = importlib.import_module("src.core.github_oauth");
    sessions = importlib.import_module("src.core.session_store");
    result = getattr(oauth, "exchange_code")(code, state);
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


def:pub get_recent_jobs(limit: int = 10) -> list {
    mod = importlib.import_module("src.core.product_support");
    func = getattr(mod, "list_recent_jobs");
    return func(limit);
}


def:pub get_latest_run(kind: str = "any") -> dict {
    mod = importlib.import_module("src.core.run_registry");
    func = getattr(mod, "get_latest_run");
    return func(kind);
}


def:pub get_ranked_demo_suite_catalog(benchmark_id: str = "") -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_demo_suite_catalog");
    if benchmark_id != "" {
        return func(benchmark_id);
    }
    return func(None);
}


def:pub get_ranked_demo_benchmarks -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_demo_benchmarks");
    return func();
}


def:pub get_latest_ranked_demo_suite -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_latest_demo_suite_result");
    return func();
}


def:pub get_ranked_demo_job_progress(job_id: str) -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_demo_job_progress");
    return func(job_id);
}


walker test_walker {
    has message: str = "Walker is working";

    can with entry {
        report {"walker_message": self.message, "status": "ok"};
    }
}


cl def:pub app -> JsxElement {
    has healthStatus: dict = {};
    has uiMessage: str = "";
    has activeTab: str = "paste";
    has currentTheme: str = "dark";
    has sessionToken: str = "";
    has githubLogin: str = "";
    has githubAvatarUrl: str = "";
    has githubUserId: int = 0;
    has installationId: int = 0;
    has installAccountLogin: str = "";
    has repoUrl: str = "";
    has repoPrompt: str = "make this faster";
    has repoTestCommand: str = "";
    has repoPublishPr: bool = False;
    has repoJobId: str = "";
    has repoJobStatus: str = "";
    has repoJobResult: str = "";
    has pasteSourceCode: str = "def slow_add(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n";
    has pasteFunctionName: str = "slow_add";
    has pasteFunctionCall: str = "slow_add(5000)";
    has pasteTestCall: str = "slow_add(5)";
    has pasteExpected: str = "10";
    has pasteConfigName: str = "live-fast";
    has pasteAnalysisMode: str = "llm";
    has pasteEnableRunLog: bool = True;
    has pasteJobId: str = "";
    has pasteJobStatus: str = "";
    has pasteError: str = "";
    has pasteImprovementRatio: str = "";
    has pasteExecutionBeforeMs: str = "";
    has pasteExecutionAfterMs: str = "";
    has pasteTerminationReason: str = "";
    has pasteTestPassed: str = "";
    has pasteOriginalCode: str = "";
    has pasteOptimizedCode: str = "";
    has pasteSubmitting: bool = False;
    has pasteSubmittedSourceCode: str = "";
    has pasteExpectedStatus: str = "idle";
    has pasteExpectedPreview: str = "";
    has demoView: str = "setup";
    has demoServerUrl: str = "";
    has demoBenchmarkId: str = "ranked-pitch-repo";
    has demoBenchmarkText: str = "";
    has demoLatestBrowseKind: str = "any";
    has demoTopK: str = "3";
    has demoPerFileK: str = "1";
    has demoJobId: str = "";
    has demoRunStatus: str = "idle";
    has demoRunStage: str = "Ready to run";
    has demoProgressPct: int = 0;
    has demoLogText: str = "Live run events will appear here.";
    has demoOverviewSvg: str = "";
    has demoPassCount: str = "0";
    has demoTargetCount: str = "0";
    has demoAverageSpeedup: str = "0";
    has demoAverageSaved: str = "0";
    has demoFile1Visible: bool = False;
    has demoFile1Text: str = "";
    has demoFile2Visible: bool = False;
    has demoFile2Text: str = "";
    has demoFile3Visible: bool = False;
    has demoFile3Text: str = "";
    has demoFile4Visible: bool = False;
    has demoFile4Text: str = "";
    has demoSelected1Visible: bool = False;
    has demoSelected1Title: str = "";
    has demoSelected1Meta: str = "";
    has demoSelected2Visible: bool = False;
    has demoSelected2Title: str = "";
    has demoSelected2Meta: str = "";
    has demoSelected3Visible: bool = False;
    has demoSelected3Title: str = "";
    has demoSelected3Meta: str = "";
    has demoFinalist1Visible: bool = False;
    has demoFinalist1Text: str = "";
    has demoFinalist2Visible: bool = False;
    has demoFinalist2Text: str = "";
    has demoFinalist3Visible: bool = False;
    has demoFinalist3Text: str = "";
    has demoFinalist4Visible: bool = False;
    has demoFinalist4Text: str = "";
    has demoCard1Visible: bool = False;
    has demoCard1Title: str = "";
    has demoCard1Meta: str = "";
    has demoCard1GraphSvg: str = "";
    has demoCard1Original: str = "";
    has demoCard1Optimized: str = "";
    has demoCard2Visible: bool = False;
    has demoCard2Title: str = "";
    has demoCard2Meta: str = "";
    has demoCard2GraphSvg: str = "";
    has demoCard2Original: str = "";
    has demoCard2Optimized: str = "";
    has demoCard3Visible: bool = False;
    has demoCard3Title: str = "";
    has demoCard3Meta: str = "";
    has demoCard3GraphSvg: str = "";
    has demoCard3Original: str = "";
    has demoCard3Optimized: str = "";
    has pollingInitialized: bool = False;

    def _value(data: any, key: str, fallback: any) -> any {
        if data is None {
            return fallback;
        }
        if key in data {
            return data[key];
        }
        return fallback;
    }

    def _format_demo_benchmarks(data: dict) -> str {
        lines: list = [];
        for item in _value(data, "benchmarks", []) {
            lines.append(
                str(_value(item, "label", "")) + " -> "
                + str(_value(item, "description", ""))
            );
        }
        return "\n".join(lines);
    }

    def _basename(path: str) -> str {
        parts = str(path).split("/");
        if len(parts) == 0 {
            return str(path);
        }
        return str(parts[len(parts) - 1]);
    }

    def _get_query_param(name: str) -> str {
        search = str(globalThis.window.location.search or "");
        if search == "" {
            return "";
        }
        if len(search) > 0 and search[0] == "?" {
            search = search[1:];
        }
        parts = search.split("&");
        for part in parts {
            pieces = part.split("=");
            if len(pieces) >= 2 and pieces[0] == name {
                return str(globalThis.decodeURIComponent(pieces[1]));
            }
        }
        return "";
    }

    def _new_demo_job_id() -> str {
        if "crypto" in globalThis and globalThis.crypto != None and "randomUUID" in globalThis.crypto {
            return "demo-" + str(globalThis.crypto.randomUUID());
        }
        ts = str(int(globalThis.Date.now()));
        rand = str(int(globalThis.Math.floor(globalThis.Math.random() * 1000000)));
        return "demo-" + ts + "-" + rand;
    }

    def _new_paste_job_id() -> str {
        if "crypto" in globalThis and globalThis.crypto != None and "randomUUID" in globalThis.crypto {
            return "paste-" + str(globalThis.crypto.randomUUID());
        }
        ts = str(int(globalThis.Date.now()));
        rand = str(int(globalThis.Math.floor(globalThis.Math.random() * 1000000)));
        return "paste-" + ts + "-" + rand;
    }

    def _set_theme_attr(theme: str) -> None {
        if theme not in ["light", "dark"] {
            return;
        }
        if "document" not in globalThis or globalThis.document is None {
            return;
        }
        if "documentElement" in globalThis.document and globalThis.document.documentElement != None {
            globalThis.document.documentElement.setAttribute("data-theme", theme);
        }
    }

    def _save_theme(theme: str) -> None {
        try {
            globalThis.localStorage.setItem("ringtail_theme", theme);
        } except Exception as err {
            ignored = str(err);
        }
    }

    def _load_theme(default_theme: str = "dark") -> str {
        theme = default_theme;
        try {
            saved = str(globalThis.localStorage.getItem("ringtail_theme") or "");
            if saved in ["light", "dark"] {
                theme = saved;
            }
        } except Exception as err {
            ignored = str(err);
        }
        return theme;
    }

    def _clear_demo_files() -> None {
        demoFile1Visible = False;
        demoFile1Text = "";
        demoFile2Visible = False;
        demoFile2Text = "";
        demoFile3Visible = False;
        demoFile3Text = "";
        demoFile4Visible = False;
        demoFile4Text = "";
    }

    def _set_demo_file(slot: int, item: dict) -> None {
        text = str(_value(item, "file_name", "")) + "  " + str(_value(item, "functions", []));
        if slot == 1 {
            demoFile1Visible = True;
            demoFile1Text = text;
        }
        if slot == 2 {
            demoFile2Visible = True;
            demoFile2Text = text;
        }
        if slot == 3 {
            demoFile3Visible = True;
            demoFile3Text = text;
        }
        if slot == 4 {
            demoFile4Visible = True;
            demoFile4Text = text;
        }
    }

    def _clear_selected_targets() -> None {
        demoSelected1Visible = False;
        demoSelected1Title = "";
        demoSelected1Meta = "";
        demoSelected2Visible = False;
        demoSelected2Title = "";
        demoSelected2Meta = "";
        demoSelected3Visible = False;
        demoSelected3Title = "";
        demoSelected3Meta = "";
    }

    def _set_selected_target(slot: int, item: dict) -> None {
        title = str(_value(item, "function_name", ""));
        fileName = _basename(str(_value(item, "source_file", "")));
        meta = fileName + " | ranked " + str(_value(item, "median_ms", 0.0)) + " ms";
        if slot == 1 {
            demoSelected1Visible = True;
            demoSelected1Title = title;
            demoSelected1Meta = meta;
        }
        if slot == 2 {
            demoSelected2Visible = True;
            demoSelected2Title = title;
            demoSelected2Meta = meta;
        }
        if slot == 3 {
            demoSelected3Visible = True;
            demoSelected3Title = title;
            demoSelected3Meta = meta;
        }
    }

    def _clear_finalists() -> None {
        demoFinalist1Visible = False;
        demoFinalist1Text = "";
        demoFinalist2Visible = False;
        demoFinalist2Text = "";
        demoFinalist3Visible = False;
        demoFinalist3Text = "";
        demoFinalist4Visible = False;
        demoFinalist4Text = "";
    }

    def _set_finalist(slot: int, item: dict) -> None {
        text = str(_value(item, "function_name", "")) + " | " + _basename(str(_value(item, "source_file", "")))
            + " | ranked " + str(_value(item, "median_ms", 0.0)) + " ms";
        if slot == 1 {
            demoFinalist1Visible = True;
            demoFinalist1Text = text;
        }
        if slot == 2 {
            demoFinalist2Visible = True;
            demoFinalist2Text = text;
        }
        if slot == 3 {
            demoFinalist3Visible = True;
            demoFinalist3Text = text;
        }
        if slot == 4 {
            demoFinalist4Visible = True;
            demoFinalist4Text = text;
        }
    }

    def _format_log_text(lines: list) -> str {
        if len(lines) == 0 {
            return "Live run events will appear here.";
        }
        return "\n".join(lines);
    }

    def _apply_single_latest_run_result(meta: dict) -> None {
        functionName = str(_value(meta, "function_name", ""));
        runId = str(_value(meta, "run_id", "latest-run"));
        filePath = str(_value(meta, "file_path", ""));
        rankedMs = _value(meta, "optimized_time_ms", 0.0);
        speedup = _value(meta, "improvement_ratio", 0.0);
        savedPct = _value(meta, "time_saved_pct", 0.0);
        graphSvg = str(_value(meta, "timing_graph_svg_base64", ""));
        label = functionName;
        if label == "" {
            label = runId;
        }
        source = filePath;
        if source == "" {
            source = runId;
        }
        synthesized = {
            "summary": {
                "pass_count": 1,
                "target_count": 1,
                "average_speedup": speedup,
                "average_time_saved_pct": savedPct,
                "results": [
                    {
                        "name": label,
                        "improvement_ratio": speedup,
                        "time_saved_pct": savedPct,
                        "median_ms_ranked": rankedMs,
                        "graph_svg_base64": graphSvg,
                        "original_code": "",
                        "optimized_code": "",
                    }
                ],
            },
            "final_ranked_targets": [
                {
                    "function_name": label,
                    "source_file": source,
                    "median_ms": rankedMs,
                }
            ],
            "per_file_finalists": [
                {
                    "function_name": label,
                    "source_file": source,
                    "median_ms": rankedMs,
                }
            ],
            "suite_overview_svg_base64": graphSvg,
        };
        _apply_demo_result(synthesized);
    }

    def _clear_demo_cards() -> None {
        demoCard1Visible = False;
        demoCard1Title = "";
        demoCard1Meta = "";
        demoCard1GraphSvg = "";
        demoCard1Original = "";
        demoCard1Optimized = "";
        demoCard2Visible = False;
        demoCard2Title = "";
        demoCard2Meta = "";
        demoCard2GraphSvg = "";
        demoCard2Original = "";
        demoCard2Optimized = "";
        demoCard3Visible = False;
        demoCard3Title = "";
        demoCard3Meta = "";
        demoCard3GraphSvg = "";
        demoCard3Original = "";
        demoCard3Optimized = "";
    }

    def _set_demo_card(slot: int, row: dict) -> None {
        title = str(_value(row, "name", ""));
        meta = "speedup " + str(_value(row, "improvement_ratio", 0.0)) + "x | time saved "
            + str(_value(row, "time_saved_pct", 0.0)) + "% | ranked "
            + str(_value(row, "median_ms_ranked", 0.0)) + " ms";
        graphSvg = str(_value(row, "graph_svg_base64", ""));
        originalCode = str(_value(row, "original_code", ""));
        optimizedCode = str(_value(row, "optimized_code", ""));
        if slot == 1 {
            demoCard1Visible = True;
            demoCard1Title = title;
            demoCard1Meta = meta;
            demoCard1GraphSvg = graphSvg;
            demoCard1Original = originalCode;
            demoCard1Optimized = optimizedCode;
        }
        if slot == 2 {
            demoCard2Visible = True;
            demoCard2Title = title;
            demoCard2Meta = meta;
            demoCard2GraphSvg = graphSvg;
            demoCard2Original = originalCode;
            demoCard2Optimized = optimizedCode;
        }
        if slot == 3 {
            demoCard3Visible = True;
            demoCard3Title = title;
            demoCard3Meta = meta;
            demoCard3GraphSvg = graphSvg;
            demoCard3Original = originalCode;
            demoCard3Optimized = optimizedCode;
        }
    }

    def _apply_demo_result(result: dict) -> None {
        summary = _value(result, "summary", {});
        rows = _value(summary, "results", []);
        demoOverviewSvg = str(_value(result, "suite_overview_svg_base64", ""));
        demoPassCount = str(_value(summary, "pass_count", 0));
        demoTargetCount = str(_value(summary, "target_count", 0));
        demoAverageSpeedup = str(_value(summary, "average_speedup", 0.0));
        demoAverageSaved = str(_value(summary, "average_time_saved_pct", 0.0));
        _clear_selected_targets();
        selectedTargets = _value(result, "final_ranked_targets", []);
        if len(selectedTargets) > 0 {
            _set_selected_target(1, selectedTargets[0]);
        }
        if len(selectedTargets) > 1 {
            _set_selected_target(2, selectedTargets[1]);
        }
        if len(selectedTargets) > 2 {
            _set_selected_target(3, selectedTargets[2]);
        }
        _clear_finalists();
        finalists = _value(result, "per_file_finalists", []);
        if len(finalists) > 0 {
            _set_finalist(1, finalists[0]);
        }
        if len(finalists) > 1 {
            _set_finalist(2, finalists[1]);
        }
        if len(finalists) > 2 {
            _set_finalist(3, finalists[2]);
        }
        if len(finalists) > 3 {
            _set_finalist(4, finalists[3]);
        }
        _clear_demo_cards();
        if len(rows) > 0 {
            _set_demo_card(1, rows[0]);
        }
        if len(rows) > 1 {
            _set_demo_card(2, rows[1]);
        }
        if len(rows) > 2 {
            _set_demo_card(3, rows[2]);
        }
    }

    def _reset_paste_result() -> None {
        pasteError = "";
        pasteImprovementRatio = "";
        pasteExecutionBeforeMs = "";
        pasteExecutionAfterMs = "";
        pasteTerminationReason = "";
        pasteTestPassed = "";
        pasteOriginalCode = "";
        pasteOptimizedCode = "";
    }

    def _normalize_source_code(raw: str) -> str {
        text = str(raw).replace("\r\n", "\n").replace("\r", "\n");
        js_text = globalThis.String(text);
        has_real_newline = False;
        has_escaped_newline = False;
        idx = 0;
        while idx < int(js_text.length) {
            code = int(js_text.charCodeAt(idx));
            if code == 10 {
                has_real_newline = True;
            }
            if idx + 1 < int(js_text.length)
                and code == 92
                and int(js_text.charCodeAt(idx + 1)) == 110 {
                has_escaped_newline = True;
            }
            idx = idx + 1;
        }
        if not has_real_newline and has_escaped_newline {
            # Heuristic: user pasted escaped code from JSON/log output.
            decoded_chars: list = [];
            i = 0;
            while i < int(js_text.length) {
                current_code = int(js_text.charCodeAt(i));
                if current_code == 92 and i + 1 < int(js_text.length) {
                    next_code = int(js_text.charCodeAt(i + 1));
                    if next_code == 110 {
                        decoded_chars.append("\n");
                        i = i + 2;
                        continue;
                    }
                    if next_code == 116 {
                        decoded_chars.append("    ");
                        i = i + 2;
                        continue;
                    }
                    if next_code == 114 {
                        i = i + 2;
                        continue;
                    }
                }
                decoded_chars.append(str(js_text[i]));
                i = i + 1;
            }
            text = "".join(decoded_chars);
        }
        trimmed = str(globalThis.String(text).trim());
        if trimmed.startswith("```") and trimmed.endswith("```") {
            lines = trimmed.split("\n");
            if len(lines) >= 2 {
                return "\n".join(lines[1:len(lines) - 1]);
            }
        }
        return text;
    }

    def _set_source_cursor(target: any, pos: int) -> None {
        try {
            globalThis.setTimeout(lambda -> None {
                target.selectionStart = pos;
                target.selectionEnd = pos;
            }, 0);
        } except Exception as cursorErr {
            ignored = str(cursorErr);
        }
    }

    def _update_expected_feedback() -> None {
        expectedText = str(pasteExpected).strip();
        hasValidationCall = str(pasteTestCall).strip() != "";
        if expectedText == "" {
            if hasValidationCall {
                pasteExpectedStatus = "warn";
                pasteExpectedPreview = "Validation call is set with no expected value; run will execute without an assert.";
            } else {
                pasteExpectedStatus = "idle";
                pasteExpectedPreview = "Use JSON literals like 10, \"hello\", true, null, or [1, 2].";
            }
            return;
        }
        try {
            parsed = globalThis.JSON.parse(expectedText);
            pasteExpectedStatus = "ok";
            pasteExpectedPreview = "Valid JSON parsed as: " + str(parsed);
        } except Exception as parseErr {
            ignored = str(parseErr);
            pasteExpectedStatus = "warn";
            pasteExpectedPreview = "Not valid JSON; this value will be sent as raw text.";
        }
    }

    def _parse_expected_value(raw: str) -> dict | list | str | int | float | bool | None {
        text = str(raw).strip();
        if text == "" {
            return None;
        }
        try {
            return globalThis.JSON.parse(text);
        } except Exception as err {
            ignored = str(err);
            return text;
        }
    }

    def handleSourceEditorPaste(e: any) -> None {
        try {
            clipboard = _value(e, "clipboardData", None);
            if clipboard is None {
                return;
            }
            rawText = str(clipboard.getData("text") or "");
            if rawText == "" {
                return;
            }
            normalized = _normalize_source_code(rawText);
            if normalized == rawText {
                return;
            }
            e.preventDefault();
            target = e.target;
            value = str(_value(target, "value", ""));
            start = int(_value(target, "selectionStart", len(value)));
            end = int(_value(target, "selectionEnd", start));
            updated = value[0:start] + normalized + value[end:];
            pasteSourceCode = updated;
            _set_source_cursor(target, start + len(normalized));
        } except Exception as pasteErr {
            ignored = str(pasteErr);
        }
    }

    async def handleSourceEditorKeydown(e: any) -> None {
        key = str(_value(e, "key", ""));
        if bool(_value(e, "metaKey", False)) or bool(_value(e, "ctrlKey", False)) {
            if key == "Enter" {
                e.preventDefault();
                await _submit_paste_job();
                return;
            }
        }
        if key != "Tab" {
            return;
        }
        e.preventDefault();
        target = e.target;
        value = str(_value(target, "value", pasteSourceCode));
        start = int(_value(target, "selectionStart", len(value)));
        end = int(_value(target, "selectionEnd", start));
        if bool(_value(e, "shiftKey", False)) {
            if start == end and start >= 4 and value[start - 4:start] == "    " {
                updated = value[0:start - 4] + value[start:];
                pasteSourceCode = updated;
                _set_source_cursor(target, start - 4);
            }
            return;
        }
        updated = value[0:start] + "    " + value[end:];
        pasteSourceCode = updated;
        _set_source_cursor(target, start + 4);
    }

    def _toggle_theme() -> None {
        if currentTheme == "dark" {
            currentTheme = "light";
        } else {
            currentTheme = "dark";
        }
        _set_theme_attr(currentTheme);
        _save_theme(currentTheme);
    }

    def _apply_paste_result(result: dict) -> None {
        metrics = _value(result, "metrics", {});
        baseline = _value(result, "baseline_metrics", {});
        pasteImprovementRatio = str(_value(result, "improvement_ratio", 0.0));
        pasteExecutionBeforeMs = str(_value(baseline, "execution_time", 0.0));
        pasteExecutionAfterMs = str(_value(metrics, "execution_time", 0.0));
        pasteTerminationReason = str(_value(result, "termination_reason", ""));
        pasteTestPassed = str(_value(result, "test_passed", False));
        pasteOriginalCode = pasteSubmittedSourceCode != "" and pasteSubmittedSourceCode or pasteSourceCode;
        pasteOptimizedCode = str(_value(result, "optimized_code", ""));
        if "error" in result {
            pasteError = str(result["error"]);
        } else {
            pasteError = "";
        }
    }

    async def _submit_paste_job() -> None {
        if pasteSubmitting {
            return;
        }
        expected_job_id = _new_paste_job_id();
        pasteSubmitting = True;
        pasteJobStatus = "submitting";
        pasteJobId = expected_job_id;
        _reset_paste_result();
        uiMessage = "";
        _update_expected_feedback();
        try {
            normalizedSource = _normalize_source_code(pasteSourceCode);
            pasteSourceCode = normalizedSource;
            pasteSubmittedSourceCode = normalizedSource;
            payload = {
                "operation": "optimize_input",
                "job_id": expected_job_id,
                "config_name": pasteConfigName,
                "analysis_mode": pasteAnalysisMode,
                "enable_run_log": pasteEnableRunLog,
                "run_name": "web-paste-optimize",
                "input": {
                    "source_code": normalizedSource,
                    "function_name": pasteFunctionName,
                    "function_call": pasteFunctionCall,
                    "test_cases": []
                }
            };
            if str(pasteTestCall).strip() != "" {
                expected = _parse_expected_value(pasteExpected);
                payload["input"]["test_cases"] = [
                    {"call": pasteTestCall, "expected": expected}
                ];
            }
            submitted = await submit_optimization_job(payload);
            returned_job_id = str(_value(submitted, "job_id", ""));
            returned_status = str(_value(submitted, "status", "queued"));
            if returned_job_id == expected_job_id {
                pasteJobStatus = returned_status;
            } else {
                pasteJobStatus = "queued";
            }
            if expected_job_id == "" {
                pasteJobStatus = "failed";
                pasteError = str(_value(submitted, "error", "No job ID returned"));
            } else {
                await pollPasteJob();
            }
        } except Exception as err {
            pasteJobStatus = "failed";
            pasteError = str(err);
            uiMessage = "Paste optimization failed to submit: " + str(err);
        } finally {
            pasteSubmitting = False;
        }
    }

    async def submitPasteJob(e: any) -> None {
        e.preventDefault();
        await _submit_paste_job();
    }

    async def pollPasteJob() -> None {
        if pasteJobId == "" or pasteJobStatus in ["succeeded", "failed", "not_found", ""] {
            return;
        }
        result = await get_optimization_job(pasteJobId);
        pasteJobStatus = str(_value(result, "status", "running"));
        if pasteJobStatus == "succeeded" {
            _apply_paste_result(_value(result, "result", {}));
        }
        if pasteJobStatus == "failed" {
            pasteError = str(_value(result, "error", "Optimization job failed"));
        }
    }

    async def handleGithubLogin() -> None {
        result = await get_github_login_url("");
        url = _value(result, "url", "");
        if url != "" {
            globalThis.window.location.href = url;
        } else {
            uiMessage = str(_value(result, "error", "OAuth not configured"));
        }
    }

    def _save_session_cookie(token: str) -> None {
        globalThis.document.cookie = "ringtail_session=" + token + "; path=/; max-age=86400; SameSite=Lax";
    }

    def _read_session_cookie() -> str {
        raw = str(globalThis.document.cookie or "");
        if raw == "" {
            return "";
        }
        parts = raw.split("; ");
        for part in parts {
            pieces = part.split("=");
            if len(pieces) >= 2 and pieces[0] == "ringtail_session" {
                return pieces[1];
            }
        }
        return "";
    }

    def _clear_session_cookie() -> None {
        globalThis.document.cookie = "ringtail_session=; path=/; max-age=0";
    }

    async def handleOAuthCallback() -> None {
        code = _get_query_param("code");
        state = _get_query_param("state");
        if code == "" or state == "" {
            uiMessage = "OAuth callback missing code or state.";
            return;
        }
        result = await exchange_github_code(code, state);
        if "error" in result {
            uiMessage = str(result["error"]);
            return;
        }
        sessionToken = str(result["session_token"]);
        githubLogin = str(result["github_login"]);
        githubUserId = int(result["github_user_id"]);
        githubAvatarUrl = str(_value(result, "github_avatar_url", ""));
        await loadInstallation();
        try {
            _save_session_cookie(sessionToken);
            globalThis.window.history.replaceState({}, "", globalThis.window.location.pathname);
        } except Exception as cookieErr {
            uiMessage = "";
        }
    }

    async def restoreSession() -> None {
        saved = _read_session_cookie();
        if saved == "" {
            return;
        }
        result = await get_session(saved);
        if "error" in result {
            _clear_session_cookie();
            return;
        }
        sessionToken = saved;
        githubLogin = str(result["github_login"]);
        githubUserId = int(result["github_user_id"]);
        githubAvatarUrl = str(_value(result, "github_avatar_url", ""));
        iid = int(_value(_value(result, "installation", {}), "installation_id", 0));
        if iid != 0 {
            installationId = iid;
            installAccountLogin = str(_value(_value(result, "installation", {}), "account_login", ""));
        }
    }

    async def handleLogout() -> None {
        if sessionToken != "" {
            await logout(sessionToken);
        }
        _clear_session_cookie();
        sessionToken = "";
        githubLogin = "";
        githubUserId = 0;
        githubAvatarUrl = "";
        installationId = 0;
        installAccountLogin = "";
    }

    async def handleInstallApp() -> None {
        result = await get_github_app_install_info(sessionToken);
        url = _value(result, "install_url", "");
        if url != "" {
            globalThis.window.location.href = url;
        } else {
            uiMessage = "GitHub App not configured on this server.";
        }
    }

    async def loadInstallation() -> None {
        if sessionToken == "" {
            return;
        }
        result = await get_session(sessionToken);
        iid = int(_value(_value(result, "installation", {}), "installation_id", 0));
        if iid != 0 {
            installationId = iid;
            installAccountLogin = str(_value(_value(result, "installation", {}), "account_login", ""));
        }
    }

    async def handleInstallCallback() -> None {
        iid = _get_query_param("installation_id");
        if iid == "" {
            return;
        }
        if sessionToken == "" {
            stateToken = _get_query_param("state");
            if stateToken != "" {
                saved = await get_session(stateToken);
                if "error" not in saved {
                    sessionToken = stateToken;
                    githubLogin = str(_value(saved, "github_login", ""));
                    githubUserId = int(_value(saved, "github_user_id", 0));
                    githubAvatarUrl = str(_value(saved, "github_avatar_url", ""));
                }
            }
        }
        if sessionToken == "" {
            uiMessage = "Session expired. Please sign in again.";
            return;
        }
        result = await save_github_installation(sessionToken, int(iid), "");
        if _value(result, "success", False) {
            installationId = int(iid);
        }
        globalThis.window.history.replaceState({}, "", globalThis.window.location.pathname);
        activeTab = "repo";
    }

    async def submitRepoJob(e: any) -> None {
        e.preventDefault();
        repoJobStatus = "submitting";
        repoJobResult = "";
        uiMessage = "";
        try {
            payload = {
                "repo_url": repoUrl,
                "prompt": repoPrompt,
                "publish_pr": repoPublishPr,
                "session_token": sessionToken
            };
            if repoTestCommand != "" {
                payload["test_command"] = repoTestCommand;
            }
            submitted = await submit_repo_agent_job(payload);
            repoJobId = str(_value(submitted, "job_id", ""));
            repoJobStatus = str(_value(submitted, "status", "queued"));
            if repoJobId == "" {
                repoJobStatus = "failed";
                repoJobResult = str(_value(submitted, "error", "No job ID returned"));
            }
        } except Exception as err {
            repoJobStatus = "failed";
            repoJobResult = str(err);
            uiMessage = "Job submission failed: " + str(err);
        }
    }

    async def pollRepoJob() -> None {
        if repoJobId == "" or repoJobStatus in ["succeeded", "failed", ""] {
            return;
        }
        result = await get_repo_agent_job(repoJobId);
        repoJobStatus = str(_value(result, "status", "running"));
        if repoJobStatus == "succeeded" {
            repoJobResult = "Optimization complete. Check the repo for a new PR or preview.";
        }
        if repoJobStatus == "failed" {
            repoJobResult = str(_value(result, "error", "Job failed"));
        }
    }

    async def refreshBenchmarkContext() -> None {
        benchmarks = await get_ranked_demo_benchmarks();
        catalog = await get_ranked_demo_suite_catalog(demoBenchmarkId);
        demoBenchmarkText = _format_demo_benchmarks(benchmarks);
        _clear_demo_files();
        files = _value(catalog, "files", []);
        if len(files) > 0 {
            _set_demo_file(1, files[0]);
        }
        if len(files) > 1 {
            _set_demo_file(2, files[1]);
        }
        if len(files) > 2 {
            _set_demo_file(3, files[2]);
        }
        if len(files) > 3 {
            _set_demo_file(4, files[3]);
        }
    }

    async def loadLatestDemoSuite() -> None {
        selectedKind = str(demoLatestBrowseKind).strip();
        if selectedKind == "" {
            selectedKind = "any";
        }
        latest = await get_latest_run(selectedKind);
        if not bool(_value(latest, "success", False)) {
            uiMessage = str(_value(latest, "error", "Could not locate latest run for kind '" + selectedKind + "'"));
            return;
        }
        latestMeta = _value(latest, "latest", {});
        latestKind = str(_value(latestMeta, "kind", ""));
        latestJobId = str(_value(latestMeta, "job_id", ""));
        latestRunId = str(_value(latestMeta, "run_id", ""));
        if latestKind == "ranked_demo_suite" and latestJobId != "" {
            progress = await get_ranked_demo_job_progress(latestJobId);
            if "result" in progress {
                _apply_demo_result(progress["result"]);
                demoRunStatus = "succeeded";
                demoRunStage = "Showing latest benchmark run";
                demoProgressPct = 100;
                demoView = "results";
                return;
            }
        }
        if latestKind != "ranked_demo_suite" {
            _apply_single_latest_run_result(latestMeta);
            demoRunStatus = str(_value(latestMeta, "status", "succeeded"));
            demoRunStage = "Showing latest " + latestKind + " run";
            demoProgressPct = 100;
            demoView = "results";
            if latestRunId != "" {
                uiMessage = "Showing latest " + latestKind + " run " + latestRunId + " in unified results view.";
            } else {
                uiMessage = "Showing latest " + latestKind + " run in unified results view.";
            }
            return;
        }
        result = await get_latest_ranked_demo_suite();
        if bool(_value(result, "success", False)) or "summary" in result {
            _apply_demo_result(result);
            demoRunStatus = "succeeded";
            demoRunStage = "Showing latest verified benchmark run";
            demoProgressPct = 100;
            demoView = "results";
            return;
        }
        uiMessage = str(_value(result, "error", "Could not load latest benchmark result"));
    }

    async def _start_demo_run() -> None {
        try {
            demoJobId = _new_demo_job_id();
            demoView = "running";
            demoRunStatus = "queued";
            demoRunStage = "Submitting benchmark run";
            demoProgressPct = 6;
            demoLogText = "Submitting benchmark run...";
            uiMessage = "";
            _clear_demo_cards();
            demoOverviewSvg = "";
            serverUrl = demoServerUrl;
            if str(serverUrl).strip() == "" {
                serverUrl = str(globalThis.window.location.origin or "");
            }
            payload = {
                "operation": "run_ranked_demo_suite",
                "job_id": demoJobId,
                "server_url": serverUrl,
                "benchmark_id": demoBenchmarkId,
                "top_k": int(demoTopK),
                "per_file_k": int(demoPerFileK)
            };
            await submit_optimization_job(payload);
            await pollDemoProgress();
        } except Exception as err {
            demoRunStatus = "failed";
            demoRunStage = "Benchmark submission failed";
            demoProgressPct = 0;
            demoLogText = "Benchmark submission failed.\n" + str(err);
            uiMessage = "Could not start benchmark run: " + str(err);
        }
    }

    async def startDemoRun(e: any) -> None {
        e.preventDefault();
        await _start_demo_run();
    }

    async def pollDemoProgress() -> None {
        if demoJobId == "" {
            return;
        }
        progress = await get_ranked_demo_job_progress(demoJobId);
        demoRunStatus = str(_value(progress, "job_status", _value(progress, "status", "running")));
        demoRunStage = str(_value(progress, "stage", "Running benchmark"));
        demoProgressPct = int(_value(progress, "progress_pct", 0));
        demoLogText = _format_log_text(_value(progress, "log_lines", []));
        if str(_value(progress, "job_status", "")) == "succeeded" and "result" in progress {
            _apply_demo_result(_value(progress, "result", {}));
            demoProgressPct = 100;
            demoView = "results";
        }
        if str(_value(progress, "job_status", "")) == "failed" {
            demoRunStage = "Benchmark run failed";
            uiMessage = str(_value(progress, "error", _value(progress, "job_error", "Benchmark run failed")));
        }
    }

    async def tickDemoPolling() -> None {
        if demoView == "running" and demoJobId != "" {
            await pollDemoProgress();
        }
    }

    async def resetToSetup() -> None {
        demoView = "setup";
        demoRunStatus = "idle";
        demoRunStage = "Ready to run";
        demoProgressPct = 0;
        uiMessage = "";
    }

    async can with entry {
        try {
            currentTheme = _load_theme("dark");
            _set_theme_attr(currentTheme);
            if demoServerUrl == "" {
                demoServerUrl = str(globalThis.location.origin);
            }
            healthStatus = await health();
            await restoreSession();
            if _get_query_param("installation_id") != "" {
                await handleInstallCallback();
            } elif _get_query_param("code") != "" and _get_query_param("installation_id") == "" {
                await handleOAuthCallback();
            }
            _update_expected_feedback();
            await refreshBenchmarkContext();
            if not pollingInitialized {
                pollingInitialized = True;
                globalThis.setInterval(lambda -> None { tickDemoPolling(); pollRepoJob(); pollPasteJob(); }, 3000);
            }
        } except Exception as e {
            healthStatus = {"status": "error", "message": str(e)};
            uiMessage = str(e);
        }
    }

    return
        <div className={currentTheme == "dark" and "demo-shell theme-dark" or "demo-shell theme-light"}>
            <div className="demo-hero">
                <div className="demo-hero-copy">
                    <span className="version">Ringtail Dashboard</span>
                    <h1>Professional Optimization Studio</h1>
                    <p>Paste code for rapid optimization, run benchmark suites, and ship production-grade repository improvements from one polished Jac UI.</p>
                </div>
                <div className="hero-right">
                    <button className="secondary-button theme-toggle" onClick={lambda -> None { _toggle_theme(); }}>
                        {currentTheme == "dark" and "Switch to Light" or "Switch to Dark"}
                    </button>
                    {githubLogin == "" and
                        <button className="gh-login-button" onClick={lambda -> None { handleGithubLogin(); }}>
                            Sign in with GitHub
                        </button>
                    }
                    {githubLogin != "" and
                        <div className="gh-user-bar">
                            {githubAvatarUrl != "" and <img className="gh-avatar" src={githubAvatarUrl} alt="" />}
                            <span>{githubLogin}</span>
                            <button className="secondary-button gh-logout" onClick={lambda -> None { handleLogout(); }}>
                                Sign out
                            </button>
                        </div>
                    }
                    {_value(healthStatus, "status", "") == "healthy" and <div className="status-badge" role="status">Service Healthy</div>}
                </div>
            </div>

            <div className="tab-bar" role="tablist" aria-label="Dashboard views">
                <button id="tab-paste" role="tab" aria-selected={activeTab == "paste" and "true" or "false"} className={activeTab == "paste" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "paste"; }}>Paste Optimizer</button>
                <button id="tab-benchmark" role="tab" aria-selected={activeTab == "benchmark" and "true" or "false"} className={activeTab == "benchmark" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "benchmark"; }}>Benchmark Studio</button>
                <button id="tab-repo" role="tab" aria-selected={activeTab == "repo" and "true" or "false"} className={activeTab == "repo" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "repo"; if sessionToken != "" and installationId == 0 { loadInstallation(); }; }}>Optimize a Repo</button>
            </div>

            {uiMessage != "" and <div className="info-banner" role="status" aria-live="polite">{uiMessage}</div>}

            {activeTab == "paste" and
                <div className="container" role="tabpanel" aria-labelledby="tab-paste">
                    <div className="hero-card" role="region" aria-label="Paste optimizer form">
                        <h2>Paste Code To Optimize</h2>
                        <p className="hero-subtitle">Submit a single function with an optional test assertion to get measurable before/after runtime feedback.</p>
                        <form className="form-grid" onSubmit={lambda e: any -> None { submitPasteJob(e); }}>
                            <label className="field field-full">
                                <span>Source Code</span>
                                <textarea className="code-editor"
                                    rows={16}
                                    spellCheck={False}
                                    wrap="off"
                                    value={pasteSourceCode}
                                    onChange={lambda e: any -> None { pasteSourceCode = e.target.value; }}
                                    onPaste={lambda e: any -> None { handleSourceEditorPaste(e); }}
                                    onKeyDown={lambda e: any -> None { handleSourceEditorKeydown(e); }} />
                                <div className="field-help">Shortcuts: Tab indents, Shift+Tab unindents, Cmd/Ctrl+Enter submits. Pasted markdown fences and escaped newline blobs are cleaned automatically.</div>
                            </label>
                            <label className="field">
                                <span>Function Name</span>
                                <input value={pasteFunctionName} onChange={lambda e: any -> None { pasteFunctionName = e.target.value; }} />
                            </label>
                            <label className="field">
                                <span>Function Call</span>
                                <input value={pasteFunctionCall} onChange={lambda e: any -> None { pasteFunctionCall = e.target.value; }} />
                            </label>
                            <label className="field">
                                <span>Validation Call (optional)</span>
                                <input value={pasteTestCall} placeholder="slow_add(5)" onChange={lambda e: any -> None { pasteTestCall = e.target.value; _update_expected_feedback(); }} />
                            </label>
                            <label className="field">
                                <span>Expected Result (JSON literal, optional)</span>
                                <input value={pasteExpected} placeholder="10, string, true, null, [1,2]" onChange={lambda e: any -> None { pasteExpected = e.target.value; _update_expected_feedback(); }} />
                                <div className="editor-status">
                                    <span className={pasteExpectedStatus == "ok" and "validation-chip ok" or pasteExpectedStatus == "warn" and "validation-chip warn" or "validation-chip"}>
                                        {pasteExpectedStatus == "ok" and "Expected value parsed" or pasteExpectedStatus == "warn" and "Needs attention" or "Optional field"}
                                    </span>
                                    <span className="validation-chip">{pasteExpectedPreview}</span>
                                </div>
                            </label>
                            <label className="field">
                                <span>Config Profile</span>
                                <input value={pasteConfigName} onChange={lambda e: any -> None { pasteConfigName = e.target.value; }} />
                            </label>
                            <label className="field">
                                <span>Analysis Mode</span>
                                <select value={pasteAnalysisMode} onChange={lambda e: any -> None { pasteAnalysisMode = e.target.value; }}>
                                    <option value="llm">llm</option>
                                    <option value="heuristic">heuristic</option>
                                </select>
                            </label>
                            <label className="checkbox-field">
                                <input type="checkbox" checked={pasteEnableRunLog} onChange={lambda e: any -> None { pasteEnableRunLog = e.target.checked; }} />
                                <span>Enable run logs</span>
                            </label>
                            <div className="panel-actions field-full">
                                <button type="submit" className="primary-button" disabled={pasteSubmitting or pasteJobStatus in ["queued", "running", "submitting"]}>
                                    {pasteSubmitting and "Submitting..." or pasteJobStatus in ["queued", "running"] and "Job In Progress" or "Optimize Pasted Code"}
                                </button>
                                {pasteJobId != "" and <button type="button" className="secondary-button" disabled={pasteSubmitting} onClick={lambda -> None { pollPasteJob(); }}>Refresh Status</button>}
                            </div>
                        </form>
                    </div>

                    <div className="stat-grid">
                        <div className="stat-card">
                            <span>Job Status</span>
                            <strong>{pasteJobStatus != "" and pasteJobStatus or "idle"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Improvement Ratio</span>
                            <strong>{pasteImprovementRatio != "" and pasteImprovementRatio + "x" or "--"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Exec Time (Before -> After)</span>
                            <strong>{pasteExecutionBeforeMs != "" and pasteExecutionBeforeMs + " -> " + pasteExecutionAfterMs or "--"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Tests Passed</span>
                            <strong>{pasteTestPassed != "" and pasteTestPassed or "--"}</strong>
                        </div>
                    </div>

                    <div className="demo-layout">
                        <div className="section">
                            <h3>Job Details</h3>
                            <div className="simple-list">
                                {pasteJobId != "" and <div className="simple-list-item">Job ID: {pasteJobId}</div>}
                                {pasteTerminationReason != "" and <div className="simple-list-item">Termination: {pasteTerminationReason}</div>}
                                {pasteError != "" and <div className="simple-list-item">Error: {pasteError}</div>}
                            </div>
                        </div>
                        <div className="section">
                            <h3>Optimization Tips</h3>
                            <div className="simple-list">
                                <div className="simple-list-item">Keep function scope small for faster optimization cycles.</div>
                                <div className="simple-list-item">Use deterministic validation calls to avoid flaky runtime metrics.</div>
                                <div className="simple-list-item">Switch to benchmark mode for multi-target ranking and richer suite reporting.</div>
                            </div>
                        </div>
                    </div>

                    <div className="comparison-grid">
                        <div>
                            <h4>Original Code</h4>
                            <pre className="result-box">{pasteOriginalCode}</pre>
                        </div>
                        <div>
                            <h4>Optimized Code</h4>
                            <pre className="result-box">{pasteOptimizedCode}</pre>
                        </div>
                    </div>
                </div>
            }

            {activeTab == "repo" and
                <div className="container" role="tabpanel" aria-labelledby="tab-repo">
                    {githubLogin == "" and
                        <div className="hero-card" style={{"textAlign": "center", "padding": "3rem"}}>
                            <h2>Connect GitHub</h2>
                            <p className="hero-subtitle">Sign in with GitHub to optimize your repositories.</p>
                            <button className="gh-login-button" style={{"marginTop": "1.5rem"}} onClick={lambda -> None { handleGithubLogin(); }}>
                                Sign in with GitHub
                            </button>
                        </div>
                    }
                    {githubLogin != "" and installationId == 0 and
                        <div className="hero-card" style={{"textAlign": "center", "padding": "3rem"}}>
                            <h2>Install Ringtail on Your Repos</h2>
                            <p className="hero-subtitle">Ringtail needs access to push branches and open pull requests.</p>
                            <button className="primary-button" style={{"marginTop": "1.5rem"}} onClick={lambda -> None { handleInstallApp(); }}>
                                Install GitHub App
                            </button>
                        </div>
                    }
                    {githubLogin != "" and installationId != 0 and
                        <div className="demo-layout">
                            <div className="hero-card">
                                <h2>Optimize a Repository</h2>
                                <p className="hero-subtitle">Point Ringtail at a repo, describe what to optimize, and we'll open a PR with the results.</p>
                                <form className="form-grid" onSubmit={lambda e: any -> None { submitRepoJob(e); }}>
                                    <label className="field field-full">
                                        <span>Repository URL</span>
                                        <input value={repoUrl} placeholder="https://github.com/org/repo" onChange={lambda e: any -> None { repoUrl = e.target.value; }} />
                                    </label>
                                    <label className="field field-full">
                                        <span>Optimization Prompt</span>
                                        <textarea rows={4} value={repoPrompt} onChange={lambda e: any -> None { repoPrompt = e.target.value; }} />
                                    </label>
                                    <label className="field">
                                        <span>Test Command (optional)</span>
                                        <input value={repoTestCommand} placeholder="python -m pytest tests" onChange={lambda e: any -> None { repoTestCommand = e.target.value; }} />
                                    </label>
                                    <label className="checkbox-field">
                                        <input type="checkbox" checked={repoPublishPr} onChange={lambda e: any -> None { repoPublishPr = e.target.checked; }} />
                                        <span>Open a real PR</span>
                                    </label>
                                    <div className="panel-actions field-full">
                                        <button type="submit" className="primary-button">Submit Optimization Job</button>
                                    </div>
                                </form>
                            </div>
                            <div className="hero-card">
                                <h3>Connection Status</h3>
                                <div className="simple-list">
                                    <div className="simple-list-item">Signed in as {githubLogin}</div>
                                    <div className="simple-list-item">Installation ID: {str(installationId)}</div>
                                    {installAccountLogin != "" and <div className="simple-list-item">Account: {installAccountLogin}</div>}
                                </div>
                                {repoJobStatus != "" and
                                    <div style={{"marginTop": "1.5rem"}}>
                                        <h3>Job Status</h3>
                                        <div className="simple-list">
                                            <div className="simple-list-item">Job: {repoJobId}</div>
                                            <div className="simple-list-item">Status: {repoJobStatus}</div>
                                            {repoJobResult != "" and <div className="simple-list-item">{repoJobResult}</div>}
                                        </div>
                                    </div>
                                }
                            </div>
                        </div>
                    }
                </div>
            }

            {activeTab == "benchmark" and demoView == "setup" and
                <div className="container" role="tabpanel" aria-labelledby="tab-benchmark">
                    <div className="demo-layout">
                        <div className="hero-card">
                            <h2>Choose A Benchmark</h2>
                            <p className="hero-subtitle">Pick an engineer-designed benchmark suite, choose how many ranked targets to optimize, and run the demo.</p>
                            <form className="form-grid" onSubmit={lambda e: any -> None { startDemoRun(e); }}>
                                <label className="field field-full">
                                    <span>Benchmark</span>
                                    <select value={demoBenchmarkId} onChange={lambda e: any -> None { demoBenchmarkId = e.target.value; refreshBenchmarkContext(); }}>
                                        <option value="ranked-pitch-repo">Ranked Pitch Repo</option>
                                    </select>
                                </label>
                                <label className="field">
                                    <span>Top K Final Targets</span>
                                    <input type="number" min="1" step="1" value={demoTopK} onChange={lambda e: any -> None { demoTopK = e.target.value; }} />
                                </label>
                                <label className="field">
                                    <span>Per-File Finalists</span>
                                    <input type="number" min="1" step="1" value={demoPerFileK} onChange={lambda e: any -> None { demoPerFileK = e.target.value; }} />
                                </label>
                                <label className="field">
                                    <span>Latest Result Type</span>
                                    <select value={demoLatestBrowseKind} onChange={lambda e: any -> None { demoLatestBrowseKind = e.target.value; }}>
                                        <option value="any">Any</option>
                                        <option value="ranked_demo_suite">Ranked Demo Suite</option>
                                        <option value="file_optimize">File Optimize</option>
                                        <option value="replay_optimize">Replay Optimize</option>
                                        <option value="repo_agent">Repo Agent</option>
                                        <option value="async_job">Async Job</option>
                                        <option value="run">Run</option>
                                    </select>
                                </label>
                                <div className="panel-actions field-full">
                                    <button type="button" className="secondary-button" onClick={lambda -> None { loadLatestDemoSuite(); }}>
                                        View Latest Results
                                    </button>
                                    <button type="submit" className="primary-button">Run Benchmark</button>
                                </div>
                            </form>
                        </div>

                        <div className="hero-card">
                            <h3>Files In This Suite</h3>
                            <div className="simple-list">
                                {demoFile1Visible and <div className="simple-list-item">{demoFile1Text}</div>}
                                {demoFile2Visible and <div className="simple-list-item">{demoFile2Text}</div>}
                                {demoFile3Visible and <div className="simple-list-item">{demoFile3Text}</div>}
                                {demoFile4Visible and <div className="simple-list-item">{demoFile4Text}</div>}
                            </div>
                        </div>
                    </div>
                </div>
            }

            {activeTab == "benchmark" and demoView == "running" and
                <div className="container" role="tabpanel" aria-labelledby="tab-benchmark">
                    <div className="run-stage-card">
                        <div className="run-stage-copy">
                            <p className="eyebrow">Benchmark Running</p>
                            <h2>{demoRunStage}</h2>
                            <p>Status: {demoRunStatus}</p>
                        </div>
                        <div className="progress-meter">
                            <div className="progress-track" role="progressbar" aria-label="Benchmark progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow={str(demoProgressPct)}>
                                <div className="progress-fill" style={{"width": str(demoProgressPct) + "%"}}></div>
                            </div>
                            <span className="progress-label">{str(demoProgressPct)}%</span>
                        </div>
                    </div>

                    <div className="stage-grid">
                        <div className={demoProgressPct >= 10 and "stage-card active" or "stage-card"}>
                            <span>1</span>
                            <h3>Discover</h3>
                            <p>Scan benchmark files and gather candidate functions.</p>
                        </div>
                        <div className={demoProgressPct >= 30 and "stage-card active" or "stage-card"}>
                            <span>2</span>
                            <h3>Rank</h3>
                            <p>Pick strong per-file finalists, then choose final targets.</p>
                        </div>
                        <div className={demoProgressPct >= 55 and "stage-card active" or "stage-card"}>
                            <span>3</span>
                            <h3>Optimize</h3>
                            <p>Generate optimized candidates and validate behavior.</p>
                        </div>
                        <div className={demoProgressPct >= 90 and "stage-card active" or "stage-card"}>
                            <span>4</span>
                            <h3>Report</h3>
                            <p>Write graphs, summaries, and comparison artifacts.</p>
                        </div>
                    </div>

                    <div className="log-card">
                        <div className="log-card-header">
                            <h3>Live Activity</h3>
                            <button className="secondary-button" onClick={lambda -> None { pollDemoProgress(); }}>Refresh Now</button>
                        </div>
                        <pre className="log-feed" role="log" aria-live="polite">{demoLogText}</pre>
                    </div>
                </div>
            }

            {activeTab == "benchmark" and demoView == "results" and
                <div className="container" role="tabpanel" aria-labelledby="tab-benchmark">
                    <div className="results-header">
                        <div>
                            <p className="eyebrow">Benchmark Complete</p>
                            <h2>Selected Targets And Measured Speedups</h2>
                            <p>Ringtail picked the best benchmark targets, validated optimized candidates, and generated comparison graphs for the winners.</p>
                        </div>
                        <div className="panel-actions">
                            <button className="secondary-button" onClick={lambda -> None { resetToSetup(); }}>
                                Back To Setup
                            </button>
                            <button className="primary-button" onClick={lambda -> None { _start_demo_run(); }}>
                                Run Benchmark Again
                            </button>
                        </div>
                    </div>

                    <div className="stat-grid">
                        <div className="stat-card">
                            <span>Targets Passed</span>
                            <strong>{demoPassCount}/{demoTargetCount}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Average Speedup</span>
                            <strong>{demoAverageSpeedup}x</strong>
                        </div>
                        <div className="stat-card">
                            <span>Average Time Saved</span>
                            <strong>{demoAverageSaved}%</strong>
                        </div>
                    </div>

                    <div className="demo-layout">
                        <div className="section">
                            <h3>Selected Targets</h3>
                            <div className="simple-list">
                                {demoSelected1Visible and
                                    <div className="target-pill">
                                        <strong>{demoSelected1Title}</strong>
                                        <span>{demoSelected1Meta}</span>
                                    </div>
                                }
                                {demoSelected2Visible and
                                    <div className="target-pill">
                                        <strong>{demoSelected2Title}</strong>
                                        <span>{demoSelected2Meta}</span>
                                    </div>
                                }
                                {demoSelected3Visible and
                                    <div className="target-pill">
                                        <strong>{demoSelected3Title}</strong>
                                        <span>{demoSelected3Meta}</span>
                                    </div>
                                }
                            </div>
                        </div>
                        <div className="section">
                            <h3>Ranking Details</h3>
                            <div className="simple-list">
                                {demoFinalist1Visible and <div className="simple-list-item">{demoFinalist1Text}</div>}
                                {demoFinalist2Visible and <div className="simple-list-item">{demoFinalist2Text}</div>}
                                {demoFinalist3Visible and <div className="simple-list-item">{demoFinalist3Text}</div>}
                                {demoFinalist4Visible and <div className="simple-list-item">{demoFinalist4Text}</div>}
                            </div>
                        </div>
                    </div>

                    {demoOverviewSvg != "" and
                        <div className="section">
                            <h3>Suite Overview</h3>
                            <img className="suite-graph" src={"data:image/svg+xml;base64," + demoOverviewSvg} alt="Benchmark suite overview graph" />
                        </div>
                    }

                    <div className="suite-card-grid">
                        {demoCard1Visible and
                            <div className="suite-card">
                                <h3>#1 {demoCard1Title}</h3>
                                <p className="suite-meta">{demoCard1Meta}</p>
                                {demoCard1GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + demoCard1GraphSvg} alt={"Timing graph for " + demoCard1Title} />
                                }
                                <div className="comparison-grid">
                                    <div>
                                        <h4>Original</h4>
                                        <pre className="result-box">{demoCard1Original}</pre>
                                    </div>
                                    <div>
                                        <h4>Optimized</h4>
                                        <pre className="result-box">{demoCard1Optimized}</pre>
                                    </div>
                                </div>
                            </div>
                        }

                        {demoCard2Visible and
                            <div className="suite-card">
                                <h3>#2 {demoCard2Title}</h3>
                                <p className="suite-meta">{demoCard2Meta}</p>
                                {demoCard2GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + demoCard2GraphSvg} alt={"Timing graph for " + demoCard2Title} />
                                }
                                <div className="comparison-grid">
                                    <div>
                                        <h4>Original</h4>
                                        <pre className="result-box">{demoCard2Original}</pre>
                                    </div>
                                    <div>
                                        <h4>Optimized</h4>
                                        <pre className="result-box">{demoCard2Optimized}</pre>
                                    </div>
                                </div>
                            </div>
                        }

                        {demoCard3Visible and
                            <div className="suite-card">
                                <h3>#3 {demoCard3Title}</h3>
                                <p className="suite-meta">{demoCard3Meta}</p>
                                {demoCard3GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + demoCard3GraphSvg} alt={"Timing graph for " + demoCard3Title} />
                                }
                                <div className="comparison-grid">
                                    <div>
                                        <h4>Original</h4>
                                        <pre className="result-box">{demoCard3Original}</pre>
                                    </div>
                                    <div>
                                        <h4>Optimized</h4>
                                        <pre className="result-box">{demoCard3Optimized}</pre>
                                    </div>
                                </div>
                            </div>
                        }
                    </div>
                </div>
            }
        </div>
    ;
}

# Main entry point for direct execution (jac run)
with entry {
    print("Ringtail initialized");
    print("Ready to optimize code!");
}
