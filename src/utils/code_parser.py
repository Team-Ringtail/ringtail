"""
Code parsing utilities for extracting function information.

Pure Python functions that can be called from Jac files.
"""

import ast
import re
from typing import Dict, List, Any, Optional


def parse_function(source_code: str, language: str = "python") -> Dict[str, Any]:
    """
    Parse and extract function information from source code.
    
    Args:
        source_code: Raw function code as string
        language: Programming language (default: "python")
    
    Returns:
        Dictionary with:
        - function_name: str - Extracted function name
        - parameters: list - Function parameters
        - docstring: str - Function docstring if present
        - ast_representation: dict - Basic AST structure (optional, for future use)
    """
    if language == "python":
        return _parse_python_function(source_code)
    else:
        # For other languages, use basic string parsing
        return _parse_generic_function(source_code)


def _parse_python_function(source_code: str) -> Dict[str, Any]:
    """Parse Python function using AST module."""
    try:
        tree = ast.parse(source_code)
        
        # Find the first function definition
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Extract function name
                function_name = node.name
                
                # Extract parameters
                parameters = []
                for arg in node.args.args:
                    param_name = arg.arg
                    # Get type annotation if present
                    param_type = None
                    if arg.annotation:
                        param_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                    parameters.append({
                        "name": param_name,
                        "type": param_type
                    })
                
                # Extract docstring
                docstring = ast.get_docstring(node) or ""
                
                # Basic AST representation (simplified)
                ast_representation = {
                    "name": function_name,
                    "lineno": node.lineno,
                    "args_count": len(node.args.args),
                    "has_decorators": len(node.decorator_list) > 0
                }
                
                return {
                    "function_name": function_name,
                    "parameters": parameters,
                    "docstring": docstring,
                    "ast_representation": ast_representation
                }
        
        # If no function found, try to extract from string patterns
        return _parse_generic_function(source_code)
        
    except SyntaxError:
        # If AST parsing fails, fall back to regex parsing
        return _parse_generic_function(source_code)
    except Exception as e:
        # On any error, return minimal info with error indication
        return {
            "function_name": "",
            "parameters": [],
            "docstring": "",
            "ast_representation": {},
            "error": str(e)
        }


def _parse_generic_function(source_code: str) -> Dict[str, Any]:
    """Basic string-based parsing for non-Python code or fallback."""
    # Try to extract function name using regex patterns
    # Pattern: def function_name( or function function_name( or similar
    patterns = [
        r'def\s+(\w+)\s*\(',
        r'function\s+(\w+)\s*\(',
        r'(\w+)\s*=\s*function\s*\(',
    ]
    
    function_name = ""
    for pattern in patterns:
        match = re.search(pattern, source_code)
        if match:
            function_name = match.group(1)
            break
    
    # Try to extract parameters
    param_pattern = r'\(([^)]*)\)'
    parameters = []
    match = re.search(param_pattern, source_code)
    if match:
        param_string = match.group(1)
        if param_string.strip():
            # Split by comma and clean up
            param_names = [p.strip().split(':')[0].split('=')[0].strip() 
                          for p in param_string.split(',')]
            parameters = [{"name": name, "type": None} for name in param_names if name]
    
    # Try to extract docstring (triple quotes, single or double)
    docstring_pattern = r'"""(.*?)"""|\'\'\'(.*?)\'\'\''
    docstring_match = re.search(docstring_pattern, source_code, re.DOTALL)
    docstring = ""
    if docstring_match:
        docstring = docstring_match.group(1) or docstring_match.group(2) or ""
    
    return {
        "function_name": function_name,
        "parameters": parameters,
        "docstring": docstring,
        "ast_representation": {}
    }
