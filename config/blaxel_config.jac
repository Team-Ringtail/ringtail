"""Blaxel sandbox configuration.

Reads connection settings from environment variables (populated by Infisical
or .env at runtime). No secrets are stored in code or config files.

Infisical secret names expected:
  - blaxel_api_key   -> maps to BL_API_KEY env var
  - blaxel_workspace -> maps to BL_WORKSPACE env var (or BLAXEL_WORKSPACE)
"""

import os;
import from typing { Optional }


def _get_api_key() -> str {
    """Resolve the Blaxel API key from any of the common env var names."""
    return (
        os.environ.get("blaxel_api_key", "")
        or os.environ.get("BLAXEL_API_KEY", "")
        or os.environ.get("BL_API_KEY", "")
    );
}


def _get_workspace() -> str {
    """Resolve the Blaxel workspace from any of the common env var names."""
    return (
        os.environ.get("blaxel_workspace", "")
        or os.environ.get("BLAXEL_WORKSPACE", "")
        or os.environ.get("BL_WORKSPACE", "")
    );
}


obj BlaxelConfig {
    has workspace: str = "";
    has default_image: str = "python:3.12-slim";
    has default_memory_mb: int = 2048;
    has region: Optional[str] = None;
    has max_parallel_sandboxes: int = 10;
    has sandbox_ttl_seconds: int = 300;
}


def blaxel_config_from_env() -> BlaxelConfig {
    """Build config from environment variables (set by Infisical)."""
    return BlaxelConfig(
        workspace=_get_workspace(),
        default_image=os.environ.get("BL_IMAGE", "python:3.12-slim"),
        default_memory_mb=int(os.environ.get("BL_MEMORY_MB", "2048")),
        region=os.environ.get("BL_REGION") or None,
        max_parallel_sandboxes=int(os.environ.get("BL_MAX_PARALLEL", "10")),
        sandbox_ttl_seconds=int(os.environ.get("BL_SANDBOX_TTL", "300"))
    );
}


def blaxel_is_configured(config: BlaxelConfig) -> bool {
    """True when both API key and workspace are present."""
    return bool(config.workspace) and bool(_get_api_key());
}


def blaxel_to_backend_dict(config: BlaxelConfig) -> dict {
    """Return the dict expected by sandbox_runner.get_backend."""
    if not blaxel_is_configured(config) {
        return {"backend": "local"};
    }
    return {
        "backend": "blaxel",
        "workspace": config.workspace,
        "image": config.default_image,
        "memory_mb": config.default_memory_mb,
        "region": config.region
    };
}
