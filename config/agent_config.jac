"""
Agent configuration settings and named profiles.
"""

import os;

node AgentConfig {
    has name: str = "default";
    has max_iterations: int = 3;
    has llm_model: str = "";
    has temperature: float = 0.1;
    has candidate_count: int = 1;
    has benchmark_min_rounds: int = 10;
    has benchmark_warmup: bool = True;
    has property_test_max_examples: int = 50;
    has run_property_tests: bool = True;

    # Loop policy configuration
    has max_no_improvement_iters: int = 3;
    has stop_on_test_failure: bool = True;
    has min_improvement_ratio: float = 1.0;
}


def:pub resolve_default_llm_model(
    llm_model: str | None = None
) -> str {
    if llm_model is not None and str(llm_model) != "" {
        return str(llm_model);
    }
    env_model = os.environ.get("RINGTAIL_DEFAULT_LLM_MODEL", "");
    if env_model != "" {
        return env_model;
    }
    return "claude-opus-4-6";
}


"""Return an AgentConfig instance for a given named profile.

Profiles:
  - "default": shipped Anthropic Opus profile.
  - "heuristic": legacy profile name; no longer provides a silent fallback optimizer.
  - "candidate-search": LLM-backed two-candidate search profile.
  - "live-fast": fast live LLM profile for local smoke/demo runs.
  - "test-fast": low-cost explicit mock profile for local/unit tests.
  - "test-fast-candidate-search": low-cost test profile with two candidates.
  - "anthropic-sonnet": compatibility alias for the shipped Anthropic default.
  - "anthropic-opus": explicit Anthropic Opus profile.
"""
def:pub get_agent_config(
    name: str | None = None
) -> AgentConfig {
    cfg = AgentConfig();

    if name == "heuristic" {
        cfg.name = "heuristic";
        cfg.llm_model = "";
        return cfg;
    }

    if name is None or name == "" or name == "default" {
        cfg.name = "default";
        cfg.llm_model = resolve_default_llm_model(None);
        return cfg;
    }

    if name == "candidate-search" {
        cfg.name = "candidate-search";
        cfg.llm_model = resolve_default_llm_model(None);
        cfg.candidate_count = 2;
        cfg.stop_on_test_failure = False;
        return cfg;
    }

    if name == "live-fast" {
        cfg.name = "live-fast";
        cfg.llm_model = resolve_default_llm_model(None);
        cfg.max_iterations = 2;
        cfg.max_no_improvement_iters = 1;
        cfg.candidate_count = 1;
        cfg.benchmark_min_rounds = 2;
        cfg.benchmark_warmup = False;
        cfg.property_test_max_examples = 12;
        cfg.stop_on_test_failure = False;
        return cfg;
    }

    if name == "test-fast" {
        cfg.name = "test-fast";
        cfg.llm_model = "__ringtail_test_mock__";
        cfg.max_iterations = 1;
        cfg.max_no_improvement_iters = 1;
        cfg.benchmark_min_rounds = 1;
        cfg.benchmark_warmup = False;
        cfg.property_test_max_examples = 8;
        cfg.run_property_tests = False;
        return cfg;
    }

    if name == "test-fast-candidate-search" {
        cfg.name = "test-fast-candidate-search";
        cfg.llm_model = "__ringtail_test_mock__";
        cfg.max_iterations = 1;
        cfg.max_no_improvement_iters = 1;
        cfg.candidate_count = 2;
        cfg.stop_on_test_failure = False;
        cfg.benchmark_min_rounds = 1;
        cfg.benchmark_warmup = False;
        cfg.property_test_max_examples = 8;
        cfg.run_property_tests = False;
        return cfg;
    }

    if name == "anthropic-sonnet" or name == "anthropic-opus" {
        cfg.name = str(name);
        cfg.llm_model = resolve_default_llm_model(None);
        # Slightly lower iteration counts by default when using LLMs.
        cfg.max_iterations = 3;
        cfg.max_no_improvement_iters = 2;
        cfg.candidate_count = 2;
        # Let the loop retry with failure feedback instead of stopping immediately.
        cfg.stop_on_test_failure = False;
        return cfg;
    }

    # Fallback: unknown names behave like default but keep the name for diagnostics.
    cfg.name = str(name if name is not None else "");
    return cfg;
}
