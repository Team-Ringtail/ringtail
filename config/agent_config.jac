"""
Agent configuration settings
"""

node AgentConfig {
    has name: str = "default";
    has max_iterations: int = 3;
    has llm_model: str = "";
    has temperature: float = 0.1;

    # Loop policy configuration
    has max_no_improvement_iters: int = 3;
    has stop_on_test_failure: bool = True;
    has min_improvement_ratio: float = 1.0;
}
