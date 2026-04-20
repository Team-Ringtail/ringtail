# Ringtail - AI Agent-Based Code Optimizer
# Main application entry point
#
# Public functions below become REST endpoints via `jac start main.jac`.
# Implementation lives in src/api/ modules; main.jac re-exports them so
# the Jac server exposes a flat endpoint namespace.

cl import "./styles.css";
cl import from "@codemirror/state" { * as cmState }
cl import from "@codemirror/view" { * as cmView }
cl import from "@codemirror/lang-python" { * as cmLangPython }
cl import from "@codemirror/commands" { * as cmCommands }
cl import from "@codemirror/language" { * as cmLanguage }
cl import from "@codemirror/autocomplete" { * as cmAutocomplete }
cl import from "@codemirror/search" { * as cmSearch }
cl import from "@codemirror/theme-one-dark" { * as cmOneDark }
import from typing { Any }

# --- Optimization -----------------------------------------------------------
import from src.api.optimization_requests {
    run_optimization_request,
    get_optimization_operation_contract
}

def:pub optimize_sync(payload: dict) -> dict | list {
    return run_optimization_request(payload);
}

def:pub get_optimization_contract -> dict {
    return get_optimization_operation_contract();
}

# --- Jobs --------------------------------------------------------------------
# jac-scale treats only entry-module `def:pub` as public HTTP routes; importing
# `def:pub` symbols from submodules without re-declaring them here leaves them
# JWT-protected (401 from the browser). Mirror the demo_api / diagnostics_api pattern.
import from src.api.jobs_api {
    submit_optimization_job as _jobs_submit_optimization_job,
    get_optimization_job as _jobs_get_optimization_job,
    cancel_optimization_job as _jobs_cancel_optimization_job,
    run_repo_agent_sync as _jobs_run_repo_agent_sync,
    submit_repo_agent_job as _jobs_submit_repo_agent_job,
    get_repo_agent_job as _jobs_get_repo_agent_job,
    get_recent_jobs as _jobs_get_recent_jobs,
    wait_job_notification as _jobs_wait_job_notification,
}

def:pub submit_optimization_job(payload: dict) -> dict {
    print("[RT-SERVER] submit_optimization_job called, payload type:", type(payload), "value:", str(payload)[:200]);
    return _jobs_submit_optimization_job(payload);
}

def:pub get_optimization_job(job_id: str) -> dict {
    return _jobs_get_optimization_job(job_id);
}

def:pub cancel_optimization_job(job_id: str) -> dict {
    return _jobs_cancel_optimization_job(job_id);
}

def:pub run_repo_agent_sync(payload: dict) -> dict {
    return _jobs_run_repo_agent_sync(payload);
}

def:pub submit_repo_agent_job(payload: dict) -> dict {
    print(
        "[RT-SERVER] submit_repo_agent_job called, repo_url:",
        str(payload.get("repo_url", ""))[:120],
        "publish_pr:",
        bool(payload.get("publish_pr", False)),
        "has_session_token:",
        str(payload.get("session_token", "")).strip() != "",
    );
    return _jobs_submit_repo_agent_job(payload);
}

def:pub get_repo_agent_job(job_id: str) -> dict {
    return _jobs_get_repo_agent_job(job_id);
}

def:pub get_recent_jobs(limit: int = 10) -> list {
    return _jobs_get_recent_jobs(limit);
}

def:pub wait_job_notification(
    job_id: str,
    since_seq: int = 0,
    timeout_s: float = 25.0
) -> dict {
    return _jobs_wait_job_notification(job_id, since_seq, timeout_s);
}

# --- GitHub ------------------------------------------------------------------
import from src.api.github_api {
    get_github_app_install_info as _gh_get_github_app_install_info,
    handle_github_app_install_callback as _gh_handle_github_app_install_callback,
    verify_github_repo_access as _gh_verify_github_repo_access,
    get_github_login_url as _gh_get_github_login_url,
    exchange_github_code as _gh_exchange_github_code,
    get_session as _gh_get_session,
    logout as _gh_logout,
    list_github_repos as _gh_list_github_repos,
    list_github_repos_by_token as _gh_list_github_repos_by_token,
    save_github_installation as _gh_save_github_installation
}

import from config.agent_config {
    list_agent_config_names as _cfg_list_agent_config_names
}

def:pub get_github_app_install_info(state: str = "") -> dict {
    return _gh_get_github_app_install_info(state);
}

def:pub handle_github_app_install_callback(
    installation_id: int,
    setup_action: str = "",
    state: str = ""
) -> dict {
    return _gh_handle_github_app_install_callback(
        installation_id,
        setup_action,
        state
    );
}

def:pub verify_github_repo_access(payload: dict) -> dict {
    return _gh_verify_github_repo_access(payload);
}

def:pub get_github_login_url(redirect_uri: str = "") -> dict {
    return _gh_get_github_login_url(redirect_uri);
}

def:pub exchange_github_code(code: str, state: str, redirect_uri: str = "") -> dict {
    return _gh_exchange_github_code(code, state, redirect_uri);
}

def:pub get_session(session_token: str) -> dict {
    return _gh_get_session(session_token);
}

def:pub logout(session_token: str) -> dict {
    return _gh_logout(session_token);
}

def:pub list_github_repos(session_token: str) -> dict {
    return _gh_list_github_repos(session_token);
}

def:pub list_github_repos_by_token(token: str) -> dict {
    return _gh_list_github_repos_by_token(token);
}

def:pub save_github_installation(
    session_token: str,
    installation_id: int,
    account_login: str = ""
) -> dict {
    return _gh_save_github_installation(
        session_token,
        installation_id,
        account_login
    );
}

def:pub list_agent_config_names -> list {
    return _cfg_list_agent_config_names();
}

# --- Diagnostics -------------------------------------------------------------
import from src.api.diagnostics_api {
    health as _diag_health,
    hello as _diag_hello,
    get_auth_readiness as _diag_get_auth_readiness,
    get_config_doctor as _diag_get_config_doctor,
    get_latest_run as _diag_get_latest_run,
    list_recent_runs as _diag_list_recent_runs,
    hydrate_run_entry as _diag_hydrate_run_entry
}

def:pub health -> dict {
    return _diag_health();
}

def:pub hello(name: str = "Ringtail") -> dict {
    return _diag_hello(name);
}

def:pub get_auth_readiness -> dict {
    return _diag_get_auth_readiness();
}

def:pub get_config_doctor -> dict {
    return _diag_get_config_doctor();
}

def:pub get_latest_run(kind: str = "any") -> dict {
    return _diag_get_latest_run(kind);
}

def:pub list_recent_runs(limit: int = 50, kind: str = "any", surface: str = "any", outcome: str = "any") -> dict {
    return _diag_list_recent_runs(limit, kind, surface, outcome);
}

def:pub hydrate_run_entry(run_entry: dict) -> dict {
    return _diag_hydrate_run_entry(run_entry);
}

# --- Demo / Benchmarks -------------------------------------------------------
import from src.api.demo_api {
    get_ranked_demo_suite_catalog as _demo_get_ranked_demo_suite_catalog,
    get_ranked_demo_benchmarks as _demo_get_ranked_demo_benchmarks,
    get_latest_ranked_demo_suite as _demo_get_latest_ranked_demo_suite,
    get_ranked_demo_job_progress as _demo_get_ranked_demo_job_progress
}

def:pub get_ranked_demo_suite_catalog(benchmark_id: str = "") -> dict {
    return _demo_get_ranked_demo_suite_catalog(benchmark_id);
}

def:pub get_ranked_demo_benchmarks -> dict {
    return _demo_get_ranked_demo_benchmarks();
}

def:pub get_latest_ranked_demo_suite -> dict {
    return _demo_get_latest_ranked_demo_suite();
}

def:pub get_ranked_demo_job_progress(job_id: str) -> dict {
    return _demo_get_ranked_demo_job_progress(job_id);
}

# --- Dashboard UI ------------------------------------------------------------
# Client HTTP: ringtail_* helpers POST to /function/<name>. Component must stay
# in this entry module so `jac start` registers `app` (submodules omit JSX in Python).

