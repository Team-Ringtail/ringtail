"""Execution backend abstraction for running profiling / testing workloads.

Provides a uniform interface so callers can run code either locally
(subprocess) or in isolated Blaxel sandboxes without changing their logic.
"""

import json;
import os;
import subprocess;
import sys;
import tempfile;
import asyncio;
import from typing { Any, Dict, Optional }


"""Abstract interface for running a Python script with supporting files."""
class ExecutionBackend {
    def run_script(
        self: ExecutionBackend,
        script_name: str,
        files: dict,
        timeout: int = 30,
        pip_deps: list = None
    ) -> dict abs;
}


"""Runs scripts in a local subprocess + temp directory."""
class LocalBackend(ExecutionBackend) {
    def run_script(
        self: LocalBackend,
        script_name: str,
        files: dict,
        timeout: int = 30,
        pip_deps: list = None
    ) -> dict {
        tmp_dir = tempfile.mkdtemp(prefix="ringtail_local_");

        try {
            for (fname, contents) in files.items() {
                path = os.path.join(tmp_dir, fname);
                os.makedirs(os.path.dirname(path), exist_ok=True);
                with open(path, "w") as f {
                    f.write(contents);
                }
            }

            if pip_deps {
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet"] + pip_deps,
                    capture_output=True,
                    timeout=120
                );
            }

            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp_dir
            );

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0
            };

        } except subprocess.TimeoutExpired {
            return {
                "stdout": "",
                "stderr": "Timed out after %ds" % timeout,
                "returncode": -1,
                "success": False
            };
        } except Exception as e {
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False
            };
        } finally {
            _cleanup_dir(tmp_dir);
        }
    }
}


"""Runs scripts inside Blaxel sandbox microVMs.

Requires the blaxel SDK (pip install blaxel) and a valid
API key environment variable (managed via Infisical).
"""
class BlaxelBackend(ExecutionBackend) {
    has workspace: str;
    has image: str = "python:3.12-slim";
    has memory_mb: int = 2048;
    has region: str = None;

    def run_script(
        self: BlaxelBackend,
        script_name: str,
        files: dict,
        timeout: int = 30,
        pip_deps: list = None
    ) -> dict {
        try {
            return asyncio.get_event_loop().run_until_complete(
                self._run_async(script_name, files, timeout, pip_deps)
            );
        } except RuntimeError {
            loop = asyncio.new_event_loop();
            try {
                return loop.run_until_complete(
                    self._run_async(script_name, files, timeout, pip_deps)
                );
            } finally {
                loop.close();
            }
        }
    }

    async def _run_async(
        self: BlaxelBackend,
        script_name: str,
        files: dict,
        timeout: int,
        pip_deps: list
    ) -> dict {
        try {
            from blaxel.core import SandboxInstance;
        } except ImportError {
            return {
                "stdout": "",
                "stderr": "blaxel SDK not installed. Run: pip install blaxel",
                "returncode": -1,
                "success": False
            };
        }

        sandbox = None;
        try {
            create_opts = {
                "name": "ringtail-%s" % os.urandom(4).hex(),
                "image": self.image,
                "memory": self.memory_mb
            };
            if self.region {
                create_opts["region"] = self.region;
            }

            sandbox = await SandboxInstance.create(create_opts);

            for (fname, contents) in files.items() {
                await sandbox.fs.write("/workspace/%s" % fname, contents);
            }

            if pip_deps {
                await sandbox.process.exec(
                    {"command": "pip install --quiet " + " ".join(pip_deps),
                     "wait_for_completion": True,
                     "timeout": 120000}
                );
            }

            process = await sandbox.process.exec(
                {"command": "cd /workspace && python %s" % script_name,
                 "working_dir": "/workspace",
                 "wait_for_completion": True,
                 "timeout": timeout * 1000}
            );

            stdout = getattr(process, "stdout", "") or "";
            stderr = getattr(process, "stderr", "") or "";
            logs_obj = getattr(process, "logs", None);
            if logs_obj {
                stdout = getattr(logs_obj, "stdout", stdout) or stdout;
                stderr = getattr(logs_obj, "stderr", stderr) or stderr;
            }
            returncode = getattr(process, "exit_code", None);
            if returncode is None {
                returncode = getattr(process, "exitCode", -1);
            }

            return {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "success": returncode == 0
            };

        } except Exception as e {
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False
            };
        }
    }
}


"""Check all common env var names for the Blaxel API key."""
def _resolve_api_key() -> str {
    return (
        os.environ.get("blaxel_api_key", "")
        or os.environ.get("BLAXEL_API_KEY", "")
        or os.environ.get("BL_API_KEY", "")
    );
}


"""Factory: return BlaxelBackend if configured, else LocalBackend."""
def get_backend(config: dict = None) -> ExecutionBackend {
    cfg = config;
    if cfg is None {
        cfg = {};
    }

    backend_type = cfg.get("backend", "local");

    if backend_type == "blaxel" {
        api_key = _resolve_api_key();
        if not api_key {
            raise EnvironmentError(
                "Blaxel API key not set. Add blaxel_api_key to Infisical "
                "or set BL_API_KEY in your environment."
            );
        }
        return BlaxelBackend(
            workspace=cfg.get("workspace", ""),
            image=cfg.get("image", "sandbox/ringtail-python:yjetxvb6idjq"),
            memory_mb=cfg.get("memory_mb", 2048),
            region=cfg.get("region")
        );
    }

    return LocalBackend();
}


"""Remove a temp directory tree."""
def _cleanup_dir(path: str) -> None {
    for (dirpath, dirs, files) in os.walk(path, topdown=False) {
        for f in files {
            try {
                os.remove(os.path.join(dirpath, f));
            } except OSError {
                ;
            }
        }
        for d in dirs {
            try {
                os.rmdir(os.path.join(dirpath, d));
            } except OSError {
                ;
            }
        }
    }
    try {
        os.rmdir(path);
    } except OSError {
        ;
    }
}
