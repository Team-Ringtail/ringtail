# Ringtail - AI Agent-Based Code Optimizer
# Main application entry point

import from uuid { uuid4 }
import importlib;

import from interfaces.cli.cli { run_optimization_request }
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
    has demoView: str = "setup";
    has demoServerUrl: str = "";
    has demoBenchmarkId: str = "ranked-pitch-repo";
    has demoBenchmarkText: str = "";
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
        result = await get_latest_ranked_demo_suite();
        if bool(_value(result, "success", False)) or "summary" in result {
            _apply_demo_result(result);
            demoRunStatus = "succeeded";
            demoRunStage = "Showing latest verified benchmark run";
            demoProgressPct = 100;
            demoView = "results";
        } else {
            uiMessage = str(_value(result, "error", "Could not load latest benchmark result"));
        }
    }

    async def startDemoRun(e: any) -> None {
        e.preventDefault();
        demoJobId = str(uuid4());
        demoView = "running";
        demoRunStatus = "queued";
        demoRunStage = "Submitting benchmark run";
        demoProgressPct = 6;
        demoLogText = "Submitting benchmark run...";
        uiMessage = "";
        _clear_demo_cards();
        demoOverviewSvg = "";
        payload = {
            "operation": "run_ranked_demo_suite",
            "job_id": demoJobId,
            "server_url": demoServerUrl,
            "benchmark_id": demoBenchmarkId,
            "top_k": int(demoTopK),
            "per_file_k": int(demoPerFileK)
        };
        await submit_optimization_job(payload);
        await pollDemoProgress();
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
            if demoServerUrl == "" {
                demoServerUrl = str(globalThis.location.origin);
            }
            healthStatus = await health();
            await refreshBenchmarkContext();
            if not pollingInitialized {
                pollingInitialized = True;
                globalThis.setInterval(lambda -> None { tickDemoPolling(); }, 3000);
            }
        } except Exception as e {
            healthStatus = {"status": "error", "message": str(e)};
            uiMessage = str(e);
        }
    }

    return
        <div className="demo-shell">
            <div className="demo-hero">
                <div className="demo-hero-copy">
                    <span className="version">v0.1.0</span>
                    <h1>Ringtail Benchmark Studio</h1>
                    <p>Run a curated optimization benchmark, watch Ringtail work in real time, and review the selected targets with measured speedups.</p>
                </div>
                {_value(healthStatus, "status", "") == "healthy" and <div className="status-badge">Service Healthy</div>}
            </div>

            {uiMessage != "" and <div className="info-banner">{uiMessage}</div>}

            {demoView == "setup" and
                <div className="container">
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
                                    <input value={demoTopK} onChange={lambda e: any -> None { demoTopK = e.target.value; }} />
                                </label>
                                <label className="field">
                                    <span>Per-File Finalists</span>
                                    <input value={demoPerFileK} onChange={lambda e: any -> None { demoPerFileK = e.target.value; }} />
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

            {demoView == "running" and
                <div className="container">
                    <div className="run-stage-card">
                        <div className="run-stage-copy">
                            <p className="eyebrow">Benchmark Running</p>
                            <h2>{demoRunStage}</h2>
                            <p>Status: {demoRunStatus}</p>
                        </div>
                        <div className="progress-meter">
                            <div className="progress-track">
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
                        <pre className="log-feed">{demoLogText}</pre>
                    </div>
                </div>
            }

            {demoView == "results" and
                <div className="container">
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
                            <button className="primary-button" onClick={lambda -> None { resetToSetup(); }}>
                                Run Another Benchmark
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
                            <img className="suite-graph" src={"data:image/svg+xml;base64," + demoOverviewSvg} />
                        </div>
                    }

                    <div className="suite-card-grid">
                        {demoCard1Visible and
                            <div className="suite-card">
                                <h3>#1 {demoCard1Title}</h3>
                                <p className="suite-meta">{demoCard1Meta}</p>
                                {demoCard1GraphSvg != "" and
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + demoCard1GraphSvg} />
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
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + demoCard2GraphSvg} />
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
                                    <img className="suite-graph" src={"data:image/svg+xml;base64," + demoCard3GraphSvg} />
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
