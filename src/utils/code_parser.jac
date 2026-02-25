"""Code parsing utilities for extracting function information."""

import ast;
import re;
import from typing { Dict, List, Any, Optional }


def parse_function(source_code: str, language: str = "python") -> dict {
    if language == "python" {
        return _parse_python_function(source_code);
    } else {
        return _parse_generic_function(source_code);
    }
}


def _parse_python_function(source_code: str) -> dict {
    """Parse Python function using the AST module."""
    try {
        tree = ast.parse(source_code);

        for node in ast.walk(tree) {
            if isinstance(node, ast.FunctionDef) {
                function_name = node.name;

                parameters = [];
                for arg in node.args.args {
                    param_name = arg.arg;
                    param_type = None;
                    if arg.annotation {
                        param_type = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else str(arg.annotation);
                    }
                    parameters.append({
                        "name": param_name,
                        "type": param_type
                    });
                }

                docstring = ast.get_docstring(node) or "";

                ast_representation = {
                    "name": function_name,
                    "lineno": node.lineno,
                    "args_count": len(node.args.args),
                    "has_decorators": len(node.decorator_list) > 0
                };

                return {
                    "function_name": function_name,
                    "parameters": parameters,
                    "docstring": docstring,
                    "ast_representation": ast_representation
                };
            }
        }

        return _parse_generic_function(source_code);

    } except SyntaxError {
        return _parse_generic_function(source_code);
    } except Exception as e {
        return {
            "function_name": "",
            "parameters": [],
            "docstring": "",
            "ast_representation": {},
            "error": str(e)
        };
    }
}


def _parse_generic_function(source_code: str) -> dict {
    """Basic string-based parsing for non-Python code or fallback."""
    patterns = [
        r'def\s+(\w+)\s*\(',
        r'function\s+(\w+)\s*\(',
        r'(\w+)\s*=\s*function\s*\('
    ];

    function_name = "";
    for pattern in patterns {
        match = re.search(pattern, source_code);
        if match {
            function_name = match.group(1);
            break;
        }
    }

    param_pattern = r'\(([^)]*)\)';
    parameters = [];
    match = re.search(param_pattern, source_code);
    if match {
        param_string = match.group(1);
        if param_string.strip() {
            param_names = [p.strip().split(':')[0].split('=')[0].strip()
                           for p in param_string.split(',')];
            parameters = [{"name": name, "type": None} for name in param_names if name];
        }
    }

    docstring_pattern = r'"""(.*?)"""|\'\'\'(.*?)\'\'\'';
    docstring_match = re.search(docstring_pattern, source_code, re.DOTALL);
    docstring = "";
    if docstring_match {
        docstring = docstring_match.group(1) or docstring_match.group(2) or "";
    }

    return {
        "function_name": function_name,
        "parameters": parameters,
        "docstring": docstring,
        "ast_representation": {}
    };
}
