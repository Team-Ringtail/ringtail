"""
Agent configuration settings and named profiles.
"""

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


"""Return an AgentConfig instance for a given named profile.

Profiles:
  - "default": heuristic-only (no LLM model configured).
  - "candidate-search": heuristic-only with two candidate rewrites per iteration.
  - "test-fast": low-cost heuristic profile for local/unit tests.
  - "test-fast-candidate-search": low-cost test profile with two candidates.
  - "anthropic-sonnet": enables LLM planning/codegen using Claude Sonnet,
    with conservative iteration limits to control cost.
"""
def:pub get_agent_config(
    name: str | None = None
) -> AgentConfig {
    cfg = AgentConfig();

    if name is None or name == "" or name == "default" {
        cfg.name = "default";
        return cfg;
    }

    if name == "candidate-search" {
        cfg.name = "candidate-search";
        cfg.candidate_count = 2;
        cfg.stop_on_test_failure = False;
        return cfg;
    }

    if name == "test-fast" {
        cfg.name = "test-fast";
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

    if name == "anthropic-sonnet" {
        cfg.name = "anthropic-sonnet";
        cfg.llm_model = "claude-sonnet-4-20250514";
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
