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

# Walker example - also becomes a REST endpoint at /walker/test_walker  
walker test_walker {
    has message: str = "Walker is working";
    
    can with entry {
        report {"walker_message": self.message, "status": "ok"};
    }
}

# Client-side home page component
cl def:pub app -> JsxElement {
    has healthStatus: dict = {};
    has activeMode: str = "repo";
    has repoUrl: str = "";
    has repoPrompt: str = "make this faster";
    has repoBranch: str = "main";
    has repoBackend: str = "local";
    has repoPublishPr: bool = False;
    has repoTestCommand: str = "";
    has repoSetupCommands: str = "";
    has repoMaxTargets: str = "3";
    has currentJobId: str = "";
    has repoJobStatus: dict = {};
    has repoJobText: str = "No repo job submitted yet.";
    has functionFilePath: str = "";
    has functionName: str = "";
    has functionCall: str = "";
    has functionTestsRoot: str = "tests";
    has functionResultText: str = "No function optimization run yet.";
    has authReadinessText: str = "";
    has doctorText: str = "";
    has recentJobsText: str = "";
    has preflightText: str = "";
    has uiMessage: str = "";

    def _bool_text(value: bool) -> str {
        if value {
            return "yes";
        }
        return "no";
    }

    def _format_dict(data: dict) -> str {
        lines: list = [];
        for key in data.keys() {
            lines.append(str(key) + ": " + str(data[key]));
        }
        return "\\n".join(lines);
    }

    def _format_jobs(jobs: list) -> str {
        lines: list = [];
        for job in jobs {
            lines.append(
                str(job.get("job_id", "")) + " | "
                + str(job.get("status", "")) + " | "
                + str(job.get("request_summary", {}).get("operation", ""))
            );
        }
        if len(lines) == 0 {
            return "No jobs recorded yet.";
        }
        return "\\n".join(lines);
    }

    async def refreshStatus() -> None {
        authData = await get_auth_readiness();
        doctorData = await get_config_doctor();
        recentJobs = await get_recent_jobs(8);
        authReadinessText = _format_dict({
            "auth_mode": str(authData.get("auth_mode", "none")),
            "installation_id": str(authData.get("installation_id", "")),
            "blaxel_configured": _bool_text(bool(authData.get("blaxel_configured", False))),
            "repo_agent_config_present": _bool_text(bool(authData.get("repo_agent_config_present", False))),
            "install_url": str(authData.get("github_app", {}).get("install_url", "")),
            "missing": str(authData.get("github_app", {}).get("missing", []))
        });
        doctorText = _format_dict({
            "ok": _bool_text(bool(doctorData.get("ok", False))),
            "issues": str(doctorData.get("issues", [])),
            "jac": str(doctorData.get("checks", {}).get("jac", {}).get("path", "")),
            "git": str(doctorData.get("checks", {}).get("git", {}).get("path", "")),
            "openssl": str(doctorData.get("checks", {}).get("openssl", {}).get("path", "")),
            "jobs_dir": str(doctorData.get("jobs_dir", ""))
        });
        recentJobsText = _format_jobs(recentJobs);
    }

    async def submitRepoJob(e: any) -> None {
        e.preventDefault();
        setupCommands: list = [];
        if repoSetupCommands.strip() != "" {
            for rawLine in repoSetupCommands.split("\\n") {
                if rawLine.strip() != "" {
                    setupCommands.append(rawLine.strip());
                }
            }
        }
        payload = {
            "repo_url": repoUrl,
            "base_branch": repoBranch,
            "prompt": repoPrompt,
            "test_command": repoTestCommand if repoTestCommand.strip() != "" else None,
            "setup_commands": setupCommands,
            "max_targets": int(repoMaxTargets),
            "publish_pr": repoPublishPr,
            "backend_config": {"backend": repoBackend}
        };
        uiMessage = "Submitting repo job...";
        submitted = await submit_repo_agent_job(payload);
        currentJobId = str(submitted.get("job_id", ""));
        repoJobStatus = submitted;
        repoJobText = _format_dict(submitted);
        uiMessage = "Repo job submitted.";
        await refreshStatus();
    }

    async def pollRepoJob() -> None {
        if currentJobId == "" {
            uiMessage = "No repo job id to poll yet.";
            return;
        }
        status = await get_repo_agent_job(currentJobId);
        repoJobStatus = status;
        repoJobText = _format_dict(status);
        uiMessage = "Repo job status refreshed.";
        await refreshStatus();
    }

    async def runFileOptimize(e: any) -> None {
        e.preventDefault();
        payload = {
            "operation": "optimize_file_function",
            "file_path": functionFilePath,
            "function_name": functionName,
            "function_call": functionCall if functionCall.strip() != "" else None,
            "tests_root": functionTestsRoot
        };
        uiMessage = "Running function optimization...";
        result = await optimize_sync(payload);
        functionResultText = _format_dict(result);
        uiMessage = "Function optimization completed.";
    }

    async def runRepoPreflight() -> None {
        if repoUrl.strip() == "" {
            preflightText = "Enter a repo path or GitHub URL first.";
            return;
        }
        result = await verify_github_repo_access({"repo_url": repoUrl});
        preflightText = _format_dict(result);
    }

    async can with entry {
        try {
            healthStatus = await health();
            await refreshStatus();
        } except Exception as e {
            healthStatus = {"status": "error", "message": str(e)};
            uiMessage = str(e);
        }
    }
    
    return 
        <div className="container">
            <div className="header">
                <h1>Ringtail</h1>
                <p>AI Agent-Based Code Optimizer</p>
                <span className="version">v0.1.0</span>
                {healthStatus.get("status") == "healthy" and <div className="status-badge">Service Healthy</div>}
            </div>

            {uiMessage != "" and <div className="info-banner">{uiMessage}</div>}

            <div className="mode-switch">
                <button className={activeMode == "repo" and "mode-button active" or "mode-button"} onClick={lambda -> None { activeMode = "repo"; }}>
                    Repo Agent
                </button>
                <button className={activeMode == "function" and "mode-button active" or "mode-button"} onClick={lambda -> None { activeMode = "function"; }}>
                    Function Optimize
                </button>
            </div>

            <div className="dashboard-grid">
                <div className="section">
                    <h2>Auth And Config</h2>
                    <div className="panel-actions">
                        <button className="secondary-button" onClick={lambda -> None { refreshStatus(); }}>Refresh</button>
                    </div>
                    <pre className="result-box">{authReadinessText}</pre>
                    <pre className="result-box">{doctorText}</pre>
                </div>

                <div className="section">
                    <h2>Recent Jobs</h2>
                    <pre className="result-box">{recentJobsText}</pre>
                </div>
            </div>

            {activeMode == "repo" and
                <div className="section">
                    <h2>Repo Agent</h2>
                    <form className="form-grid" onSubmit={lambda e: any -> None { submitRepoJob(e); }}>
                        <label className="field">
                            <span>Repo URL or Local Path</span>
                            <input value={repoUrl} onChange={lambda e: any -> None { repoUrl = e.target.value; }} placeholder="/path/to/repo or https://github.com/org/repo" />
                        </label>
                        <label className="field">
                            <span>Base Branch</span>
                            <input value={repoBranch} onChange={lambda e: any -> None { repoBranch = e.target.value; }} />
                        </label>
                        <label className="field field-full">
                            <span>Prompt</span>
                            <textarea value={repoPrompt} onChange={lambda e: any -> None { repoPrompt = e.target.value; }} rows={4}></textarea>
                        </label>
                        <label className="field">
                            <span>Backend</span>
                            <select value={repoBackend} onChange={lambda e: any -> None { repoBackend = e.target.value; }}>
                                <option value="local">local</option>
                                <option value="blaxel">blaxel</option>
                            </select>
                        </label>
                        <label className="field">
                            <span>Max Targets</span>
                            <input value={repoMaxTargets} onChange={lambda e: any -> None { repoMaxTargets = e.target.value; }} />
                        </label>
                        <label className="field field-full">
                            <span>Test Command (optional)</span>
                            <input value={repoTestCommand} onChange={lambda e: any -> None { repoTestCommand = e.target.value; }} placeholder="python -m pytest tests" />
                        </label>
                        <label className="field field-full">
                            <span>Setup Commands (optional, one per line)</span>
                            <textarea value={repoSetupCommands} onChange={lambda e: any -> None { repoSetupCommands = e.target.value; }} rows={4}></textarea>
                        </label>
                        <label className="checkbox-field field-full">
                            <input type="checkbox" checked={repoPublishPr} onChange={lambda e: any -> None { repoPublishPr = bool(e.target.checked); }} />
                            <span>Publish PR when successful</span>
                        </label>
                        <div className="panel-actions field-full">
                            <button type="button" className="secondary-button" onClick={lambda -> None { runRepoPreflight(); }}>
                                Verify Repo Access
                            </button>
                            <button type="button" className="secondary-button" onClick={lambda -> None { pollRepoJob(); }}>
                                Poll Current Job
                            </button>
                            <button type="submit" className="primary-button">Submit Repo Job</button>
                        </div>
                    </form>
                    <h3>Preflight</h3>
                    <pre className="result-box">{preflightText}</pre>
                    <h3>Current Repo Job</h3>
                    <pre className="result-box">{repoJobText}</pre>
                </div>
            }

            {activeMode == "function" and
                <div className="section">
                    <h2>Function Optimize</h2>
                    <form className="form-grid" onSubmit={lambda e: any -> None { runFileOptimize(e); }}>
                        <label className="field field-full">
                            <span>File Path</span>
                            <input value={functionFilePath} onChange={lambda e: any -> None { functionFilePath = e.target.value; }} placeholder="/absolute/path/to/file.py" />
                        </label>
                        <label className="field">
                            <span>Function Name</span>
                            <input value={functionName} onChange={lambda e: any -> None { functionName = e.target.value; }} />
                        </label>
                        <label className="field">
                            <span>Tests Root</span>
                            <input value={functionTestsRoot} onChange={lambda e: any -> None { functionTestsRoot = e.target.value; }} />
                        </label>
                        <label className="field field-full">
                            <span>Function Call (optional)</span>
                            <input value={functionCall} onChange={lambda e: any -> None { functionCall = e.target.value; }} placeholder="my_func(10)" />
                        </label>
                        <div className="panel-actions field-full">
                            <button type="submit" className="primary-button">Optimize Function</button>
                        </div>
                    </form>
                    <h3>Function Result</h3>
                    <pre className="result-box">{functionResultText}</pre>
                </div>
            }

            <div className="section">
                <h2>How It Works</h2>
                <div className="features">
                    <div className="feature-card">
                        <h3>Repo Agent</h3>
                        <p>Submit a repo path or GitHub URL with a natural-language prompt, then poll the async job until it returns a PR preview or published PR.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Function Optimize</h3>
                        <p>Run the existing function optimizer on a specific file and function without writing raw request JSON by hand.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Config Doctor</h3>
                        <p>Check local prerequisites, auth readiness, and recent jobs from the same local UI before kicking off expensive work.</p>
                    </div>
                </div>
            </div>

            <div className="footer">
                <p>Built with Jaseci • AI-Native Full-Stack Development</p>
                <p style={{"marginTop": "0.5rem", "fontSize": "0.9rem", "color": "#888"}}>
                    EECS 449 Project • University of Michigan
                </p>
            </div>
        </div>
    ;
}

# Main entry point for direct execution (jac run)
with entry {
    print("Ringtail initialized");
    print("Ready to optimize code!");
}
