# Ringtail - AI Agent-Based Code Optimizer
# Main application entry point

import from uuid { uuid4 }
cl import "./styles.css";

# Public functions become REST endpoints automatically with jac start
def:pub health -> dict {
    return {"status": "healthy", "service": "ringtail", "version": "0.1.0"};
}

def:pub hello(name: str = "Ringtail") -> dict {
    return {"message": f"Hello from {name}!", "status": "ok"};
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
    
    async can with entry {
        try {
            healthStatus = await health();
        } except Exception as e {
            healthStatus = {"status": "error", "message": str(e)};
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
            
            <div className="section">
                <h2>Overview</h2>
                <p style={{"fontSize": "1.1rem", "lineHeight": "1.6", "color": "#555", "marginBottom": "1rem"}}>
                    Ringtail is an intelligent code optimization system that uses AI agents in an iterative loop to improve code quality, 
                    performance, and maintainability. The system analyzes your code, generates optimized versions, validates them through 
                    unit testing and profiling, and iterates until optimal results are achieved.
                </p>
                <p style={{"fontSize": "1rem", "lineHeight": "1.6", "color": "#666"}}>
                    You can optimize individual functions, entire codebases, or link GitHub repositories for batch processing. 
                    Define custom optimization criteria including performance targets, code quality metrics, and functionality requirements.
                </p>
            </div>
            
            <div className="section">
                <h2>How It Works</h2>
                <div className="features">
                    <div className="feature-card">
                        <h3>Analysis Phase</h3>
                        <p>The agent analyzes the target code and estimates potential optimizations, identifying bottlenecks, 
                        inefficiencies, and areas for improvement based on your specified criteria.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Optimization Loop</h3>
                        <p>Think → Write → Test → Profile → Compare → Iterate. The agent generates optimized code, 
                        validates functionality with unit tests, profiles performance, and compares against estimated limits.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Validation & Testing</h3>
                        <p>Each optimization is validated through comprehensive unit testing to ensure correctness, 
                        followed by profiling to measure actual performance improvements.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Benchmarking</h3>
                        <p>Compare optimized code metrics against standalone top agents (Claude, GPT-4, etc.) and baseline 
                        performance using GitHub repositories and LeetCode problems as test cases.</p>
                    </div>
                </div>
            </div>
            
            <div className="section">
                <h2>Interfaces</h2>
                <div style={{"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))", "gap": "1rem", "marginTop": "1rem"}}>
                    <div className="endpoint-card">
                        <h3 style={{"marginBottom": "0.5rem", "color": "#333"}}>Command Line</h3>
                        <p style={{"fontSize": "0.9rem", "color": "#666"}}>Direct function optimization via CLI interface</p>
                    </div>
                    <div className="endpoint-card">
                        <h3 style={{"marginBottom": "0.5rem", "color": "#333"}}>Web Interface</h3>
                        <p style={{"fontSize": "0.9rem", "color": "#666"}}>Paste functions or code snippets for optimization</p>
                    </div>
                    <div className="endpoint-card">
                        <h3 style={{"marginBottom": "0.5rem", "color": "#333"}}>Python Decorators</h3>
                        <p style={{"fontSize": "0.9rem", "color": "#666"}}>Use @optimize decorator for seamless integration</p>
                    </div>
                    <div className="endpoint-card">
                        <h3 style={{"marginBottom": "0.5rem", "color": "#333"}}>GitHub Integration</h3>
                        <p style={{"fontSize": "0.9rem", "color": "#666"}}>Link repositories for batch optimization</p>
                    </div>
                </div>
            </div>
            
            <div className="section">
                <h2>Optimization Criteria</h2>
                <p style={{"fontSize": "1rem", "lineHeight": "1.6", "color": "#666", "marginBottom": "1rem"}}>
                    Define what you want to optimize:
                </p>
                <ul style={{"paddingLeft": "1.5rem", "lineHeight": "1.8", "color": "#555"}}>
                    <li><strong>Performance:</strong> Execution time, memory usage, CPU utilization</li>
                    <li><strong>Code Quality:</strong> Readability, maintainability, complexity metrics</li>
                    <li><strong>Functionality:</strong> Correctness validated through unit tests</li>
                    <li><strong>Custom Metrics:</strong> Define your own optimization targets</li>
                </ul>
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
