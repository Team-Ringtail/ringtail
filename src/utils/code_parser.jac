"""
Code parsing utilities for extracting function information.

parse_function(source_code, language) returns a dict with function_name,
parameters, docstring, ast_representation. For Python we use the ast module
directly; for other languages we use generic regex-based parsing in Jac.
"""

import re;
import ast;


def _first_function_name(patterns: list, source_code: str) -> str {
    i = 0;
    while i < len(patterns) {
        m = re.search(patterns[i], source_code);
        if m is not None {
            return m.group(1);
        }
        i = i + 1;
    }
    return "";
}


def _parse_generic_function(source_code: str) -> dict {
    p1 = 'def\\s+(\\w+)\\s*\\(';
    p2 = 'function\\s+(\\w+)\\s*\\(';
    p3 = '(\\w+)\\s*=\\s*function\\s*\\(';
    patterns = [p1, p2, p3];
    function_name = _first_function_name(patterns, source_code);

    param_pattern = "\\(([^)]*)\\)";
    param_match = re.search(param_pattern, source_code);
    parameters: list = [];
    if param_match {
        param_string = param_match.group(1);
        if param_string.strip() != "" {
            parts = param_string.split(",");
            for p in parts {
                name = p.strip().split(":")[0].split("=")[0].strip();
                if name != "" {
                    parameters.append({"name": name, "type": None});
                }
            }
        }
    }

    docstring_pattern = "\"\"\"(.*?)\"\"\"|'''(.*?)'''";
    docstring_match = re.search(docstring_pattern, source_code, re.DOTALL);
    docstring = "";
    if docstring_match {
        g1 = docstring_match.group(1);
        g2 = docstring_match.group(2);
        if g1 is not None { docstring = g1; }
        elif g2 is not None { docstring = g2; }
    }

    return {
        "function_name": function_name,
        "parameters": parameters,
        "docstring": docstring,
        "ast_representation": {}
    };
}


def parse_function(source_code: str, language: str = "python") -> dict {
    if language == "python" {
        try {
            tree = ast.parse(source_code);
            for node in ast.walk(tree) {
                if isinstance(node, ast.FunctionDef) {
                    function_name = node.name;

                    parameters: list = [];
                    for arg in node.args.args {
                        param_type = None;
                        if arg.annotation is not None {
                            if hasattr(ast, "unparse") {
                                param_type = ast.unparse(arg.annotation);
                            } else {
                                param_type = str(arg.annotation);
                            }
                        }
                        parameters.append({"name": arg.arg, "type": param_type});
                    }

                    docstring = ast.get_docstring(node);
                    if docstring is None { docstring = ""; }

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
    return _parse_generic_function(source_code);
}