cl def:pub app -> JsxElement {
    has healthStatus: dict = {};
    has uiMessage: str = "";
    has activeTab: str = "home";
    has repoExperienceMode: str = "local";
    has currentTheme: str = "dark";
    has sessionToken: str = "";
    has githubLogin: str = "";
    has githubAvatarUrl: str = "";
    has githubUserId: int = 0;
    has installationId: int = 0;
    has installAccountLogin: str = "";
    has githubPatToken: str = "";
    has githubPatInput: str = "";
    has githubAuthMode: str = "none";
    has repoUrl: str = "";
    has availableRepos: list = [];
    has reposLoading: bool = False;
    has repoPrompt: str = "make this faster";
    has repoTestCommand: str = "";
    has repoEntryPoint: str = "";
    has repoBaseBranch: str = "";
    has repoSetupCommands: str = "";
    has repoPublishPr: bool = False;
    has repoJobId: str = "";
    has repoJobStatus: str = "";
    has repoJobResult: str = "";
    has repoSubmitting: bool = False;
    has repoCancelling: bool = False;
    has repoActivityText: list = ["Submit a repository job to stream worker status and PR publish events."];
    has repoRunLogPath: str = "";
    has repoRunId: str = "";
    has repoPullRequestUrl: str = "";
    has pasteSourceCode: str = "def slow_add(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n";
    has pasteFunctionName: str = "slow_add";
    has pasteFunctionCall: str = "slow_add(5000)";
    has pasteTestCall: str = "slow_add(5)";
    has pasteExpected: str = "10";
    has pasteConfigName: str = "live-fast";
    has pasteConfigProfiles: list = ["live-fast", "default"];
    has pasteAnalysisMode: str = "llm";
    has pasteEnableRunLog: bool = True;
    has pasteJobId: str = "";
    has pasteJobStatus: str = "";
    has pasteActivityText: list = ["Submit a job to stream live status and run-log events from the server."];
    has pasteRunLogPath: str = "";
    has pasteRunId: str = "";
    has pasteError: str = "";
    has pasteImprovementRatio: str = "";
    has pasteExecutionBeforeMs: str = "";
    has pasteExecutionAfterMs: str = "";
    has pasteTerminationReason: str = "";
    has pasteTestPassed: str = "";
    has pasteOriginalCode: str = "";
    has pasteOptimizedCode: str = "";
    has pasteSubmitting: bool = False;
    has pasteCancelling: bool = False;
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
    has demoLogText: list = ["Live run events will appear here."];
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
    has runHistoryPhase: str = "pick";
    has runHistorySurfaceFilter: str = "any";
    has runHistoryOutcomeFilter: str = "any";
    has runHistoryListFiltered: list = [];
    has runHistorySelectLabels: list = [];
    has runHistorySelectedIndex: int = 0;
    has runHistoryListFetchSeq: int = 0;
    has runHistoryDetailFetchSeq: int = 0;
    has runHistoryError: str = "";
    has runHistoryMetaLine: str = "";
    has runHistoryOriginSurface: str = "";
    has runHistoryOriginChannel: str = "";
    has runHistoryOverviewSvg: str = "";
    has runHistoryPassCount: str = "0";
    has runHistoryTargetCount: str = "0";
    has runHistoryAverageSpeedup: str = "0";
    has runHistoryAverageSaved: str = "0";
    has runHistorySelected1Visible: bool = False;
    has runHistorySelected1Title: str = "";
    has runHistorySelected1Meta: str = "";
    has runHistorySelected2Visible: bool = False;
    has runHistorySelected2Title: str = "";
    has runHistorySelected2Meta: str = "";
    has runHistorySelected3Visible: bool = False;
    has runHistorySelected3Title: str = "";
    has runHistorySelected3Meta: str = "";
    has runHistoryFinalist1Visible: bool = False;
    has runHistoryFinalist1Text: str = "";
    has runHistoryFinalist2Visible: bool = False;
    has runHistoryFinalist2Text: str = "";
    has runHistoryFinalist3Visible: bool = False;
    has runHistoryFinalist3Text: str = "";
    has runHistoryFinalist4Visible: bool = False;
    has runHistoryFinalist4Text: str = "";
    has runHistoryCard1Visible: bool = False;
    has runHistoryCard1Title: str = "";
    has runHistoryCard1Meta: str = "";
    has runHistoryCard1GraphSvg: str = "";
    has runHistoryCard1Original: str = "";
    has runHistoryCard1Optimized: str = "";
    has runHistoryCard2Visible: bool = False;
    has runHistoryCard2Title: str = "";
    has runHistoryCard2Meta: str = "";
    has runHistoryCard2GraphSvg: str = "";
    has runHistoryCard2Original: str = "";
    has runHistoryCard2Optimized: str = "";
    has runHistoryCard3Visible: bool = False;
    has runHistoryCard3Title: str = "";
    has runHistoryCard3Meta: str = "";
    has runHistoryCard3GraphSvg: str = "";
    has runHistoryCard3Original: str = "";
    has runHistoryCard3Optimized: str = "";
    # Coalesce duplicate refreshBenchmarkContext calls (e.g. React 18 Strict Mode
    # double-mount in dev) for the same benchmark_id within a short window.
    has benchmarkContextRefreshSig: str = "";
    has benchmarkContextRefreshAtMs: int = 0;
    has demoStreamSeq: int = 0;
    has demoStreamGen: int = 0;
    has repoNotifiedJobId: str = "";
    has pasteActivityVersion: int = 0;
    has demoActivityVersion: int = 0;
    has liveActivityTextById: dict = {
        "paste-live-activity-log": "Submit a job to stream live status and run-log events from the server.",
        "repo-live-activity-log": "Submit a repository job to stream worker status and PR publish events.",
        "demo-live-log-feed": "Live run events will appear here.",
        "run-history-log-feed": "Load a run to show structured log tail and job lines here.",
    };
    has liveActivityVersionById: dict = {
        "paste-live-activity-log": 0,
        "repo-live-activity-log": 0,
        "demo-live-log-feed": 0,
        "run-history-log-feed": 0,
    };
    has liveActivityEls: dict = {};
    has liveActivityDomSyncPending: dict = {};
    has pasteEditorHostEl: Any = None;
    has pasteEditorView: Any = None;
    has pasteEditorReady: bool = False;
    has pasteEditorSyncingFromState: bool = False;

    def _http_unwrap_response(raw: dict | list | str | int | float | bool | None) -> dict | list | str | int | float | bool | None {
        if raw is None {
            return {};
        }
        if globalThis.Array.isArray(raw) {
            return raw;
        }
        try {
            if "data" in raw {
                data = raw["data"];
                if data is not None
                    and (not globalThis.Array.isArray(data))
                    and ("result" in data) {
                    return data["result"];
                }
            }
        } except Exception {
            ignored = "";
        }
        return raw;
    }

    async def ringtail_post_function(name: str, body: dict) -> dict | list | str | int | float | bool | None {
        origin = str(globalThis.window.location.origin or "");
        url = origin + "/function/" + name;
        headers = {};
        headers["Content-Type"] = "application/json";
        init = {};
        init["method"] = "POST";
        init["headers"] = headers;
        body_str = "";
        try { body_str = globalThis.JSON.stringify(globalThis.JSON.parse(globalThis.JSON.stringify(body))); } except Exception { ignored = ""; }
        if body_str == "" or body_str == "null" {
            body_str = globalThis.JSON.stringify(body);
        }
        init["body"] = body_str;
        resp = await globalThis.fetch(url, init);
        text = await resp.text();
        parsed: dict | list | str | int | float | bool | None = None;
        parsed_js = None;
        try {
            parsed_js = globalThis.JSON.parse(text);
            parsed = parsed_js;
        } except Exception {
            return {"error": "invalid_json", "status": resp.status, "raw": text};
        }
        parsed_plain = parsed_js;
        if not resp.ok {
            detail = parsed_plain;
            try {
                if parsed_plain is not None
                    and (not globalThis.Array.isArray(parsed_plain))
                    and ("detail" in parsed_plain) {
                    detail = parsed_plain["detail"];
                }
            } except Exception {
                ignored = "";
            }
            return {"error": ("http_" + str(resp.status)), "message": str(detail)};
        }
        def _is_nullish(v: Any) -> bool {
            # Prefer direct None check; also treat literal JS null/undefined as nullish
            # (but do NOT treat objects that merely stringify oddly as nullish).
            if v is None {
                return True;
            }
            try {
                if globalThis.Object.is(v, globalThis.null) {
                    return True;
                }
            } except Exception { ignored = ""; }
            try {
                if globalThis.Object.is(v, globalThis.undefined) {
                    return True;
                }
            } except Exception { ignored = ""; }
            return False;
        }
        def _is_json_nullish(v: Any) -> bool {
            # Some Jac/JS proxy objects behave oddly for direct comparisons; use
            # JSON.stringify as a coarse "is this real data?" check.
            if v is None {
                return True;
            }
            try {
                sv = str(globalThis.JSON.stringify(v));
                return sv == "" or sv == "null" or sv == "undefined";
            } except Exception {
                return True;
            }
        }
        # The Jaseci HTTP layer can return multiple wrapper shapes. We want the
        # actual function result object:
        # - {"ok":true,"type":"response","data":{"result":<X>,"reports":[...]}}
        # - {"data":{"result":<X>}}
        # - {"result":<X>}
        # Fall back to the parsed object if no wrapper is present.
        def _safe_get(container: dict | list | str | int | float | bool | None, key: str) -> dict | list | str | int | float | bool | None {
            if container is None {
                return None;
            }
            if globalThis.Array.isArray(container) {
                return None;
            }
            try {
                v = container[key];
                if v is None {
                    return None;
                }
                sv = str(v);
                if sv == "undefined" or sv == "null" {
                    return None;
                }
                return v;
            } except Exception {
                ignored = "";
            }
            return None;
        }
        unwrapped = parsed_plain;
        # Prefer direct indexing for parsed.data.result (this has proven reliable
        # in earlier runs), but guard against JS undefined/null.
        d0 = _safe_get(parsed_plain, "data");
        r0 = None;
        r0_direct = None;
        r0_direct_ok = False;
        try { r0_direct = parsed_plain["data"]["result"]; r0_direct_ok = True; } except Exception { r0_direct = None; r0_direct_ok = False; }
        r0_direct_json = "";
        try { r0_direct_json = str(globalThis.JSON.stringify(r0_direct)); } except Exception { r0_direct_json = ""; }
        r0_source = "none";
        if r0_direct_json != "" and r0_direct_json != "null" and r0_direct_json != "undefined" {
            r0 = r0_direct; 
            r0_source = "direct";
        } elif d0 is not None and (not globalThis.Array.isArray(d0)) {
            r0 = _safe_get(d0, "result");
            if r0 is not None { r0_source = "safe"; }
        }
        top_r = _safe_get(parsed_plain, "result");
        reports0 = None;
        reports0_len = -1;
        reports0_r = None;
        reports0_dr = None;
        if d0 is not None and (not globalThis.Array.isArray(d0)) {
            try { reports0 = d0["reports"]; } except Exception { reports0 = None; }
            try { reports0_len = int(reports0.length); } except Exception { reports0_len = -1; }
            if reports0_len > 0 {
                try { reports0_r = reports0[0]["result"]; } except Exception { reports0_r = None; }
                try { reports0_dr = reports0[0]["data"]["result"]; } except Exception { reports0_dr = None; }
            }
        }
        # Prefer parsed.data.result when present.
        if r0 is not None {
            unwrapped = r0;
        } elif top_r is not None {
            unwrapped = top_r;
        } elif not _is_json_nullish(reports0_dr) {
            # Some responses carry the true result only in reports[0].data.result
            unwrapped = reports0_dr;
        } else {
            # Last resort: return the full parsed envelope rather than `null`
            # so downstream code can still recover.
            unwrapped = parsed;
        }
        # Normalize potentially-proxied objects into plain JSON.
        # IMPORTANT: We have runtime evidence that JSON.stringify(unwrapped) can
        # collapse to "null" even when JSON.stringify(parsed.data.result) is fine.
        # If we selected the direct path, use the already-good JSON string.
        try {
            if r0_source == "direct"
                and r0_direct_json != ""
                and r0_direct_json != "null"
                and r0_direct_json != "undefined" {
                unwrapped = globalThis.JSON.parse(r0_direct_json);
            } else {
                s_unwrapped = globalThis.JSON.stringify(unwrapped);
                if str(s_unwrapped) != "" and str(s_unwrapped) != "null" and str(s_unwrapped) != "undefined" {
                    unwrapped = globalThis.JSON.parse(s_unwrapped);
                }
            }
        } except Exception {
            ignored = "";
        }
        return unwrapped;
    }

    async def ringtail_health -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("health", {});
    }

    async def ringtail_submit_optimization_job(request_json: str) -> dict | list | str | int | float | bool | None {
        if str(request_json).strip() == "" {
            return {"error": "empty_request_payload"};
        }
        request_obj = {};
        try {
            request_obj = globalThis.JSON.parse(request_json);
        } except Exception as parseErr {
            return {"error": "invalid_request_payload", "message": str(parseErr)};
        }
        return await ringtail_post_function("submit_optimization_job", {"payload": request_obj});
    }

    async def ringtail_get_optimization_job(job_id: str) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_optimization_job", {"job_id": job_id});
    }

    async def ringtail_cancel_optimization_job(job_id: str) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("cancel_optimization_job", {"job_id": job_id});
    }

    async def ringtail_submit_repo_agent_job(request_json: str) -> dict | list | str | int | float | bool | None {
        if str(request_json).strip() == "" {
            return {"error": "empty_request_payload"};
        }
        request_obj = {};
        try {
            request_obj = globalThis.JSON.parse(request_json);
        } except Exception as parseErr {
            return {"error": "invalid_request_payload", "message": str(parseErr)};
        }
        return await ringtail_post_function("submit_repo_agent_job", {"payload": request_obj});
    }

    async def ringtail_get_repo_agent_job(job_id: str) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_repo_agent_job", {"job_id": job_id});
    }

    async def ringtail_get_github_login_url(redirect_uri: str = "") -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_github_login_url", {"redirect_uri": redirect_uri});
    }

    async def ringtail_exchange_github_code(
        code: str,
        state: str,
        redirect_uri: str = ""
    ) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function(
            "exchange_github_code",
            {"code": code, "state": state, "redirect_uri": redirect_uri}
        );
    }

    async def ringtail_get_session(session_token: str) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_session", {"session_token": session_token});
    }

    async def ringtail_logout(session_token: str) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("logout", {"session_token": session_token});
    }

    async def ringtail_list_github_repos(session_token: str = "", token: str = "") -> dict | list | str | int | float | bool | None {
        if token != "" {
            return await ringtail_post_function("list_github_repos_by_token", {"token": token});
        }
        return await ringtail_post_function("list_github_repos", {"session_token": session_token});
    }

    async def ringtail_save_github_installation(
        session_token: str,
        installation_id: int,
        account_login: str = ""
    ) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function(
            "save_github_installation",
            {
                "session_token": session_token,
                "installation_id": installation_id,
                "account_login": account_login
            }
        );
    }

    async def ringtail_list_agent_config_names -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("list_agent_config_names", {});
    }

    async def ringtail_get_github_app_install_info(state: str = "") -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_github_app_install_info", {"state": state});
    }

    async def ringtail_get_ranked_demo_benchmarks -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_ranked_demo_benchmarks", {});
    }

    async def ringtail_get_ranked_demo_suite_catalog(benchmark_id: str = "") -> dict | list | str | int | float | bool | None {
        if str(benchmark_id).strip() == "" {
            return await ringtail_post_function("get_ranked_demo_suite_catalog", {});
        }
        return await ringtail_post_function(
            "get_ranked_demo_suite_catalog",
            {"benchmark_id": benchmark_id}
        );
    }

    async def ringtail_get_latest_ranked_demo_suite -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_latest_ranked_demo_suite", {});
    }

    async def ringtail_get_ranked_demo_job_progress(job_id: str) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_ranked_demo_job_progress", {"job_id": job_id});
    }

    async def ringtail_get_latest_run(kind: str = "any") -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("get_latest_run", {"kind": kind});
    }

    async def ringtail_list_recent_runs(
        limit: int = 200,
        kind: str = "any",
        surface: str = "any",
        outcome: str = "any"
    ) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function(
            "list_recent_runs",
            {"limit": limit, "kind": kind, "surface": surface, "outcome": outcome}
        );
    }

    async def ringtail_hydrate_run_entry(run_entry: dict) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function("hydrate_run_entry", {"run_entry": run_entry});
    }

    async def ringtail_wait_job_notification(
        job_id: str,
        since_seq: int,
        timeout_s: float
    ) -> dict | list | str | int | float | bool | None {
        return await ringtail_post_function(
            "wait_job_notification",
            {"job_id": job_id, "since_seq": since_seq, "timeout_s": timeout_s}
        );
    }

    def _value(
        data: dict | list | str | int | float | bool | None,
        key: str,
        fallback: dict | list | str | int | float | bool | None
    ) -> dict | list | str | int | float | bool | None {
        if data is None {
            return fallback;
        }
        if globalThis.Array.isArray(data) {
            return fallback;
        }
        try {
            # Use Reflect.get to avoid proxy/indexing quirks.
            v = globalThis.Reflect.get(data, key);
            if v is None {
                return fallback;
            }
            sv = str(v);
            if sv == "null" or sv == "undefined" {
                return fallback;
            }
            return v;
        } except Exception {
            ignored = "";
        }
        return fallback;
    }

    def _coerce_list(value: dict | list | str | int | float | bool | None) {
        if globalThis.Array.isArray(value) {
            return value;
        }
        return [];
    }

    def _coerce_plain_object(value: dict | list | str | int | float | bool | None) {
        if value is None {
            return {};
        }
        if globalThis.Array.isArray(value) {
            return {};
        }
        return value;
    }

    def _lower_text(value: dict | list | str | int | float | bool | None) -> str {
        try {
            return str(globalThis.String(value or "").toLowerCase()).strip();
        } except Exception {
            ignored = "";
        }
        return str(value).strip();
    }

    def _flatten_function_job_payload(raw: dict | list | str | int | float | bool | None) -> dict {
        # Peel nested {data:{result:...}} / {result:...} envelopes without relying
        # on `is not None` checks (which can compile inconsistently in some runtimes).
        cur = _coerce_plain_object(raw);
        try { cur = globalThis.JSON.parse(globalThis.JSON.stringify(cur)); } except Exception { ignored = ""; }
        peel = 0;
        while peel < 8 {
            if str(_value(cur, "job_id", "")).strip() != "" {
                return cur;
            }
            from_data = _coerce_plain_object(_value(_coerce_plain_object(_value(cur, "data", {})), "result", {}));
            if str(_value(from_data, "job_id", "")).strip() != "" {
                return from_data;
            }
            from_top = _coerce_plain_object(_value(cur, "result", {}));
            if str(_value(from_top, "job_id", "")).strip() != "" {
                return from_top;
            }
            next_candidate = {};
            if str(globalThis.JSON.stringify(from_data)) != "{}" {
                next_candidate = from_data;
            } elif str(globalThis.JSON.stringify(from_top)) != "{}" {
                next_candidate = from_top;
            } else {
                return cur;
            }
            cur = _coerce_plain_object(next_candidate);
            try { cur = globalThis.JSON.parse(globalThis.JSON.stringify(cur)); } except Exception { ignored = ""; }
            peel = peel + 1;
        }
        return cur;
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
        if theme != "light" and theme != "dark" {
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
            if saved == "light" or saved == "dark" {
                theme = saved;
            }
        } except Exception as err {
            ignored = str(err);
        }
        return theme;
    }

    def _save_pat_session(token: str) -> None {
        try {
            globalThis.sessionStorage.setItem("ringtail_github_pat", token);
        } except Exception as err {
            ignored = str(err);
        }
    }

    def _load_pat_session() -> str {
        try {
            return str(globalThis.sessionStorage.getItem("ringtail_github_pat") or "");
        } except Exception as err {
            ignored = str(err);
            return "";
        }
    }

    def _clear_pat_session() -> None {
        try {
            globalThis.sessionStorage.removeItem("ringtail_github_pat");
        } except Exception as err {
            ignored = str(err);
        }
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
        # Some payloads stringify newlines; normalize for <pre> display.
        norm: list = [];
        for ln in lines {
            txt = str(ln);
            # Handle different escaping levels emitted by worker/log bridges.
            txt = txt.replace("\\r\\n", "\n");
            txt = txt.replace("\\\\n", "\n");
            txt = txt.replace("\\n", "\n");
            txt = txt.replace("\\\\t", "    ");
            txt = txt.replace("\\t", "    ");
            norm.append(txt);
        }
        out = "\n".join(norm);
        return out;
    }

    def _run_history_row_label(row: dict) -> str {
        surf = str(_value(row, "ui_surface", ""));
        ch = str(_value(row, "submission_channel", ""));
        if surf == "" {
            surf = "—";
        }
        if ch == "" {
            ch = "—";
        }
        kind = str(_value(row, "kind", ""));
        st = str(_value(row, "status", ""));
        jid = str(_value(row, "job_id", ""));
        rid = str(_value(row, "run_id", ""));
        fin = str(_value(row, "finished_at", _value(row, "submitted_at", "")));
        tail = jid != "" and jid or rid;
        return fin + " · surface=" + surf + " · channel=" + ch + " · kind=" + kind + " · " + st + " · " + tail;
    }

    def _clear_run_history_layout() -> None {
        runHistoryOverviewSvg = "";
        runHistoryPassCount = "0";
        runHistoryTargetCount = "0";
        runHistoryAverageSpeedup = "0";
        runHistoryAverageSaved = "0";
        runHistoryMetaLine = "";
        runHistoryOriginSurface = "";
        runHistoryOriginChannel = "";
        runHistorySelected1Visible = False;
        runHistorySelected2Visible = False;
        runHistorySelected3Visible = False;
        runHistoryFinalist1Visible = False;
        runHistoryFinalist2Visible = False;
        runHistoryFinalist3Visible = False;
        runHistoryFinalist4Visible = False;
        runHistoryCard1Visible = False;
        runHistoryCard2Visible = False;
        runHistoryCard3Visible = False;
    }

    def _set_run_history_card(slot: int, row: dict) -> None {
        title = str(_value(row, "name", ""));
        meta = "speedup " + str(_value(row, "improvement_ratio", 0.0)) + "x | time saved "
            + str(_value(row, "time_saved_pct", 0.0)) + "% | ranked "
            + str(_value(row, "median_ms_ranked", 0.0)) + " ms";
        graphSvg = str(_value(row, "graph_svg_base64", ""));
        originalCode = str(_value(row, "original_code", ""));
        optimizedCode = str(_value(row, "optimized_code", ""));
        if slot == 1 {
            runHistoryCard1Visible = True;
            runHistoryCard1Title = title;
            runHistoryCard1Meta = meta;
            runHistoryCard1GraphSvg = graphSvg;
            runHistoryCard1Original = originalCode;
            runHistoryCard1Optimized = optimizedCode;
        }
        if slot == 2 {
            runHistoryCard2Visible = True;
            runHistoryCard2Title = title;
            runHistoryCard2Meta = meta;
            runHistoryCard2GraphSvg = graphSvg;
            runHistoryCard2Original = originalCode;
            runHistoryCard2Optimized = optimizedCode;
        }
        if slot == 3 {
            runHistoryCard3Visible = True;
            runHistoryCard3Title = title;
            runHistoryCard3Meta = meta;
            runHistoryCard3GraphSvg = graphSvg;
            runHistoryCard3Original = originalCode;
            runHistoryCard3Optimized = optimizedCode;
        }
    }

    def _set_run_history_target_slot(slot: int, item: dict) -> None {
        title = str(_value(item, "function_name", ""));
        fileName = _basename(str(_value(item, "source_file", "")));
        meta = fileName + " | ranked " + str(_value(item, "median_ms", 0.0)) + " ms";
        if slot == 1 {
            runHistorySelected1Visible = True;
            runHistorySelected1Title = title;
            runHistorySelected1Meta = meta;
        }
        if slot == 2 {
            runHistorySelected2Visible = True;
            runHistorySelected2Title = title;
            runHistorySelected2Meta = meta;
        }
        if slot == 3 {
            runHistorySelected3Visible = True;
            runHistorySelected3Title = title;
            runHistorySelected3Meta = meta;
        }
    }

    def _set_run_history_finalist_slot(slot: int, item: dict) -> None {
        text = str(_value(item, "function_name", "")) + " | " + _basename(str(_value(item, "source_file", "")))
            + " | ranked " + str(_value(item, "median_ms", 0.0)) + " ms";
        if slot == 1 {
            runHistoryFinalist1Visible = True;
            runHistoryFinalist1Text = text;
        }
        if slot == 2 {
            runHistoryFinalist2Visible = True;
            runHistoryFinalist2Text = text;
        }
        if slot == 3 {
            runHistoryFinalist3Visible = True;
            runHistoryFinalist3Text = text;
        }
        if slot == 4 {
            runHistoryFinalist4Visible = True;
            runHistoryFinalist4Text = text;
        }
    }

    def _apply_run_history_display(rd: dict) -> None {
        meta = _coerce_plain_object(_value(rd, "meta", {}));
        runHistoryOriginSurface = str(_value(meta, "ui_surface", ""));
        runHistoryOriginChannel = str(_value(meta, "submission_channel", ""));
        runHistoryMetaLine = "Job " + str(_value(meta, "job_id", "")) + " · run " + str(_value(meta, "run_id", ""))
            + " · kind " + str(_value(meta, "kind", "")) + " · status " + str(_value(meta, "status", ""));
        runHistoryOverviewSvg = str(_value(rd, "overview_svg_base64", ""));
        runHistoryPassCount = str(_value(rd, "pass_count", 0));
        runHistoryTargetCount = str(_value(rd, "target_count", 0));
        runHistoryAverageSpeedup = str(_value(rd, "average_speedup", 0.0));
        runHistoryAverageSaved = str(_value(rd, "average_time_saved_pct", 0.0));
        rows = _coerce_list(_value(rd, "results", []));
        selectedTargets = _coerce_list(_value(rd, "final_ranked_targets", []));
        finalists = _coerce_list(_value(rd, "per_file_finalists", []));
        runHistorySelected1Visible = False;
        runHistorySelected2Visible = False;
        runHistorySelected3Visible = False;
        runHistoryFinalist1Visible = False;
        runHistoryFinalist2Visible = False;
        runHistoryFinalist3Visible = False;
        runHistoryFinalist4Visible = False;
        runHistoryCard1Visible = False;
        runHistoryCard2Visible = False;
        runHistoryCard3Visible = False;
        ti = 0;
        while ti < len(selectedTargets) and ti < 3 {
            _set_run_history_target_slot(ti + 1, _coerce_plain_object(selectedTargets[ti]));
            ti = ti + 1;
        }
        fi = 0;
        while fi < len(finalists) and fi < 4 {
            _set_run_history_finalist_slot(fi + 1, _coerce_plain_object(finalists[fi]));
            fi = fi + 1;
        }
        ri = 0;
        while ri < len(rows) and ri < 3 {
            _set_run_history_card(ri + 1, _coerce_plain_object(rows[ri]));
            ri = ri + 1;
        }
    }

    def renderRunHistorySelectOptions() -> list {
        opts = [];
        labels = runHistorySelectLabels;
        i = 0;
        while i < len(labels) {
            lab = str(labels[i]);
            val = str(i);
            opts.append(<option key={val} value={val}>{lab}</option>);
            i = i + 1;
        }
        return opts;
    }

    async def refreshRunHistoryList() -> None {
        runHistoryListFetchSeq = runHistoryListFetchSeq + 1;
        fetch_id = runHistoryListFetchSeq;
        surface_arg = runHistorySurfaceFilter;
        outcome_arg = runHistoryOutcomeFilter;
        runHistoryError = "";
        resp = await ringtail_list_recent_runs(200, "any", surface_arg, outcome_arg);
        if fetch_id != runHistoryListFetchSeq {
            return;
        }
        if not bool(_value(resp, "success", False)) {
            runHistoryError = str(_value(resp, "error", "Could not list runs"));
            runHistoryListFiltered = [];
            runHistorySelectLabels = [];
            return;
        }
        runs = _coerce_list(_value(resp, "runs", []));
        runHistoryListFiltered = runs;
        labels = [];
        ri = 0;
        while ri < len(runs) {
            row = runs[ri];
            labels.append(_run_history_row_label(_coerce_plain_object(row)));
            ri = ri + 1;
        }
        runHistorySelectLabels = labels;
        runHistorySelectedIndex = 0;
    }

    async def openRunHistoryTab() -> None {
        activeTab = "run_history";
        runHistoryPhase = "pick";
        await refreshRunHistoryList();
    }

    def runHistoryBackToPick() -> None {
        runHistoryPhase = "pick";
        _clear_run_history_layout();
        _set_live_activity("run-history-log-feed", "Load a run to show structured log tail and job lines here.", True);
    }

    async def loadRunHistoryDetail() -> None {
        runs = runHistoryListFiltered;
        if len(runs) == 0 {
            runHistoryError = "No runs loaded. Refresh the list or widen filters.";
            return;
        }
        if runHistorySelectedIndex < 0 or runHistorySelectedIndex >= len(runs) {
            runHistorySelectedIndex = 0;
        }
        runHistoryDetailFetchSeq = runHistoryDetailFetchSeq + 1;
        detail_fetch_id = runHistoryDetailFetchSeq;
        row_raw = runs[runHistorySelectedIndex];
        entry = _coerce_plain_object(row_raw);
        resp = await ringtail_hydrate_run_entry(entry);
        if detail_fetch_id != runHistoryDetailFetchSeq {
            return;
        }
        if not bool(_value(resp, "success", False)) {
            runHistoryError = str(_value(resp, "error", "Could not load run details"));
            return;
        }
        lines = _coerce_list(_value(resp, "activity_log_lines", []));
        txt = _format_log_text(lines);
        _set_live_activity("run-history-log-feed", txt, True);
        rd = _coerce_plain_object(_value(resp, "run_display", {}));
        _apply_run_history_display(rd);
        runHistoryPhase = "detail";
        runHistoryError = "";
        flush_log_id = runHistoryDetailFetchSeq;
        globalThis.setTimeout(lambda -> None {
            if flush_log_id != runHistoryDetailFetchSeq {
                return;
            }
            late = _live_activity_text("run-history-log-feed", txt);
            _sync_live_activity_dom("run-history-log-feed", late);
        }, 0);
    }

    # def liveActivityBox(
    #     title: str,
    #     help_text: str,
    #     pre_id: str,
    #     body_text: str,
    #     update_version: int = 0,
    #     refresh_label: str = "Refresh Now",
    #     on_refresh: Any = None,
    #     header_right: Any = None,
    # ) -> Any {
    #     safe_title = str(title);
    #     safe_help_text = str(help_text);
    #     safe_pre_id = str(pre_id);
    #     safe_body_text = str(body_text);
    #     if safe_body_text == "" or safe_body_text == "undefined" or safe_body_text == "null" {
    #         safe_body_text = "Live run events will appear here.";
    #     }
    #     safe_update_version = 0;
    #     try {
    #         uv = str(update_version);
    #         if uv != "" and uv != "undefined" and uv != "null" {
    #             safe_update_version = int(update_version);
    #         }
    #     } except Exception {
    #         safe_update_version = 0;
    #     }
    #     has_on_refresh = False;
    #     has_header_right = False;
    #     try { has_on_refresh = on_refresh is not None and str(on_refresh) != "undefined" and str(on_refresh) != "null"; } except Exception { has_on_refresh = False; }
    #     try { has_header_right = header_right is not None and str(header_right) != "undefined" and str(header_right) != "null"; } except Exception { has_header_right = False; }

    #     return <div className="log-card">
    #         <div className="log-card-header">
    #             <div>
    #                 <h3>{safe_title}</h3>
    #                 {safe_help_text != "" and <p className="field-help">{safe_help_text}</p>}
    #             </div>
    #             {has_header_right and header_right}
    #             {has_on_refresh and
    #                 <button className="secondary-button" onClick={lambda -> None { on_refresh(); }}>
    #                     {refresh_label}
    #                 </button>
    #             }
    #         </div>
    #         <pre
    #             key={safe_pre_id}
    #             id={safe_pre_id}
    #             data-live-id={safe_pre_id}
    #             data-activity-version={str(safe_update_version)}
    #             className="log-feed"
    #             role="log"
    #             aria-live="polite"
    #             style={{"whiteSpace": "pre-wrap", "wordBreak": "break-word"}} 
    #             ref={lambda el -> None {
    #                 try {
    #                     # Register the in-document node; clear on unmount so we never
    #                     # hold a detached element (version-based keys used to remount
    #                     # and stale the cache).
    #                     # Some Jac client runtimes may pass JS `undefined` instead of null.
    #                     try {
    #                         if el is not None and globalThis.Object.is(el, globalThis.undefined) {
    #                             el = None;
    #                         }
    #                     } except Exception { ignored = ""; }
    #                     if el != None {
    #                         liveActivityEls[safe_pre_id] = el;
    #                         # If live activity was updated before this <pre> mounted,
    #                         # catch up immediately by writing the latest cached text.
    #                         # This avoids timing where _sync_live_activity_dom runs
    #                         # while the tab is not rendered, yielding undefined/null.
    #                         try {
    #                             latest_txt = _live_activity_text(safe_pre_id, "");
    #                             if latest_txt != "" {
    #                                 # Replace the textContent assignment with this:
    #                                 clean_txt = str(latest_txt).replace("\\r\\n", "\n").replace("\\\\n", "\n").replace("\\n", "\n");
    #                                 el.textContent = clean_txt;
    #                                 el.scrollTop = el.scrollHeight;
    #                             }
    #                         } except Exception { ignored = ""; }
    #                     } else {
    #                         try {
    #                             globalThis.Reflect.deleteProperty(liveActivityEls, safe_pre_id);
    #                         } except Exception { ignored = ""; }
    #                     }
    #                 } except Exception { ignored = ""; }
    #             }}
    #         >{safe_body_text}</pre>
    #     </div>;
    # }

    # Imperative DOM sync is centralized via reusable activity helpers.

    def _format_error_display(val: dict | list | str | int | float | bool | None) -> str {
        if val is None {
            return "";
        }
        s = str(val).strip();
        if s == "" or s == "None" or s == "null" {
            return "";
        }
        return s;
    }

    def _format_ratio_display(raw: str) -> str {
        txt = str(raw).strip();
        if txt == "" {
            return "";
        }
        try {
            v = float(txt);
            if v >= 1000.0 {
                return str(round(v, 2));
            }
            if v >= 10.0 {
                return str(round(v, 3));
            }
            return str(round(v, 4));
        } except Exception {
            return txt;
        }
    }

    def _format_exec_time_display(raw: str) -> str {
        txt = str(raw).strip();
        if txt == "" {
            return "";
        }
        try {
            sec = float(txt);
            abs_sec = sec >= 0.0 and sec or -sec;
            if abs_sec >= 1.0 {
                return str(round(sec, 3)) + " s";
            }
            if abs_sec >= 0.001 {
                return str(round(sec * 1000.0, 3)) + " ms";
            }
            if abs_sec >= 0.000001 {
                return str(round(sec * 1000000.0, 3)) + " us";
            }
            return str(round(sec * 1000000000.0, 3)) + " ns";
        } except Exception {
            return txt;
        }
    }

    def _scroll_element_to_bottom(element_id: str) -> None {
        try {
            el = globalThis.document.getElementById(element_id);
            # In some Jac client runtimes, missing elements can come back as JS `undefined`
            # rather than `null`. Treat both as "no element".
            try {
                if el is not None and globalThis.Object.is(el, globalThis.undefined) {
                    el = None;
                }
            } except Exception { ignored = ""; }
        } except Exception {
            ignored = "";
        }
    }

    def _sync_live_activity_dom(element_id: str, text: str) -> None {
        # Target the live in-document node: id is stable; getElementById avoids a
        # stale liveActivityEls entry pointing at a detached <pre> after remounts.
        # Do not gate the liveActivityEls fallback on isConnected — some Jac/JS
        # bridges misreport it and updates would never paint (see prior fix thread).
        try {
            el = None;
            try {
                el = globalThis.document.getElementById(element_id);
            } except Exception {
                el = None;
            }
            if el is None {
                el = _value(liveActivityEls, element_id, None);
            }
            try {
                if el is not None and globalThis.Object.is(el, globalThis.undefined) {
                    el = None;
                }
            } except Exception { ignored = ""; }
            if el is None {
                already = False;
                try { already = bool(_value(liveActivityDomSyncPending, element_id, False)); } except Exception { already = False; }
                if not already {
                    liveActivityDomSyncPending[element_id] = True;
                    globalThis.setTimeout(lambda -> None {
                        try { globalThis.Reflect.deleteProperty(liveActivityDomSyncPending, element_id); } except Exception { ignored = ""; }
                        fresh = _live_activity_text(element_id, text);
                        _sync_live_activity_dom(element_id, fresh);
                    }, 25);
                }
                return;
            }
            connected = True;
            try {
                if el != None {
                    connected = bool(el.isConnected);
                }
            } except Exception {
                connected = True;
            }
            if el is None or not connected {
                try {
                    el = globalThis.document.getElementById(element_id);
                } except Exception {
                    el = None;
                }
            }
            try {
                is_conn = False;
                try { is_conn = bool(el != None and bool(el.isConnected)); } except Exception { is_conn = False; }
                try {
                    if el is not None and globalThis.Object.is(el, globalThis.undefined) {
                        el = None;
                    }
                } except Exception { ignored = ""; }
                if el != None {
                    clean_txt = str(text).replace("\\r\\n", "\n").replace("\\\\n", "\n").replace("\\n", "\n");
                    lines = clean_txt.split("\n");
                    el.innerHTML = "";
                    for ln in lines {
                        d = globalThis.document.createElement("div");
                        d.className = "log-line";
                        d.textContent = str(ln);
                        el.appendChild(d);
                    }
                    liveActivityEls[element_id] = el;
                }
            } except Exception {
                ignored = "";
            }
        } except Exception {
            ignored = "";
        }
    }

    def _live_activity_text(target_id: str, fallback: str = "Live run events will appear here.") -> str {
        try {
            txt = _value(liveActivityTextById, target_id, fallback);
            return str(txt);
        } except Exception {
            ignored = "";
        }
        return fallback;
    }

    def _live_activity_version(target_id: str) -> int {
        try {
            return int(_value(liveActivityVersionById, target_id, 0));
        } except Exception {
            ignored = "";
        }
        return 0;
    }

    def _set_live_activity(target_id: str, text: str, bump_version: bool = True) -> None {
        try {
            liveActivityTextById[target_id] = text;
        } except Exception {
            ignored = "";
        }
        _sync_live_activity_dom(target_id, text);
        try {
            scroll_id = target_id;
            globalThis.setTimeout(lambda -> None {
                try {
                    sel = globalThis.document.getElementById(scroll_id);
                    if sel is not None {
                        sel.scrollTop = sel.scrollHeight;
                    }
                } except Exception { ignored = ""; }
            }, 50);
        } except Exception {
            ignored = "";
        }
    }

    def _activity_text_from_payload(payload: dict, default_status: str = "running") -> str {
        act_lines = [];
        raw_lines = _value(payload, "activity_log_lines", []);
        if globalThis.Array.isArray(raw_lines) {
            for ln in raw_lines {
                act_lines.append(str(ln));
            }
        } else {
            raw_obj = _coerce_plain_object(raw_lines);
            guessed_len = int(_value(raw_obj, "length", -1));
            if guessed_len > 0 {
                idx = 0;
                while idx < guessed_len {
                    txt = str(_value(raw_obj, str(idx), ""));
                    if txt != "" {
                        act_lines.append(txt);
                    }
                    idx = idx + 1;
                }
            } else {
                try {
                    keys = globalThis.Object.keys(raw_obj);
                    for key in keys {
                        txt = str(_value(raw_obj, str(key), ""));
                        if txt != "" {
                            act_lines.append(txt);
                        }
                    }
                } except Exception {
                    ignored = "";
                }
            }
        }
        if len(act_lines) > 0 {
            return _format_log_text(act_lines);
        }
        wm = str(_value(payload, "worker_message", "")).strip();
        status_line = "[job] status=" + str(_value(payload, "status", default_status));
        if wm != "" {
            status_line = status_line + "\n" + wm;
        }
        return status_line;
    }

    def _apply_live_activity_payload(target_id: str, payload: dict, default_status: str = "running") -> str {
        txt = _activity_text_from_payload(payload, default_status);
        _set_live_activity(target_id, txt, True);
        return txt;
    }

    def _apply_paste_job_payload(raw: dict) -> None {
        result = _flatten_function_job_payload(raw);
        st = _extract_job_status(result, "running");
        if st == "" {
            st = "running";
        }
        pasteJobStatus = st;
        pasteRunId = str(_value(result, "run_id", ""));
        pasteRunLogPath = str(_value(result, "run_log_path", ""));
        act_lines = _coerce_list(_value(result, "activity_log_lines", []));
        _apply_live_activity_payload("paste-live-activity-log", result, st);
        resolved = _extract_paste_result_payload(result);
        has_result_fields = (
            str(_value(resolved, "optimized_code", "")).strip() != ""
            or str(_value(resolved, "improvement_ratio", "")).strip() != ""
            or str(_value(resolved, "test_passed", "")).strip() != ""
        );
        if has_result_fields {
            _apply_paste_result(resolved);
        }
        if st in ["queued", "running", "submitting"] {
            pasteError = "";
        }
        if st == "succeeded" {
            fe = _format_error_display(_value(resolved, "error", None));
            if fe != "" {
                st = "failed";
                pasteJobStatus = st;
                pasteError = fe;
            }
        }
        if st == "failed" {
            fe = _format_error_display(_value(result, "error", None));
            pasteError = fe != "" and fe or "Optimization job failed";
        }
        if st == "not_found" {
            fe = _format_error_display(_value(result, "error", None));
            pasteError = fe != "" and fe or "Job not found on server";
        }
    }

    def _apply_repo_job_payload(raw: dict) -> None {
        result = _flatten_function_job_payload(raw);
        payload = _coerce_plain_object(_value(result, "result", {}));
        pr = _coerce_plain_object(_value(payload, "pull_request", {}));
        repoJobId = str(_value(result, "job_id", ""));
        st = _extract_job_status(result, "running");
        if st == "" {
            st = "running";
        }
        repoJobStatus = st;
        repoRunId = str(_value(result, "run_id", ""));
        repoRunLogPath = str(_value(result, "run_log_path", ""));
        repoPullRequestUrl = str(_value(pr, "url", ""));
        tmp = _apply_live_activity_payload("repo-live-activity-log", result, st);
        repoActivityText = tmp.split("\n") if tmp else [];
        if st in ["queued", "running", "submitting"] {
            repoJobResult = "";
        }
        if st == "succeeded" {
            repoJobResult = _repo_job_completion_message(result);
            uiMessage = repoJobResult;
            _notify_repo_job_completion(str(_value(result, "job_id", "")), repoJobResult);
        }
        if st == "failed" {
            repoJobResult = str(_value(result, "error", "Job failed"));
            uiMessage = repoJobResult;
        }
        if st == "not_found" {
            repoJobResult = str(_value(result, "error", "Job not found on server"));
            uiMessage = repoJobResult;
        }
    }

    def _notify_repo_job_completion(job_id: str, message: str) -> None {
        if job_id == "" or message.strip() == "" or repoNotifiedJobId == job_id {
            return;
        }
        repoNotifiedJobId = job_id;
        try {
            globalThis.alert(message);
        } except Exception {
            ignored = "";
        }
    }

    def _repo_job_completion_message(result: dict) -> str {
        payload = _coerce_plain_object(_value(result, "result", {}));
        pr = _coerce_plain_object(_value(payload, "pull_request", {}));
        pr_url = str(_value(pr, "url", ""));
        if pr_url != "" {
            return "Pull request created: " + pr_url;
        }
        if bool(_value(pr, "preview_only", False)) {
            return "Optimization complete. PR preview generated locally; publishing was not requested.";
        }
        branch_name = str(_value(payload, "branch_name", ""));
        if branch_name != "" {
            return "Optimization complete. Branch prepared: " + branch_name;
        }
        return "Optimization complete.";
    }

    def _apply_demo_progress_payload(prog: dict) -> None {
        demoRunStatus = str(_value(prog, "job_status", _value(prog, "status", "running")));
        demoRunStage = str(_value(prog, "stage", "Running benchmark"));
        demoProgressPct = int(_value(prog, "progress_pct", 0));
        live_payload = {
            "status": demoRunStatus,
            "worker_message": demoRunStage,
            "activity_log_lines": _coerce_list(_value(prog, "log_lines", [])),
        };
        _apply_live_activity_payload("demo-live-log-feed", live_payload, demoRunStatus);
        if str(_value(prog, "job_status", "")) == "succeeded" and "result" in prog {
            _apply_demo_result(_coerce_plain_object(_value(prog, "result", {})));
            demoProgressPct = 100;
            demoView = "results";
        }
        if str(_value(prog, "job_status", "")) == "failed" {
            demoRunStage = "Benchmark run failed";
            uiMessage = str(_value(prog, "error", _value(prog, "job_error", "Benchmark run failed")));
        }
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
        summary = _coerce_plain_object(_value(result, "summary", {}));
        rows = _coerce_list(_value(summary, "results", []));
        demoOverviewSvg = str(_value(result, "suite_overview_svg_base64", ""));
        demoPassCount = str(_value(summary, "pass_count", 0));
        demoTargetCount = str(_value(summary, "target_count", 0));
        demoAverageSpeedup = str(_value(summary, "average_speedup", 0.0));
        demoAverageSaved = str(_value(summary, "average_time_saved_pct", 0.0));
        _clear_selected_targets();
        selectedTargets = _coerce_list(_value(result, "final_ranked_targets", []));
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
        finalists = _coerce_list(_value(result, "per_file_finalists", []));
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
        _set_live_activity("paste-live-activity-log", "Submit a job to stream live status and run-log events from the server.", True);
        pasteRunLogPath = "";
        pasteRunId = "";
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

    def _set_source_cursor(target: dict | None, pos: int) -> None {
        try {
            globalThis.setTimeout(lambda -> None {
                target.selectionStart = pos;
                target.selectionEnd = pos;
            }, 0);
        } except Exception as cursorErr {
            ignored = str(cursorErr);
        }
    }

    def _source_editor_value() -> str {
        if pasteEditorView is None {
            return pasteSourceCode;
        }
        try {
            return str(pasteEditorView.state.doc.toString());
        } except Exception as readErr {
            ignored = str(readErr);
            return pasteSourceCode;
        }
    }

    def _set_paste_source_code(value: str, sync_editor: bool = True) -> None {
        pasteSourceCode = value;
        if not sync_editor or pasteEditorView is None {
            return;
        }
        try {
            current = str(pasteEditorView.state.doc.toString());
            if current == value {
                return;
            }
            pasteEditorSyncingFromState = True;
            pasteEditorView.dispatch(
                {
                    "changes": {
                        "from": 0,
                        "to": len(current),
                        "insert": value
                    }
                }
            );
        } except Exception as syncErr {
            ignored = str(syncErr);
        }
        pasteEditorSyncingFromState = False;
    }

    def _destroy_paste_editor() -> None {
        viewExists = str(pasteEditorView) != "null" and str(pasteEditorView) != "undefined" and str(pasteEditorView) != "None";
        if viewExists {
            try {
                pasteEditorView.destroy();
            } except Exception as destroyErr {
                ignored = str(destroyErr);
            }
        }
        pasteEditorView = None;
        pasteEditorReady = False;
        pasteEditorSyncingFromState = False;
    }

    def _ensure_paste_editor_on(hostEl: Any) -> None {
        if hostEl is None {
            return;
        }
        if hostEl.__cmMounted {
            return;
        }
        hostEl.__cmMounted = True;
        try {
            stateMod = cmState;
            viewMod = cmView;
            langMod = cmLangPython;
            commandsMod = cmCommands;
            languageMod = cmLanguage;
            autocompleteMod = cmAutocomplete;
            searchMod = cmSearch;
            submitShortcut = viewMod.keymap.of(
                [
                    {
                        "key": "Mod-Enter",
                        "run": lambda view -> bool {
                            submitPasteJob();
                            return True;
                        }
                    }
                ]
            );
            indentWithTabBinding = viewMod.keymap.of(
                [
                    {
                        "key": "Tab",
                        "run": commandsMod.indentMore,
                        "shift": commandsMod.indentLess
                    }
                ]
            );
            updateListener = viewMod.EditorView.updateListener.of(
                lambda update -> None {
                    if bool(_value(update, "docChanged", False)) and (not pasteEditorSyncingFromState) {
                        pasteSourceCode = str(update.state.doc.toString());
                    }
                }
            );
            editorTheme = viewMod.EditorView.theme(
                {
                    "&": {
                        "min-height": "320px"
                    },
                    ".cm-scroller": {
                        "font-family": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace",
                        "line-height": "1.65",
                        "font-size": "0.95rem"
                    },
                    ".cm-content": {
                        "padding": "0.75rem 0.5rem"
                    }
                }
            );
            nl = globalThis.String.fromCharCode(10);
            escapedNl = globalThis.String.fromCharCode(92, 110);
            rawDoc = globalThis.String(pasteSourceCode);
            initialDoc = str(rawDoc.split(escapedNl).join(nl));
            editorState = stateMod.EditorState.create(
                {
                    "doc": initialDoc,
                    "extensions": [
                        viewMod.lineNumbers(),
                        viewMod.highlightActiveLine(),
                        viewMod.highlightActiveLineGutter(),
                        viewMod.highlightSpecialChars(),
                        viewMod.drawSelection(),
                        viewMod.rectangularSelection(),
                        viewMod.crosshairCursor(),
                        viewMod.dropCursor(),
                        stateMod.EditorState.tabSize.of(4),
                        languageMod.indentUnit.of("    "),
                        languageMod.indentOnInput(),
                        languageMod.bracketMatching(),
                        languageMod.foldGutter(),
                        viewMod.keymap.of(languageMod.foldKeymap),
                        autocompleteMod.closeBrackets(),
                        viewMod.keymap.of(autocompleteMod.closeBracketsKeymap),
                        autocompleteMod.autocompletion(),
                        viewMod.keymap.of(autocompleteMod.completionKeymap),
                        searchMod.highlightSelectionMatches(),
                        viewMod.keymap.of(searchMod.searchKeymap),
                        langMod.python(),
                        cmOneDark.oneDark,
                        viewMod.keymap.of(commandsMod.defaultKeymap),
                        viewMod.keymap.of(commandsMod.historyKeymap),
                        commandsMod.history(),
                        indentWithTabBinding,
                        submitShortcut,
                        updateListener,
                        editorTheme,
                    ]
                }
            );
            pasteEditorView = globalThis.Reflect.construct(
                viewMod.EditorView,
                [{"state": editorState, "parent": hostEl}]
            );
            pasteEditorReady = True;
        } except Exception as cmErr {
            globalThis.console.error("[CM] FAILED:", cmErr);
            hostEl.__cmMounted = False;
            _destroy_paste_editor();
            uiMessage = "CodeMirror failed to load. Falling back to plain text editing.";
            ignored = str(cmErr);
        }
    }

    def setPasteEditorHost(el: Any) -> None {
        if el is None {
            return;
        }
        pasteEditorHostEl = el;
        _ensure_paste_editor_on(el);
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

    def handleSourceEditorPaste(e: dict | None) -> None {
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
            _set_paste_source_code(updated);
            _set_source_cursor(target, start + len(normalized));
        } except Exception as pasteErr {
            ignored = str(pasteErr);
        }
    }

    async def handleSourceEditorKeydown(e: dict | None) -> None {
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
                _set_paste_source_code(updated);
                _set_source_cursor(target, start - 4);
            }
            return;
        }
        updated = value[0:start] + "    " + value[end:];
        _set_paste_source_code(updated);
        _set_source_cursor(target, start + 4);
    }

    def _toggle_theme() -> None {
        nextTheme = "dark";
        if currentTheme == "dark" {
            nextTheme = "light";
        }
        currentTheme = nextTheme;
        _set_theme_attr(nextTheme);
        _save_theme(nextTheme);
    }

    def _extract_paste_result_payload(job_payload: dict) -> dict {
        if "improvement_ratio" in job_payload or "optimized_code" in job_payload {
            return job_payload;
        }
        inner = _coerce_plain_object(_value(job_payload, "result", {}));
        if "improvement_ratio" in inner or "optimized_code" in inner {
            return inner;
        }
        nested = _coerce_plain_object(_value(inner, "result", {}));
        if "improvement_ratio" in nested or "optimized_code" in nested {
            return nested;
        }
        return inner;
    }

    def _apply_paste_result(result: dict) -> None {
        metrics = _coerce_plain_object(_value(result, "metrics", {}));
        baseline = _coerce_plain_object(_value(result, "baseline_metrics", {}));
        pasteImprovementRatio = str(_value(result, "improvement_ratio", ""));
        before_exec = _value(baseline, "execution_time", _value(baseline, "median_ms", ""));
        after_exec = _value(metrics, "execution_time", _value(metrics, "median_ms", ""));
        pasteExecutionBeforeMs = str(before_exec);
        pasteExecutionAfterMs = str(after_exec);
        pasteTerminationReason = str(_value(result, "termination_reason", ""));
        pasteTestPassed = str(_value(result, "test_passed", ""));
        server_orig = str(_value(result, "original_source_code", "")).strip();
        if server_orig != "" {
            pasteOriginalCode = _normalize_source_code(server_orig);
        } else {
            pasteOriginalCode = _normalize_source_code(
                pasteSubmittedSourceCode != "" and pasteSubmittedSourceCode or pasteSourceCode
            );
        }
        pasteOptimizedCode = _normalize_source_code(str(_value(result, "optimized_code", "")));
        er = _value(result, "error", None);
        fe = _format_error_display(er);
        if fe != "" {
            pasteError = fe;
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
        job_id_to_stream = expected_job_id;
        _reset_paste_result();
        uiMessage = "";
        _update_expected_feedback();
        try {
            latestSource = _source_editor_value();
            normalizedSource = _normalize_source_code(latestSource);
            _set_paste_source_code(normalizedSource);
            pasteSubmittedSourceCode = normalizedSource;
            payload = {
                "operation": "optimize_input",
                "job_id": expected_job_id,
                "submission_channel": "ui",
                "ui_surface": "paste",
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
            try { payload = globalThis.JSON.parse(globalThis.JSON.stringify(payload)); } except Exception { ignored = ""; }
            payload_json = "";
            try { payload_json = str(globalThis.JSON.stringify(payload)); } except Exception { payload_json = ""; }
            if payload_json == "" or payload_json == "null" or payload_json == "undefined" {
                raise Exception("Failed to serialize optimization payload");
            }
            submitted = await ringtail_submit_optimization_job(payload_json);
            try { submitted = globalThis.JSON.parse(globalThis.JSON.stringify(submitted)); } except Exception { ignored = ""; }
            submitted = _flatten_function_job_payload(submitted);
            returned_job_id = str(_value(submitted, "job_id", ""));
            returned_status = str(_value(submitted, "status", "queued"));
            if returned_job_id == "" {
                probe = _flatten_function_job_payload(
                    await ringtail_get_optimization_job(expected_job_id)
                );
                probe_id = str(_value(probe, "job_id", ""));
                probe_st = str(_value(probe, "status", ""));
                if probe_id != "" and probe_st != "not_found" {
                    returned_job_id = probe_id;
                    returned_status = probe_st;
                }
            }
            # Defensive fallback: if envelope parsing missed job_id, keep polling
            # the client-generated expected id (server honors provided job_id).
            if returned_job_id == "" {
                fallback_id = str(pasteJobId).strip();
                if fallback_id == "" {
                    fallback_id = str(expected_job_id).strip();
                }
                returned_job_id = fallback_id;
            }
            if str(returned_status).strip() == "" {
                returned_status = "running";
            }
            if returned_job_id != "" and returned_job_id != expected_job_id {
                pasteJobId = returned_job_id;
                job_id_to_stream = returned_job_id;
            }
            if returned_job_id == "" {
                pasteJobStatus = "failed";
                fe = _format_error_display(_value(submitted, "error", None));
                pasteError = fe != "" and fe or "No job ID returned";
            } else {
                pasteJobStatus = returned_status;

                globalThis.setTimeout(lambda -> None {
                    _poll_active_job(job_id_to_stream, "paste");
                }, 1500);
            }
        } except Exception as err {
            pasteJobStatus = "failed";
            pasteError = str(err);
            uiMessage = "Paste optimization failed to submit: " + str(err);
        } finally {
            pasteSubmitting = False;
        }
    }

    async def cancelPasteJob -> None {
        if str(pasteJobId).strip() == "" or pasteCancelling {
            return;
        }
        pasteCancelling = True;
        try {
            await ringtail_cancel_optimization_job(pasteJobId);
            await pollPasteJobForce();
        } except Exception as err {
            uiMessage = "Could not cancel job: " + str(err);
        } finally {
            pasteCancelling = False;
        }
    }

    async def submitPasteJob -> None {
        await _submit_paste_job();
    }

    async def pollPasteJobForce -> None {
        await _poll_paste_job_impl(True);
    }

    async def _poll_paste_job_impl(force: bool) -> None {
        if pasteJobId == "" {
            return;
        }
        if not force {
            if pasteJobStatus in ["succeeded", "not_found"] {
                return;
            }
            if pasteJobStatus == "failed" {
                return;
            }
            if pasteJobStatus == "" {
                return;
            }
        }
        result = await ringtail_get_optimization_job(pasteJobId);
        # Flatten only inside _apply_paste_job_payload (avoids diverging peel logic).
        _apply_paste_job_payload(result);
    }

    def _is_terminal_job_status(status: str) -> bool {
        st = _lower_text(status);
        return (
            st == "succeeded"
            or st == "success"
            or st == "failed"
            or st == "interrupted"
            or st == "not_found"
            or st == "completed"
            or st == "done"
            or st == "error"
            or st == "cancelled"
            or st == "canceled"
            or st == "aborted"
            or st == "stopped"
            or st == "timeout"
            or st == "timed_out"
        );
    }

    def _paste_job_active() -> bool {
        return str(pasteJobId).strip() != "" and not _is_terminal_job_status(pasteJobStatus);
    }

    def _repo_job_active() -> bool {
        return str(repoJobId).strip() != "" and not _is_terminal_job_status(repoJobStatus);
    }

    def _extract_job_status(
        payload: dict | list | str | int | float | bool | None,
        fallback: str = ""
    ) -> str {
        flat = _flatten_function_job_payload(payload);
        # Some responses put status in slightly different keys or nested objects.
        candidates = [
            _value(flat, "status", ""),
            _value(flat, "job_status", ""),
            _value(flat, "state", "")
        ];
        nested_result = _coerce_plain_object(_value(flat, "result", {}));
        candidates.append(_value(nested_result, "status", ""));
        candidates.append(_value(nested_result, "job_status", ""));
        for raw_st in candidates {
            st = _lower_text(raw_st);
            if st != "" and st != "none" and st != "null" and st != "undefined" {
                return st;
            }
        }
        # If status is missing but the job has a finish marker or an error, treat
        # it as terminal to avoid accidental infinite polling.
        finished_at = str(_value(flat, "finished_at", "")).strip();
        if finished_at != "" and finished_at != "None" and finished_at != "null" {
            return "completed";
        }
        err_txt = str(_value(flat, "error", "")).strip();
        if err_txt != "" and err_txt != "None" and err_txt != "null" {
            return "failed";
        }
        return _lower_text(fallback);
    }

    def _active_job_id_for_type(job_type: str) -> str {
        if job_type == "repo" {
            return str(repoJobId).strip();
        }
        if job_type == "paste" {
            return str(pasteJobId).strip();
        }
        return "";
    }

    def _active_job_status_for_type(job_type: str) -> str {
        if job_type == "repo" {
            return _lower_text(repoJobStatus);
        }
        if job_type == "paste" {
            return _lower_text(pasteJobStatus);
        }
        return "";
    }

    async def _poll_active_job(job_id: str, job_type: str) -> None {
        # Do not read `has` state (pasteJobId, repoJobId, _active_job_id_for_type) here:
        # the Jac client often returns "" for those inside async/setTimeout callbacks, which
        # made `job_id != pasteJobId` always true and stopped polling after one fetch.
        # Rely on closure `job_id` only; _apply_*_job_payload uses API payload, not guards.
        done = False;
        try {
            if str(job_id).strip() == "" or (job_type != "repo" and job_type != "paste") {
                done = True;
            }
            if not done {
                status = "running";
                try {
                    if job_type == "repo" {
                        latest = _flatten_function_job_payload(await ringtail_get_repo_agent_job(job_id));
                        active_st = _extract_job_status(latest, "");
                        if active_st == "not_found" {
                            status = "running";
                        } else {
                            _apply_repo_job_payload(latest);
                            status = active_st;
                        }
                    } elif job_type == "paste" {
                        raw = await ringtail_get_optimization_job(job_id);
                        flat = _flatten_function_job_payload(raw);
                        flat_st = _extract_job_status(flat, "");
                        if flat_st == "not_found" {
                            status = "running";
                        } else {
                            _apply_paste_job_payload(raw);
                            status = flat_st;
                        }
                    }
                } except Exception as pollErr {
                    ignored = str(pollErr);
                    status = "running";
                }
                if status == "" {
                    status = "running";
                }
                if _is_terminal_job_status(status) {
                    done = True;
                }
            }
        } except Exception as outerErr {
            ignored = str(outerErr);
        }
        if not done {
            globalThis.setTimeout(lambda -> None { _poll_active_job(job_id, job_type); }, 1500);
        }
    }

    async def handleGithubLogin() -> None {
        result = await ringtail_get_github_login_url();
        url = _value(result, "url", "");
        if url != "" {
            globalThis.window.location.href = url;
        } else {
            uiMessage = str(_value(result, "error", "OAuth not configured"));
        }
    }

    def applyPatAuth() -> None {
        token = str(githubPatInput).strip();
        if token == "" {
            uiMessage = "Enter a GitHub personal access token first.";
            return;
        }
        githubPatToken = token;
        githubPatInput = "";
        githubAuthMode = "pat";
        _save_pat_session(token);
        uiMessage = "Using PAT auth for this browser session.";
        loadAvailableRepos();
    }

    def clearPatAuth() -> None {
        githubPatToken = "";
        githubPatInput = "";
        if sessionToken == "" {
            githubAuthMode = "none";
        } else {
            githubAuthMode = "oauth";
        }
        _clear_pat_session();
        availableRepos = [];
        uiMessage = "Cleared PAT session auth.";
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
        result = await ringtail_exchange_github_code(code, state);
        if "error" in result {
            uiMessage = str(result["error"]);
            return;
        }
        sessionToken = str(result["session_token"]);
        githubAuthMode = "oauth";
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
        result = await ringtail_get_session(saved);
        if "error" in result {
            _clear_session_cookie();
            return;
        }
        sessionToken = saved;
        githubAuthMode = "oauth";
        githubLogin = str(result["github_login"]);
        githubUserId = int(result["github_user_id"]);
        githubAvatarUrl = str(_value(result, "github_avatar_url", ""));
        iid = int(_value(_value(result, "installation", {}), "installation_id", 0));
        if iid != 0 {
            installationId = iid;
            installAccountLogin = str(_value(_value(result, "installation", {}), "account_login", ""));
        }
        await loadAvailableRepos();
    }

    async def handleLogout() -> None {
        if sessionToken != "" {
            await ringtail_logout(sessionToken);
        }
        _clear_session_cookie();
        _clear_pat_session();
        sessionToken = "";
        githubLogin = "";
        githubUserId = 0;
        githubAvatarUrl = "";
        installationId = 0;
        installAccountLogin = "";
        githubPatToken = "";
        githubPatInput = "";
        githubAuthMode = "none";
        availableRepos = [];
    }

    async def handleInstallApp() -> None {
        result = await ringtail_get_github_app_install_info(sessionToken);
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
        result = await ringtail_get_session(sessionToken);
        iid = int(_value(_value(result, "installation", {}), "installation_id", 0));
        if iid != 0 {
            installationId = iid;
            installAccountLogin = str(_value(_value(result, "installation", {}), "account_login", ""));
        }
        await loadAvailableRepos();
    }

    async def loadAvailableRepos() -> None {
        if sessionToken == "" and githubPatToken == "" {
            return;
        }
        reposLoading = True;
        try {
            result = await ringtail_list_github_repos(sessionToken, githubPatToken);
            errMsg = str(_value(result, "error", ""));
            if errMsg != "" {
                uiMessage = "Could not load repos: " + errMsg;
                availableRepos = [];
            } else {
                repos = _value(result, "repositories", []);
                loaded = [];
                for r in repos {
                    loaded.append({
                        "full_name": str(_value(r, "full_name", "")),
                        "private": bool(_value(r, "private", False)),
                        "default_branch": str(_value(r, "default_branch", ""))
                    });
                }
                availableRepos = loaded;
                if repoBaseBranch.strip() == "" and repoUrl.strip() != "" {
                    guessed = _repo_default_branch_for_url(repoUrl);
                    if guessed != "" {
                        repoBaseBranch = guessed;
                    }
                }
            }
        } except Exception as e {
            uiMessage = "Could not load repos: " + str(e);
            availableRepos = [];
        }
        reposLoading = False;
    }

    def _repo_default_branch_for_url(url: str) -> str {
        target = str(url).strip();
        if target == "" {
            return "";
        }
        for r in availableRepos {
            name = str(_value(r, "full_name", ""));
            repo_url = "https://github.com/" + name;
            if repo_url == target {
                return str(_value(r, "default_branch", "")).strip();
            }
        }
        return "";
    }

    async def loadPasteConfigProfiles() -> None {
        try {
            result = await ringtail_list_agent_config_names();
            names = [];
            if globalThis.Array.isArray(result) {
                for name in result {
                    label = str(name).strip();
                    if label != "" {
                        names.append(label);
                    }
                }
            } else {
                payload = _coerce_plain_object(result);
                raw = _value(payload, "profiles", _value(payload, "names", []));
                if globalThis.Array.isArray(raw) {
                    for name in raw {
                        label = str(name).strip();
                        if label != "" {
                            names.append(label);
                        }
                    }
                }
            }
            if len(names) > 0 {
                pasteConfigProfiles = names;
                if pasteConfigName not in names {
                    pasteConfigName = names[0];
                }
                return;
            }
        } except Exception as e {
            ignored = str(e);
        }
        pasteConfigProfiles = ["default", "live-fast", "candidate-search", "baseline-measure", "test-fast"];
        if pasteConfigName not in pasteConfigProfiles {
            pasteConfigName = "live-fast";
        }
    }

    def renderRepoOptions() -> list {
        opts = [];
        for r in availableRepos {
            name = str(_value(r, "full_name", ""));
            url = "https://github.com/" + name;
            label = name;
            if bool(_value(r, "private", False)) {
                label = name + " (private)";
            }
            branch = str(_value(r, "default_branch", "")).strip();
            if branch != "" {
                label = label + " [" + branch + "]";
            }
            opts.append(<option key={name} value={url}>{label}</option>);
        }
        return opts;
    }

    def renderPasteConfigOptions() -> list {
        opts = [];
        for cfg in pasteConfigProfiles {
            name = str(cfg);
            opts.append(<option key={name} value={name}>{name}</option>);
        }
        return opts;
    }

    async def handleInstallCallback() -> None {
        iid = _get_query_param("installation_id");
        if iid == "" {
            return;
        }
        if sessionToken == "" {
            stateToken = _get_query_param("state");
            if stateToken != "" {
                saved = await ringtail_get_session(stateToken);
                if "error" not in saved {
                    sessionToken = stateToken;
                    githubAuthMode = "oauth";
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
        result = await ringtail_save_github_installation(sessionToken, int(iid), "");
        if _value(result, "success", False) {
            installationId = int(iid);
        }
        globalThis.window.history.replaceState({}, "", globalThis.window.location.pathname);
        activeTab = "repo";
    }

    async def submitRepoJob -> None {
        repoSubmitting = True;
        repoJobStatus = "submitting";
        repoJobResult = "";
        repoRunId = "";
        repoRunLogPath = "";
        repoPullRequestUrl = "";
        repoNotifiedJobId = "";
        _set_live_activity("repo-live-activity-log", "Submitting repository optimization job...", True);
        uiMessage = "";
        try {
            if repoEntryPoint.strip() == "" {
                repoJobStatus = "failed";
                repoJobResult = "Entry Point is required.";
                uiMessage = "Please provide an explicit entry point such as 'python runner.py'.";
                _set_live_activity(
                    "repo-live-activity-log",
                    "Repository job blocked: entry point is required before submission.",
                    True
                );
                return;
            }
            payload = {
                "repo_url": repoUrl,
                "prompt": repoPrompt,
                "publish_pr": repoPublishPr,
                "session_token": sessionToken,
                "submission_channel": "ui",
                "ui_surface": repoExperienceMode == "local" and "repo_local" or "repo_github",
                "backend_config": {"backend": "local"}
            };
            if githubPatToken != "" {
                payload["token"] = githubPatToken;
            }
            if repoTestCommand != "" {
                payload["test_command"] = repoTestCommand;
            }
            if repoEntryPoint != "" {
                payload["entry_point"] = repoEntryPoint;
            }
            if repoBaseBranch.strip() != "" {
                payload["base_branch"] = repoBaseBranch.strip();
            }
            if repoSetupCommands != "" {
                parts = repoSetupCommands.split("\n");
                cmds = [];
                for p in parts {
                    stripped = p.strip();
                    if stripped != "" {
                        cmds.append(stripped);
                    }
                }
                if len(cmds) > 0 {
                    payload["setup_commands"] = cmds;
                }
            }
            payload_json = "";
            try { payload_json = str(globalThis.JSON.stringify(payload)); } except Exception { payload_json = ""; }
            if payload_json == "" or payload_json == "null" or payload_json == "undefined" {
                raise Exception("Failed to serialize repository payload");
            }
            submitted = await ringtail_submit_repo_agent_job(payload_json);
            submitted = _flatten_function_job_payload(submitted);
            returned_repo_job_id = str(_value(submitted, "job_id", ""));
            returned_repo_status = str(_value(submitted, "status", "queued"));
            repoJobId = returned_repo_job_id;
            repoJobStatus = returned_repo_status;
            _apply_repo_job_payload(submitted);
            if returned_repo_job_id == "" {
                repoJobStatus = "failed";
                repoJobResult = str(_value(submitted, "error", "No job ID returned"));
            } else {
                globalThis.setTimeout(lambda -> None {
                    _poll_active_job(returned_repo_job_id, "repo");
                }, 250);
            }
        } except Exception as err {
            repoJobStatus = "failed";
            repoJobResult = str(err);
            uiMessage = "Job submission failed: " + str(err);
        } finally {
            repoSubmitting = False;
        }
    }

    async def cancelRepoJob -> None {
        if str(repoJobId).strip() == "" or repoCancelling {
            return;
        }
        repoCancelling = True;
        try {
            await ringtail_cancel_optimization_job(repoJobId);
            await pollRepoJob(True);
        } except Exception as err {
            uiMessage = "Could not cancel job: " + str(err);
        } finally {
            repoCancelling = False;
        }
    }

    async def pollRepoJob(force: bool = False) -> None {
        if repoJobId == "" {
            return;
        }
        if (not force) and repoJobStatus in ["succeeded", "interrupted", "not_found", ""] {
            return;
        }
        result = await ringtail_get_repo_agent_job(repoJobId);
        _apply_repo_job_payload(result);
    }

    async def refreshBenchmarkContext() -> None {
        sig = str(demoBenchmarkId);
        now = 0;
        try {
            now = int(globalThis.Date.now());
        } except Exception {
            now = 0;
        }
        if (
            sig == benchmarkContextRefreshSig
            and benchmarkContextRefreshAtMs > 0
            and (now - benchmarkContextRefreshAtMs) < 900
        ) {
            return;
        }
        benchmarkContextRefreshSig = sig;
        benchmarkContextRefreshAtMs = now;
        benchmarks = await ringtail_get_ranked_demo_benchmarks();
        catalog = await ringtail_get_ranked_demo_suite_catalog(demoBenchmarkId);
        demoBenchmarkText = _format_demo_benchmarks(_coerce_plain_object(benchmarks));
        _clear_demo_files();
        files = _coerce_list(_value(catalog, "files", []));
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
        latest = await ringtail_get_latest_run(selectedKind);
        if not bool(_value(latest, "success", False)) {
            uiMessage = str(_value(latest, "error", "Could not locate latest run for kind '" + selectedKind + "'"));
            return;
        }
        latestMeta = _coerce_plain_object(_value(latest, "latest", {}));
        latestKind = str(_value(latestMeta, "kind", ""));
        latestJobId = str(_value(latestMeta, "job_id", ""));
        latestRunId = str(_value(latestMeta, "run_id", ""));
        if latestKind == "ranked_demo_suite" and latestJobId != "" {
            progress = await ringtail_get_ranked_demo_job_progress(latestJobId);
            prog_latest = _coerce_plain_object(progress);
            if "result" in prog_latest {
                _apply_demo_result(_coerce_plain_object(prog_latest["result"]));
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
        result = await ringtail_get_latest_ranked_demo_suite();
        result_dict = _coerce_plain_object(result);
        if bool(_value(result_dict, "success", False)) or "summary" in result_dict {
            _apply_demo_result(result_dict);
            demoRunStatus = "succeeded";
            demoRunStage = "Showing latest verified benchmark run";
            demoProgressPct = 100;
            demoView = "results";
            return;
        }
        uiMessage = str(_value(result_dict, "error", "Could not load latest benchmark result"));
    }

    async def _start_demo_run() -> None {
        try {
            demoStreamGen = demoStreamGen + 1;
            dg = demoStreamGen;
            demoStreamSeq = 0;
            demoJobId = _new_demo_job_id();
            demoView = "running";
            demoRunStatus = "queued";
            demoRunStage = "Submitting benchmark run";
            demoProgressPct = 6;
            _set_live_activity("demo-live-log-feed", "Submitting benchmark run...", True);
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
                "per_file_k": int(demoPerFileK),
                "submission_channel": "ui",
                "ui_surface": "repo_local"
            };
            try { payload = globalThis.JSON.parse(globalThis.JSON.stringify(payload)); } except Exception { ignored = ""; }
            payload_json = "";
            try { payload_json = str(globalThis.JSON.stringify(payload)); } except Exception { payload_json = ""; }
            if payload_json == "" or payload_json == "null" or payload_json == "undefined" {
                raise Exception("Failed to serialize benchmark payload");
            }
            await ringtail_submit_optimization_job(payload_json);
            # Do not await the full long-poll chain here; schedule it so UI state
            # can flush between notifications in Jac/React runtime.
            globalThis.setTimeout(lambda -> None { _demo_job_stream_tick(dg); }, 0);
        } except Exception as err {
            demoRunStatus = "failed";
            demoRunStage = "Benchmark submission failed";
            demoProgressPct = 0;
            _set_live_activity("demo-live-log-feed", "Benchmark submission failed.\n" + str(err), True);
            uiMessage = "Could not start benchmark run: " + str(err);
        }
    }

    async def startDemoRun -> None {
        await _start_demo_run();
    }

    async def pollDemoProgress() -> None {
        if demoJobId == "" {
            return;
        }
        progress = await ringtail_get_ranked_demo_job_progress(demoJobId);
        _apply_demo_progress_payload(_coerce_plain_object(progress));
    }

    async def _demo_job_stream_tick(expected_gen: int) -> None {
        if int(demoStreamGen) != int(expected_gen) {
            return;
        }
        if str(demoJobId).strip() == "" {
            return;
        }
        await pollDemoProgress();
        if int(demoStreamGen) != int(expected_gen) {
            return;
        }
        st = _lower_text(demoRunStatus);
        if _is_terminal_job_status(st) {
            return;
        }
        globalThis.setTimeout(lambda -> None { _demo_job_stream_tick(expected_gen); }, 1500);
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
            loaded_theme = _load_theme("dark");
            currentTheme = loaded_theme;
            _set_theme_attr(loaded_theme);
            if demoServerUrl == "" {
                demoServerUrl = str(globalThis.location.origin);
            }
            healthStatus = await ringtail_health();
            await restoreSession();
            savedPat = _load_pat_session();
            if savedPat != "" {
                githubPatToken = savedPat;
                githubAuthMode = "pat";
                await loadAvailableRepos();
            }
            if _get_query_param("installation_id") != "" {
                await handleInstallCallback();
            } elif _get_query_param("code") != "" and _get_query_param("installation_id") == "" {
                await handleOAuthCallback();
            }
            _update_expected_feedback();
            await loadPasteConfigProfiles();
            await refreshBenchmarkContext();
        } except Exception as e {
            healthStatus = {"status": "error", "message": str(e)};
            uiMessage = str(e);
        }
    }

    return
        <div className={currentTheme == "dark" and "demo-shell theme-dark" or "demo-shell theme-light"}>
            <div className="demo-hero">
                <div className="demo-hero-copy">
                    <span className="version">Ringtail</span>
                    <h1>AI-Powered Code Optimization Platform</h1>
                    <p>A professional optimization website for validating speedups with tests and profiling, from single pasted functions to full repository workflows.</p>
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

            <div className="tab-bar" role="tablist" aria-label="Website sections">
                <button id="tab-home" role="tab" aria-selected={activeTab == "home" and "true" or "false"} className={activeTab == "home" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "home"; }}>Home</button>
                <button id="tab-paste" role="tab" aria-selected={activeTab == "paste" and "true" or "false"} className={activeTab == "paste" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "paste"; }}>Paste Demo</button>
                <button id="tab-repository" role="tab" aria-selected={activeTab == "repository" and "true" or "false"} className={activeTab == "repository" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "repository"; }}>Repository Optimization</button>
                <button id="tab-run-history" role="tab" aria-selected={activeTab == "run_history" and "true" or "false"} className={activeTab == "run_history" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { openRunHistoryTab(); }}>Run History</button>
                <button id="tab-cli" role="tab" aria-selected={activeTab == "cli" and "true" or "false"} className={activeTab == "cli" and "tab-button active" or "tab-button"}
                    onClick={lambda -> None { activeTab = "cli"; }}>CLI Setup</button>
            </div>

            {uiMessage != "" and <div className="info-banner" role="status" aria-live="polite">{uiMessage}</div>}

            {activeTab == "home" and
                <div className="container" role="tabpanel" aria-labelledby="tab-home">
                    <div className="hero-card">
                        <h2>Build Faster, Verified Code With Ringtail</h2>
                        <p className="hero-subtitle">Ringtail compares original and optimized implementations with measurable before/after runtime, preserving correctness through validation and tests. Use it for quick demos, benchmark suites, and repository-scale optimization workflows.</p>
                        <div className="panel-actions" style={{"marginTop": "1rem"}}>
                            <button className="primary-button" onClick={lambda -> None { activeTab = "paste"; }}>
                                Try Demo
                            </button>
                            <button className="secondary-button" onClick={lambda -> None { activeTab = "repository"; repoExperienceMode = "local"; }}>
                                Optimize Project Files
                            </button>
                        </div>
                    </div>
                    <div className="hero-card home-video-card">
                        <h3>Watch Ringtail In Action</h3>
                        <p className="hero-subtitle">A short walkthrough of the optimization workflow from paste demo to measurable runtime improvements.</p>
                        <div className="home-video-frame">
                            <video className="home-video-player" controls playsInline preload="metadata">
                                <source src="/assets/ringtail_demo.mp4" type="video/mp4" />
                                Your browser does not support the video tag.
                            </video>
                        </div>
                    </div>
                    <div className="feature-grid">
                        <div className="feature-card clickable" onClick={lambda -> None { activeTab = "paste"; }}>
                            <h3>Paste Demo</h3>
                            <p>Paste one function, run optimization, and inspect side-by-side code plus speedup metrics in minutes.</p>
                        </div>
                        <div className="feature-card clickable" onClick={lambda -> None { activeTab = "repository"; }}>
                            <h3>Repository Optimization</h3>
                            <p>Run ranked optimization on benchmark-style file suites or connect GitHub to create optimization pull requests.</p>
                        </div>
                        <div className="feature-card clickable" onClick={lambda -> None { activeTab = "cli"; }}>
                            <h3>CLI Setup</h3>
                            <p>Install dependencies, start the Jac app, and run command-line optimization workflows locally.</p>
                        </div>
                    </div>
                </div>
            }

            {activeTab == "paste" and
                <div className="container" role="tabpanel" aria-labelledby="tab-paste">
                    <div className="hero-card" role="region" aria-label="Paste optimizer form">
                        <h2>Paste Code To Optimize</h2>
                        <p className="hero-subtitle">Submit a single function with an optional test assertion to get measurable before/after runtime feedback.</p>
                        <form className="form-grid" onSubmit={lambda e -> None {
                            try { e.preventDefault(); } except Exception { ignored = ""; }
                            submitPasteJob();
                        }}>
                            <label className="field field-full">
                                <span>Source Code</span>
                                <div className={pasteEditorReady and "code-editor paste-cm-host ready" or "code-editor paste-cm-host"}
                                    ref={lambda el -> None { setPasteEditorHost(el); }} />
                                {not pasteEditorReady and
                                    <textarea className="code-editor code-editor-fallback"
                                        rows={16}
                                        spellCheck={False}
                                        wrap="off"
                                        value={pasteSourceCode}
                                        onChange={lambda e -> None { _set_paste_source_code(e.target.value, False); }}
                                        onPaste={lambda e -> None { handleSourceEditorPaste(e); }}
                                        onKeyDown={lambda e -> None { handleSourceEditorKeydown(e); }} />
                                }
                                <div className="field-help">Shortcuts: Tab indents, Shift+Tab unindents, Cmd/Ctrl+Enter submits. Pasted markdown fences and escaped newline blobs are cleaned automatically.</div>
                            </label>
                            <label className="field">
                                <span>Function Name</span>
                                <input value={pasteFunctionName} onChange={lambda e -> None { pasteFunctionName = e.target.value; }} />
                            </label>
                            <label className="field">
                                <span>Function Call</span>
                                <input value={pasteFunctionCall} onChange={lambda e -> None { pasteFunctionCall = e.target.value; }} />
                            </label>
                            <label className="field">
                                <span>Validation Call (optional)</span>
                                <input value={pasteTestCall} placeholder="slow_add(5)" onChange={lambda e -> None { pasteTestCall = e.target.value; _update_expected_feedback(); }} />
                            </label>
                            <label className="field">
                                <span>Expected Result (optional)</span>
                                <input value={pasteExpected} placeholder="10, string, true, null, [1,2]" onChange={lambda e -> None { pasteExpected = e.target.value; _update_expected_feedback(); }} />
                                <div className="editor-status">
                                    <span className={pasteExpectedStatus == "ok" and "validation-chip ok" or pasteExpectedStatus == "warn" and "validation-chip warn" or "validation-chip"}>
                                        {pasteExpectedStatus == "ok" and "Expected value parsed" or pasteExpectedStatus == "warn" and "Needs attention" or "Optional field"}
                                    </span>
                                    <span className="validation-chip">{pasteExpectedPreview}</span>
                                </div>
                            </label>
                            <label className="field">
                                <span>Config Profile</span>
                                <select value={pasteConfigName} onChange={lambda e -> None { pasteConfigName = e.target.value; }}>
                                    {renderPasteConfigOptions()}
                                </select>
                            </label>
                            <label className="field">
                                <span>Analysis Mode</span>
                                <select value={pasteAnalysisMode} onChange={lambda e -> None { pasteAnalysisMode = e.target.value; }}>
                                    <option value="llm">llm</option>
                                    <option value="heuristic">heuristic</option>
                                </select>
                            </label>
                            <label className="checkbox-field">
                                <input type="checkbox" checked={pasteEnableRunLog} onChange={lambda e -> None { pasteEnableRunLog = e.target.checked; }} />
                                <span>Enable run logs</span>
                            </label>
                            <div className="panel-actions field-full">
                                <button type="submit" className="primary-button" disabled={pasteSubmitting or _paste_job_active()}>
                                    {pasteSubmitting and "Submitting..." or _paste_job_active() and "Job In Progress" or "Optimize Pasted Code"}
                                </button>
                                {_paste_job_active() and not pasteSubmitting and
                                    <button type="button" className="secondary-button" disabled={pasteCancelling} onClick={lambda -> None { cancelPasteJob(); }}>
                                        {pasteCancelling and "Cancelling..." or "Cancel job"}
                                    </button>
                                }
                                {pasteJobId != "" and <button type="button" className="secondary-button" disabled={pasteSubmitting} onClick={lambda -> None { pollPasteJobForce(); }}>Refresh now</button>}
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
                            <strong>{pasteImprovementRatio != "" and _format_ratio_display(pasteImprovementRatio) + "x" or "--"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Exec Time (Before -> After)</span>
                            <strong>{pasteExecutionBeforeMs != "" and _format_exec_time_display(pasteExecutionBeforeMs) + " -> " + _format_exec_time_display(pasteExecutionAfterMs) or "--"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Tests Passed</span>
                            <strong>{pasteTestPassed != "" and pasteTestPassed or "--"}</strong>
                        </div>
                    </div>

                    {pasteJobId != "" and
                        <div className="section field-full" style={{"marginTop": "0.5rem"}}>
                            <div className="log-card">
                                <div className="log-card-header">
                                    <div>
                                        <h3>Live Activity</h3>
                                        <p className="field-help">While a job is active, the dashboard polls the server every few seconds so status and run-log lines stay in sync without a manual refresh.</p>
                                    </div>
                                </div>
                                <pre
                                    id="paste-live-activity-log"
                                    data-live-id="paste-live-activity-log"
                                    className="log-feed"
                                    role="log"
                                    aria-live="polite"
                                    style={{"whiteSpace": "pre-wrap", "wordBreak": "break-word"}}
                                    ref={lambda el -> None { if el is not None { _sync_live_activity_dom("paste-live-activity-log", _live_activity_text("paste-live-activity-log", "Submit a job to stream live status and run-log events from the server.")); } }}
                                ></pre>
                            </div>
                        </div>
                    }

                    <div className="demo-layout" style={{"marginTop": "1.75rem"}}>
                        <div className="section">
                            <h3>Job Details</h3>
                            <div className="simple-list">
                                {pasteJobId != "" and <div className="simple-list-item">Job ID: {pasteJobId}</div>}
                                {pasteRunId != "" and <div className="simple-list-item">Run ID: {pasteRunId}</div>}
                                {pasteRunLogPath != "" and <div className="simple-list-item">Run log file: {pasteRunLogPath}</div>}
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

            {activeTab == "repository" and
                <div className="container" role="tabpanel" aria-labelledby="tab-repository">
                    <div className="hero-card">
                        <h2>Repository Optimization</h2>
                        <p className="hero-subtitle">Choose how to optimize repository-scale code: run local benchmark/file workflows or connect GitHub for PR-ready changes.</p>
                        <div className="mode-toggle" role="tablist" aria-label="Repository modes">
                            <button className={repoExperienceMode == "local" and "tab-button active" or "tab-button"} onClick={lambda -> None { repoExperienceMode = "local"; }}>
                                Local Files & Benchmark
                            </button>
                            <button className={repoExperienceMode == "github" and "tab-button active" or "tab-button"} onClick={lambda -> None { repoExperienceMode = "github"; if sessionToken != "" and installationId == 0 { loadInstallation(); }; }}>
                                GitHub Integration
                            </button>
                        </div>
                    </div>
                    {repoExperienceMode == "github" and
                        <div className="repo-mode-panel">
                            {githubLogin == "" and
                                <div className="hero-card" style={{"textAlign": "center", "padding": "3rem"}}>
                                    <h2>Connect GitHub</h2>
                                    <p className="hero-subtitle">Paste a personal access token for this browser session, or use OAuth if your server is configured for it.</p>
                                    <div className="pat-auth-panel">
                                        <a className="field-help" href="https://github.com/settings/tokens" target="_blank" rel="noreferrer">Create a GitHub token</a>
                                        <input
                                            type="password"
                                            className="pat-input"
                                            value={githubPatInput}
                                            placeholder="github_pat_..."
                                            onChange={lambda e -> None { githubPatInput = e.target.value; }}
                                        />
                                        <div className="panel-actions">
                                            <button type="button" className="primary-button" onClick={lambda -> None { applyPatAuth(); }}>
                                                Use PAT This Session
                                            </button>
                                            <button type="button" className="secondary-button" onClick={lambda -> None { handleGithubLogin(); }}>
                                                Sign in with GitHub
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            }
                            {githubLogin != "" and installationId == 0 and githubPatToken == "" and
                                <div className="hero-card" style={{"textAlign": "center", "padding": "3rem"}}>
                                    <h2>Install Ringtail on Your Repos</h2>
                                    <p className="hero-subtitle">Ringtail needs access to push branches and open pull requests.</p>
                                    <button className="primary-button" style={{"marginTop": "1.5rem"}} onClick={lambda -> None { handleInstallApp(); }}>
                                        Install GitHub App
                                    </button>
                                </div>
                            }
                            {(githubPatToken != "" or (githubLogin != "" and installationId != 0)) and
                                <div className="demo-layout">
                                    <div className="hero-card">
                                        <h2>Optimize a Repository</h2>
                                        <p className="hero-subtitle">Point Ringtail at a repo, describe what to optimize, and we'll open a PR with the results.</p>
                                        <form className="form-grid" onSubmit={lambda e -> None {
                                            try { e.preventDefault(); } except Exception { ignored = ""; }
                                            submitRepoJob();
                                        }}>
                                            <label className="field field-full">
                                                <span>Repository</span>
                                                {len(availableRepos) > 0 and
                                                    <select value={repoUrl} onChange={lambda e -> None {
                                                        selectedUrl = str(e.target.value);
                                                        repoUrl = selectedUrl;
                                                        autoBranch = _repo_default_branch_for_url(selectedUrl);
                                                        if autoBranch != "" {
                                                            repoBaseBranch = autoBranch;
                                                        }
                                                    }}>
                                                        <option value="">Select a repository...</option>
                                                        {renderRepoOptions()}
                                                    </select>
                                                }
                                                {len(availableRepos) == 0 and
                                                    <input value={repoUrl} placeholder="https://github.com/org/repo" onChange={lambda e -> None { repoUrl = e.target.value; }} />
                                                }
                                            </label>
                                            <label className="field field-full">
                                                <span>Optimization Prompt</span>
                                                <textarea rows={4} value={repoPrompt} onChange={lambda e -> None { repoPrompt = e.target.value; }} />
                                            </label>
                                            <label className="field">
                                                <span>Test Command (optional)</span>
                                                <input value={repoTestCommand} placeholder="python runner.py --check" onChange={lambda e -> None { repoTestCommand = e.target.value; }} />
                                                <span className="field-help">Only runs if you provide it. Ringtail will not infer a test command.</span>
                                            </label>
                                            <label className="field">
                                                <span>Entry Point (required)</span>
                                                <input value={repoEntryPoint} placeholder="python runner.py" onChange={lambda e -> None { repoEntryPoint = e.target.value; }} />
                                                <span className="field-help">Required. Provide the command Ringtail should profile, such as `python runner.py`.</span>
                                            </label>
                                            <label className="field">
                                                <span>Base Branch (optional)</span>
                                                <input value={repoBaseBranch} placeholder="main" onChange={lambda e -> None { repoBaseBranch = e.target.value; }} />
                                                <span className="field-help">Matches CLI `--branch`; if blank, server default is used.</span>
                                            </label>
                                            <label className="field field-full">
                                                <span>Setup Commands (optional, one per line)</span>
                                                <pre className="cli-example">uv sync{"\n"}source .venv/bin/activate{"\n"}python -m pip install -e .</pre>
                                                <textarea className="cli-setup-input" rows={5} value={repoSetupCommands} placeholder="uv sync&#10;source .venv/bin/activate" onChange={lambda e -> None { repoSetupCommands = e.target.value; }} />
                                            </label>
                                            <label className="checkbox-field">
                                                <input type="checkbox" checked={repoPublishPr} onChange={lambda e -> None { repoPublishPr = e.target.checked; }} />
                                                <span>Open a real PR</span>
                                            </label>
                                            <div className="panel-actions field-full">
                                                <button type="submit" className="primary-button" disabled={repoSubmitting or _repo_job_active()}>
                                                    {repoSubmitting and "Submitting..." or _repo_job_active() and "Job In Progress" or "Submit Optimization Job"}
                                                </button>
                                                {_repo_job_active() and not repoSubmitting and
                                                    <button type="button" className="secondary-button" disabled={repoCancelling} onClick={lambda -> None { cancelRepoJob(); }}>
                                                        {repoCancelling and "Cancelling..." or "Cancel job"}
                                                    </button>
                                                }
                                            </div>
                                        </form>
                                    </div>
                                    <div className="hero-card">
                                        <h3>Connection Status</h3>
                                        <div className="simple-list">
                                            <div className="simple-list-item">Auth mode: {githubPatToken != "" and "PAT (session)" or githubLogin != "" and "OAuth session" or "none"}</div>
                                            {githubLogin != "" and <div className="simple-list-item">Signed in as {githubLogin}</div>}
                                            {installationId != 0 and <div className="simple-list-item">Installation ID: {str(installationId)}</div>}
                                            {githubPatToken != "" and <div className="simple-list-item">PAT loaded for this browser session.</div>}
                                            {installAccountLogin != "" and <div className="simple-list-item">Account: {installAccountLogin}</div>}
                                        </div>
                                        {githubPatToken != "" and
                                            <div className="panel-actions" style={{"marginTop": "0.75rem"}}>
                                                <button type="button" className="secondary-button" onClick={lambda -> None { clearPatAuth(); }}>Clear PAT</button>
                                            </div>
                                        }
                                        <div className="log-card">
                                            <div className="log-card-header">
                                                <div>
                                                    <h3>Repository Activity</h3>
                                                    <p className="field-help">Streams async job status plus structured repo-agent events for auth, git push, and pull request creation.</p>
                                                </div>
                                                <button className="secondary-button" onClick={lambda -> None { pollRepoJob(); }}>
                                                    Refresh Status
                                                </button>
                                            </div>
                                            <pre
                                                id="repo-live-activity-log"
                                                data-live-id="repo-live-activity-log"
                                                className="log-feed"
                                                role="log"
                                                aria-live="polite"
                                                style={{"whiteSpace": "pre-wrap", "wordBreak": "break-word"}}
                                                ref={lambda el -> None { if el is not None { _sync_live_activity_dom("repo-live-activity-log", _live_activity_text("repo-live-activity-log", "Submit a repository job to stream worker status and PR publish events.")); } }}
                                            ></pre>
                                        </div>
                                    </div>
                                </div>
                            }
                        </div>
                    }
                </div>
            }

            {activeTab == "repository" and repoExperienceMode == "local" and demoView == "setup" and
                <div className="container" role="tabpanel" aria-labelledby="tab-repository">
                    <div className="demo-layout">
                        <div className="hero-card">
                            <h2>Choose A Benchmark</h2>
                            <p className="hero-subtitle">Pick an engineer-designed benchmark suite, choose how many ranked targets to optimize, and run the demo.</p>
                            <form className="form-grid" onSubmit={lambda e -> None {
                                try { e.preventDefault(); } except Exception { ignored = ""; }
                                startDemoRun();
                            }}>
                                <label className="field field-full">
                                    <span>Benchmark</span>
                                    <select value={demoBenchmarkId} onChange={lambda e -> None { demoBenchmarkId = e.target.value; refreshBenchmarkContext(); }}>
                                        <option value="ranked-pitch-repo">Ranked Pitch Repo</option>
                                    </select>
                                </label>
                                <label className="field">
                                    <span>Top K Final Targets</span>
                                    <input type="number" min="1" step="1" value={demoTopK} onChange={lambda e -> None { demoTopK = e.target.value; }} />
                                </label>
                                <label className="field">
                                    <span>Per-File Finalists</span>
                                    <input type="number" min="1" step="1" value={demoPerFileK} onChange={lambda e -> None { demoPerFileK = e.target.value; }} />
                                </label>
                                <label className="field">
                                    <span>Latest Result Type</span>
                                    <select value={demoLatestBrowseKind} onChange={lambda e -> None { demoLatestBrowseKind = e.target.value; }}>
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
                                <p className="field-help field-full" style={{"marginTop": "0.6rem"}}>
                                    Note: the Live Activity box updates while a benchmark runs via periodic progress polling. If you run benchmarks from the CLI or runner scripts, progress logs will print to your terminal instead.
                                </p>
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

            {activeTab == "repository" and repoExperienceMode == "local" and demoView == "running" and
                <div className="container" role="tabpanel" aria-labelledby="tab-repository">
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
                            <div>
                                <h3>Live Activity</h3>
                            </div>
                            <button className="secondary-button" onClick={lambda -> None { pollDemoProgress(); }}>
                                Refresh Now
                            </button>
                        </div>
                        <pre
                            id="demo-live-log-feed"
                            data-live-id="demo-live-log-feed"
                            className="log-feed"
                            role="log"
                            aria-live="polite"
                            style={{"whiteSpace": "pre-wrap", "wordBreak": "break-word"}}
                            ref={lambda el -> None { if el is not None { _sync_live_activity_dom("demo-live-log-feed", _live_activity_text("demo-live-log-feed", "Live run events will appear here.")); } }}
                        ></pre>
                    </div>
                </div>
            }

            {activeTab == "repository" and repoExperienceMode == "local" and demoView == "results" and
                <div className="container" role="tabpanel" aria-labelledby="tab-repository">
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

            {activeTab == "run_history" and runHistoryPhase == "pick" and
                <div className="container" role="tabpanel" aria-labelledby="tab-run-history">
                    <div className="hero-card">
                        <h2>Run History</h2>
                        <p className="hero-subtitle">Recent async jobs (ui_surface and submission_channel: paste / repo_local / repo_github, and ui / cli / api). Load a run for metrics and a structured run-log tail.</p>
                        {runHistoryError != "" and <div className="info-banner" role="status">{runHistoryError}</div>}
                        <div className="form-grid" style={{"marginTop": "0.75rem"}}>
                            <label className="field">
                                <span>Surface</span>
                                <select value={runHistorySurfaceFilter} onChange={lambda e -> None {
                                    runHistorySurfaceFilter = e.target.value;
                                    runHistorySelectedIndex = 0;
                                    refreshRunHistoryList();
                                }}>
                                    <option value="any">Any</option>
                                    <option value="paste">Paste jobs</option>
                                    <option value="repo_local">Local repo jobs</option>
                                    <option value="repo_github">GitHub repo jobs</option>
                                </select>
                            </label>
                            <label className="field">
                                <span>Status</span>
                                <select value={runHistoryOutcomeFilter} onChange={lambda e -> None {
                                    runHistoryOutcomeFilter = e.target.value;
                                    runHistorySelectedIndex = 0;
                                    refreshRunHistoryList();
                                }}>
                                    <option value="any">Any</option>
                                    <option value="success">Success</option>
                                    <option value="failure">Failure</option>
                                    <option value="other">Other</option>
                                </select>
                            </label>
                            <label className="field field-full">
                                <span>Run (most recent first)</span>
                                <select value={str(runHistorySelectedIndex)} onChange={lambda e -> None {
                                    try { runHistorySelectedIndex = int(e.target.value); } except Exception { runHistorySelectedIndex = 0; }
                                }}>
                                    {renderRunHistorySelectOptions()}
                                </select>
                                <span className="field-help">Rows list surface=… and channel=… for quick scanning.</span>
                            </label>
                            <div className="panel-actions field-full">
                                <button type="button" className="secondary-button" onClick={lambda -> None { refreshRunHistoryList(); }}>Refresh List</button>
                                <button type="button" className="primary-button" onClick={lambda -> None { loadRunHistoryDetail(); }}>Load Run</button>
                            </div>
                        </div>
                    </div>
                </div>
            }

            {activeTab == "run_history" and runHistoryPhase == "detail" and
                <div className="container" role="tabpanel" aria-labelledby="tab-run-history">
                    <div className="results-header">
                        <div>
                            <p className="eyebrow">Run Snapshot</p>
                            <h2>Summary And Logs</h2>
                            <p>{runHistoryMetaLine}</p>
                        </div>
                        <div className="panel-actions">
                            <button className="secondary-button" onClick={lambda -> None { runHistoryBackToPick(); }}>
                                Back To List
                            </button>
                        </div>
                    </div>

                    <div className="stat-grid">
                        <div className="stat-card">
                            <span>UI surface</span>
                            <strong>{runHistoryOriginSurface != "" and runHistoryOriginSurface or "—"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Submission channel</span>
                            <strong>{runHistoryOriginChannel != "" and runHistoryOriginChannel or "—"}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Targets Passed</span>
                            <strong>{runHistoryPassCount}/{runHistoryTargetCount}</strong>
                        </div>
                        <div className="stat-card">
                            <span>Average Speedup</span>
                            <strong>{runHistoryAverageSpeedup}x</strong>
                        </div>
                        <div className="stat-card">
                            <span>Average Time Saved</span>
                            <strong>{runHistoryAverageSaved}%</strong>
                        </div>
                    </div>

                    <div className="demo-layout">
                        <div className="section">
                            <h3>Selected Targets</h3>
                            <div className="simple-list">
                                {runHistorySelected1Visible and
                                    <div className="target-pill">
                                        <strong>{runHistorySelected1Title}</strong>
                                        <span>{runHistorySelected1Meta}</span>
                                    </div>
                                }
                                {runHistorySelected2Visible and
                                    <div className="target-pill">
                                        <strong>{runHistorySelected2Title}</strong>
                                        <span>{runHistorySelected2Meta}</span>
                                    </div>
                                }
                                {runHistorySelected3Visible and
                                    <div className="target-pill">
                                        <strong>{runHistorySelected3Title}</strong>
                                        <span>{runHistorySelected3Meta}</span>
                                    </div>
                                }
                            </div>
                        </div>
                        <div className="section">
                            <h3>Ranking Details</h3>
                            <div className="simple-list">
                                {runHistoryFinalist1Visible and <div className="simple-list-item">{runHistoryFinalist1Text}</div>}
                                {runHistoryFinalist2Visible and <div className="simple-list-item">{runHistoryFinalist2Text}</div>}
                                {runHistoryFinalist3Visible and <div className="simple-list-item">{runHistoryFinalist3Text}</div>}
                                {runHistoryFinalist4Visible and <div className="simple-list-item">{runHistoryFinalist4Text}</div>}
                            </div>
                        </div>
                    </div>

                    {runHistoryOverviewSvg != "" and
                        <div className="hero-card" style={{"marginTop": "1rem"}}>
                            <h3>Suite Overview</h3>
                            <img className="suite-overview" src={"data:image/svg+xml;base64," + runHistoryOverviewSvg} alt="Suite overview" />
                        </div>
                    }

                    <div className="suite-grid" style={{"marginTop": "1rem"}}>
                        {runHistoryCard1Visible and
                            <div className="suite-card">
                                <h3>#1 {runHistoryCard1Title}</h3>
                                <p className="suite-meta">{runHistoryCard1Meta}</p>
                                {runHistoryCard1GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + runHistoryCard1GraphSvg} alt={"Timing graph for " + runHistoryCard1Title} />
                                }
                                <div className="comparison-grid">
                                    <div>
                                        <h4>Original</h4>
                                        <pre className="result-box">{runHistoryCard1Original}</pre>
                                    </div>
                                    <div>
                                        <h4>Optimized</h4>
                                        <pre className="result-box">{runHistoryCard1Optimized}</pre>
                                    </div>
                                </div>
                            </div>
                        }
                        {runHistoryCard2Visible and
                            <div className="suite-card">
                                <h3>#2 {runHistoryCard2Title}</h3>
                                <p className="suite-meta">{runHistoryCard2Meta}</p>
                                {runHistoryCard2GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + runHistoryCard2GraphSvg} alt={"Timing graph for " + runHistoryCard2Title} />
                                }
                                <div className="comparison-grid">
                                    <div>
                                        <h4>Original</h4>
                                        <pre className="result-box">{runHistoryCard2Original}</pre>
                                    </div>
                                    <div>
                                        <h4>Optimized</h4>
                                        <pre className="result-box">{runHistoryCard2Optimized}</pre>
                                    </div>
                                </div>
                            </div>
                        }
                        {runHistoryCard3Visible and
                            <div className="suite-card">
                                <h3>#3 {runHistoryCard3Title}</h3>
                                <p className="suite-meta">{runHistoryCard3Meta}</p>
                                {runHistoryCard3GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + runHistoryCard3GraphSvg} alt={"Timing graph for " + runHistoryCard3Title} />
                                }
                                <div className="comparison-grid">
                                    <div>
                                        <h4>Original</h4>
                                        <pre className="result-box">{runHistoryCard3Original}</pre>
                                    </div>
                                    <div>
                                        <h4>Optimized</h4>
                                        <pre className="result-box">{runHistoryCard3Optimized}</pre>
                                    </div>
                                </div>
                            </div>
                        }
                    </div>

                    <div className="log-card" style={{"marginTop": "1.25rem"}}>
                        <div className="log-card-header">
                            <div>
                                <h3>Run Log</h3>
                                <p className="field-help">Structured tail of the JSONL run log plus job context lines from the server.</p>
                            </div>
                        </div>
                        <pre
                            id="run-history-log-feed"
                            data-live-id="run-history-log-feed"
                            className="log-feed"
                            role="log"
                            aria-live="polite"
                            style={{"whiteSpace": "pre-wrap", "wordBreak": "break-word"}}
                            ref={lambda el -> None { if el is not None { _sync_live_activity_dom("run-history-log-feed", _live_activity_text("run-history-log-feed", "Load a run to show structured log tail and job lines here.")); } }}
                        ></pre>
                    </div>
                </div>
            }

            {activeTab == "cli" and
                <div className="container" role="tabpanel" aria-labelledby="tab-cli">
                    <div className="hero-card">
                        <h2>Install And Run Ringtail CLI</h2>
                        <p className="hero-subtitle">Follow the steps below to clone, install, and start running optimization workflows locally.</p>
                    </div>

                    <div className="stage-grid" style={{"marginTop": "1.5rem"}}>
                        <div className="stage-card active">
                            <span>1</span>
                            <h3>Clone & Install</h3>
                            <p>Set up a virtual environment and install dependencies.</p>
                        </div>
                        <div className="stage-card">
                            <span>2</span>
                            <h3>Start The App</h3>
                            <p>Launch the Jac server and open the dashboard.</p>
                        </div>
                        <div className="stage-card">
                            <span>3</span>
                            <h3>Run CLI Commands</h3>
                            <p>Use the Python CLI for headless optimization workflows.</p>
                        </div>
                    </div>

                    <div className="hero-card" style={{"marginTop": "0.5rem"}}>
                        <h3>Step 1 — Clone & Install</h3>
                        <pre className="result-box" style={{"marginTop": "0.75rem"}}>git clone https://github.com/your-org/ringtail.git
cd ringtail
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .</pre>
                    </div>

                    <div className="demo-layout" style={{"marginTop": "1.25rem"}}>
                        <div className="hero-card">
                            <h3>Step 2 — Start The App</h3>
                            <pre className="result-box" style={{"marginTop": "0.75rem"}}>jac start main.jac
# then open the local URL shown in terminal</pre>
                        </div>
                        <div className="hero-card">
                            <h3>Step 3 — CLI Workflows</h3>
                            <pre className="result-box" style={{"marginTop": "0.75rem"}}>python -m src.ringtail_cli --help
python -m src.ringtail_cli optimize --help
jac test tests/unit/</pre>
                        </div>
                    </div>

                    <div className="hero-card" style={{"marginTop": "1.25rem"}}>
                        <h3>FAQ / Troubleshooting</h3>
                        <div className="simple-list" style={{"marginTop": "0.75rem"}}>
                            <div className="simple-list-item">If Jac commands fail, confirm `jac --version` and reinstall `jaseci` in your active environment.</div>
                            <div className="simple-list-item">If LLM calls fail, verify `RINGTAIL_OPENAI_API_KEY` and/or `RINGTAIL_ANTHROPIC_API_KEY` are present in env.</div>
                            <div className="simple-list-item">If tests fail after dependency changes, recreate the virtual environment and reinstall editable package mode.</div>
                        </div>
                    </div>
                </div>
            }
        </div>
    ;
}
# --- Walker (test / demo) ----------------------------------------------------
walker test_walker {
    has message: str = "Walker is working";

    can with entry {
        report {"walker_message": self.message, "status": "ok"};
    }
}

# Main entry point for direct execution (jac run)
with entry {
    print("Ringtail initialized");
    print("Ready to optimize code!");
}
