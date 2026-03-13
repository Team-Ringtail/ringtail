"""
Code parsing utilities for extracting function information.

parse_function(source_code, language) returns a dict with function_name,
parameters, docstring, ast_representation. For Python we use the ast module
directly; for other languages we use generic regex-based parsing in Jac.
"""

import re;
import ast;
import from typing { Any }


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


def _annotation_to_string(annotation: Any | None) -> str | None {
    if annotation is None {
        return None;
    }
    if hasattr(ast, "unparse") {
        return ast.unparse(annotation);
    }
    return str(annotation);
}


def _literal_default(node: Any | None) -> Any | None {
    if node is None {
        return None;
    }
    try {
        return ast.literal_eval(node);
    } except Exception {
        return None;
    }
}


def _source_segment(source_code: str, node: Any) -> str {
    if hasattr(node, "lineno") and hasattr(node, "end_lineno") {
        lines = source_code.split("\n");
        start = int(node.lineno) - 1;
        end = int(node.end_lineno);
        return "\n".join(lines[start:end]);
    }
    return "";
}


def _python_function_info(source_code: str, node: Any) -> dict {
    parameters: list = [];
    positional_args = node.args.args;
    defaults = node.args.defaults;
    default_start = len(positional_args) - len(defaults);

    idx = 0;
    for arg in positional_args {
        param_type = _annotation_to_string(arg.annotation);
        default_value = None;
        if idx >= default_start and default_start >= 0 {
            default_value = _literal_default(defaults[idx - default_start]);
        }
        parameters.append({
            "name": arg.arg,
            "type": param_type,
            "default": default_value,
            "kind": "positional"
        });
        idx = idx + 1;
    }

    if node.args.vararg is not None {
        parameters.append({
            "name": node.args.vararg.arg,
            "type": _annotation_to_string(node.args.vararg.annotation),
            "default": None,
            "kind": "vararg"
        });
    }

    kw_idx = 0;
    for arg in node.args.kwonlyargs {
        default_value = None;
        if kw_idx < len(node.args.kw_defaults) {
            default_value = _literal_default(node.args.kw_defaults[kw_idx]);
        }
        parameters.append({
            "name": arg.arg,
            "type": _annotation_to_string(arg.annotation),
            "default": default_value,
            "kind": "kwonly"
        });
        kw_idx = kw_idx + 1;
    }

    if node.args.kwarg is not None {
        parameters.append({
            "name": node.args.kwarg.arg,
            "type": _annotation_to_string(node.args.kwarg.annotation),
            "default": None,
            "kind": "kwargs"
        });
    }

    docstring = ast.get_docstring(node);
    if docstring is None { docstring = ""; }

    ast_representation = {
        "name": node.name,
        "lineno": node.lineno,
        "end_lineno": getattr(node, "end_lineno", node.lineno),
        "args_count": len(node.args.args),
        "has_decorators": len(node.decorator_list) > 0,
        "is_async": isinstance(node, ast.AsyncFunctionDef)
    };

    return {
        "function_name": node.name,
        "parameters": parameters,
        "docstring": docstring,
        "ast_representation": ast_representation,
        "source_segment": _source_segment(source_code, node)
    };
}


def list_functions(source_code: str, language: str = "python") -> list {
    if language != "python" {
        parsed = _parse_generic_function(source_code);
        if parsed["function_name"] == "" {
            return [];
        }
        return [parsed];
    }

    try {
        tree = ast.parse(source_code);
        functions: list = [];
        for node in tree.body {
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef) {
                functions.append(_python_function_info(source_code, node));
            }
        }
        if len(functions) > 0 {
            return functions;
        }
        parsed = _parse_generic_function(source_code);
        if parsed["function_name"] == "" {
            return [];
        }
        return [parsed];
    } except SyntaxError {
        parsed = _parse_generic_function(source_code);
        if parsed["function_name"] == "" {
            return [];
        }
        return [parsed];
    } except Exception {
        return [];
    }
}


def parse_function(
    source_code: str,
    language: str = "python",
    function_name: str | None = None
) -> dict {
    if language == "python" {
        try {
            functions = list_functions(source_code, language);
            if function_name is not None and function_name != "" {
                for info in functions {
                    if info["function_name"] == function_name {
                        return info;
                    }
                }
            }
            if len(functions) > 0 {
                return functions[0];
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
