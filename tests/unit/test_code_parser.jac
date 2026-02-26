"""Unit tests for src/utils/code_parser.jac — parse_function."""

import from src.utils.code_parser { parse_function };


test "parse_function python simple" {
    source = "def add(a: int, b: int) -> int:\n    \"\"\"Add numbers\"\"\"\n    return a + b";
    info = parse_function(source, "python");

    assert info["function_name"] == "add";
    params = info["parameters"];
    assert len(params) == 2;
    assert params[0]["name"] == "a";
    assert params[1]["name"] == "b";
    assert info["docstring"] == "Add numbers";
    ast_repr = info["ast_representation"];
    assert "name" in ast_repr;
    assert "lineno" in ast_repr;
    assert "args_count" in ast_repr;
    assert "has_decorators" in ast_repr;
}

test "parse_function python multiple functions picks first" {
    source = "def first():\n    pass\n\ndef second():\n    pass";
    info = parse_function(source, "python");

    assert info["function_name"] == "first";
}

test "parse_function python syntax error falls back" {
    source = "def bad(:\n    pass";
    info = parse_function(source, "python");

    assert "function_name" in info;
    assert "parameters" in info;
    assert "docstring" in info;
    assert "ast_representation" in info;
}

test "parse_function generic js style" {
    source = "function foo(x, y) { return x + y; }";
    info = parse_function(source, "javascript");

    assert info["function_name"] == "foo";
    params = info["parameters"];
    assert len(params) == 2;
    assert params[0]["name"] == "x";
    assert params[1]["name"] == "y";
    assert info["docstring"] == "";
}

test "parse_function generic assigned function" {
    source = "foo = function(x, y) { return x + y; }";
    info = parse_function(source, "javascript");

    assert info["function_name"] == "foo";
    params = info["parameters"];
    assert len(params) == 2;
    assert params[0]["name"] == "x";
    assert params[1]["name"] == "y";
}

test "parse_function docstring triple quotes generic" {
    source = "\"\"\"\nDocstring before function\n\"\"\"\ndef f(x, y):\n    return x + y";
    info = parse_function(source, "javascript");

    assert "Docstring before function" in info["docstring"];
}
