"""Code Parser Agent — AST-based code structure extraction."""
import ast
import re
from typing import Optional


def parse_code(code: str, language: str) -> dict:
    """Parse code into structured representation."""
    if language == "python":
        return _parse_python(code)
    elif language in ("javascript", "typescript"):
        return _parse_javascript(code)
    else:
        return _parse_generic(code)


def _parse_python(code: str) -> dict:
    """Parse Python code using the ast module with scope-aware analysis."""
    result = {
        "functions": [],
        "classes": [],
        "variables": [],
        "imports": [],
        "loops": [],
        "conditionals": [],
        "function_calls": [],
        "risks": [],
        "lines": code.splitlines(),
        "line_count": len(code.splitlines()),
    }

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result["risks"].append({
            "type": "syntax_error",
            "line": e.lineno or 0,
            "message": str(e.msg),
        })
        return result

    # ── Pass 1: Collect all assigned/defined names per scope ──
    defined_names = set()
    # Builtins
    defined_names.update([
        "print", "len", "range", "int", "float", "str", "list", "dict",
        "set", "tuple", "bool", "type", "input", "open", "file", "map",
        "filter", "zip", "enumerate", "sorted", "reversed", "sum", "min",
        "max", "abs", "round", "pow", "isinstance", "issubclass", "hasattr",
        "getattr", "setattr", "delattr", "super", "property", "staticmethod",
        "classmethod", "True", "False", "None", "Exception", "ValueError",
        "TypeError", "KeyError", "IndexError", "AttributeError", "RuntimeError",
        "StopIteration", "NotImplementedError", "OSError", "IOError",
        "FileNotFoundError", "ImportError", "ModuleNotFoundError",
        "__name__", "__main__", "__file__", "__doc__", "self", "cls",
    ])

    # Collect function names, their params, and local variables
    func_info = {}  # func_name -> {"params": [], "locals": set(), "line": int}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            params = [arg.arg for arg in node.args.args]
            local_vars = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            local_vars.add(target.id)
            func_info[node.name] = {
                "params": params,
                "locals": local_vars,
                "line": node.lineno,
            }
            defined_names.add(node.name)
            defined_names.update(params)
            defined_names.update(local_vars)
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "args": params,
            })

        elif isinstance(node, ast.ClassDef):
            result["classes"].append({"name": node.name, "line": node.lineno})
            defined_names.add(node.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                result["imports"].append(alias.name)
                defined_names.add(name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)
                defined_names.add(node.module.split('.')[0])
            for alias in (node.names or []):
                name = alias.asname or alias.name
                defined_names.add(name)

        elif isinstance(node, (ast.For, ast.While)):
            loop_type = "for" if isinstance(node, ast.For) else "while"
            result["loops"].append({"type": loop_type, "line": node.lineno})
            # For-loop variable
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)

        elif isinstance(node, ast.If):
            result["conditionals"].append({"line": node.lineno})

    # ── Pass 2: Detect risks via AST ──
    for node in ast.walk(tree):

        # Risk: Division by zero
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            result["risks"].append({
                "type": "division",
                "line": node.lineno,
                "message": "Division operation detected — potential division by zero",
            })

        # Risk: Bare except
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            result["risks"].append({
                "type": "bare_except",
                "line": node.lineno,
                "message": "Bare except clause — may swallow important exceptions",
            })

        # Risk: Function calls
        elif isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                result["function_calls"].append({"name": func_name, "line": node.lineno})
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                result["function_calls"].append({"name": func_name, "line": node.lineno})

                # Detect math.sqrt with potentially negative argument
                if (isinstance(node.func.value, ast.Name) and
                    node.func.value.id == "math" and func_name == "sqrt"):
                    result["risks"].append({
                        "type": "negative_sqrt",
                        "line": node.lineno,
                        "message": "math.sqrt() called — will raise ValueError if argument is negative. Ensure the argument is validated before this call.",
                    })

            # Detect function called with literal 0 as argument (potential division by zero)
            if func_name and node.args:
                for arg_idx, arg in enumerate(node.args):
                    if isinstance(arg, ast.Constant) and arg.value == 0:
                        # Check if this function does division with this param
                        if func_name in func_info:
                            fi = func_info[func_name]
                            if arg_idx < len(fi["params"]):
                                param_name = fi["params"][arg_idx]
                                result["risks"].append({
                                    "type": "zero_argument",
                                    "line": node.lineno,
                                    "message": f"Passing literal 0 to function '{func_name}()' as parameter '{param_name}' — if used as divisor, this will cause ZeroDivisionError.",
                                    "function": func_name,
                                    "param": param_name,
                                })

        # Risk: Subscript with arithmetic (e.g., data[i+1])
        elif isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Add):
                if isinstance(node.slice.right, ast.Constant) and isinstance(node.slice.right.value, int):
                    array_name = ""
                    if isinstance(node.value, ast.Name):
                        array_name = node.value.id
                    result["risks"].append({
                        "type": "out_of_bounds",
                        "line": node.lineno,
                        "message": f"Potential IndexError: accessing '{array_name}[i + {node.slice.right.value}]' may exceed list bounds in a loop.",
                        "variable": array_name,
                    })

    # ── Pass 3: Detect undefined variable usage ──
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check return statements and expressions within this function
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    name = child.id
                    # Check if it's defined in function scope
                    fi = func_info.get(node.name, {})
                    local_scope = set(fi.get("params", [])) | fi.get("locals", set())
                    if name not in local_scope and name not in defined_names:
                        result["risks"].append({
                            "type": "undefined_variable",
                            "line": child.lineno,
                            "message": f"Undefined variable '{name}' — this name is not defined in the local or global scope. Possibly a typo.",
                            "variable": name,
                        })

    # Detect variable assignments for tracking
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result["variables"].append({
                        "name": target.id,
                        "line": node.lineno,
                    })

    # Deduplicate risks
    seen = set()
    unique_risks = []
    for risk in result["risks"]:
        key = (risk["type"], risk["line"])
        if key not in seen:
            seen.add(key)
            unique_risks.append(risk)
    result["risks"] = unique_risks

    return result


def _parse_javascript(code: str) -> dict:
    """Parse JavaScript/TypeScript using regex-based extraction with scope analysis."""
    result = {
        "functions": [],
        "classes": [],
        "variables": [],
        "imports": [],
        "loops": [],
        "conditionals": [],
        "function_calls": [],
        "risks": [],
        "lines": code.splitlines(),
        "line_count": len(code.splitlines()),
    }

    lines = code.splitlines()

    # ── Pass 1: Collect all declared names (variables, functions, params, builtins) ──
    declared_names = set()
    # JS builtins that should never be flagged
    declared_names.update([
        "console", "Math", "JSON", "Object", "Array", "String", "Number",
        "Boolean", "Date", "RegExp", "Error", "Map", "Set", "Promise",
        "parseInt", "parseFloat", "isNaN", "isFinite", "undefined", "null",
        "true", "false", "NaN", "Infinity", "window", "document",
        "setTimeout", "setInterval", "clearTimeout", "clearInterval",
        "require", "module", "exports", "process", "global", "__dirname",
    ])

    # Collect function names and their parameter names
    func_params = {}  # func_name -> [param_names]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Function declarations: function foo(a, b)
        fn_match = re.match(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', stripped)
        if fn_match:
            fname = fn_match.group(1)
            params = [p.strip().split('=')[0].strip() for p in fn_match.group(2).split(',') if p.strip()]
            declared_names.add(fname)
            declared_names.update(params)
            func_params[fname] = params
            result["functions"].append({"name": fname, "line": i, "params": params})
            continue

        # Arrow functions: const foo = (a, b) =>
        arrow_match = re.match(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)', stripped)
        if arrow_match:
            fname = arrow_match.group(1)
            params = [p.strip().split('=')[0].strip() for p in arrow_match.group(2).split(',') if p.strip()]
            declared_names.add(fname)
            declared_names.update(params)
            func_params[fname] = params
            result["functions"].append({"name": fname, "line": i, "params": params})
            continue

        # Variable declarations
        var_match = re.match(r'(?:const|let|var)\s+(\w+)', stripped)
        if var_match:
            vname = var_match.group(1)
            declared_names.add(vname)
            result["variables"].append({"name": vname, "line": i})

        # For-loop iterator variables: for (let i = 0; ...)
        for_var = re.match(r'for\s*\(\s*(?:let|var|const)\s+(\w+)', stripped)
        if for_var:
            declared_names.add(for_var.group(1))

    # ── Pass 2: Full analysis ──
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            continue

        # Classes
        cls_match = re.match(r'(?:export\s+)?class\s+(\w+)', stripped)
        if cls_match:
            result["classes"].append({"name": cls_match.group(1), "line": i})

        # Imports
        if stripped.startswith("import ") or (stripped.startswith("const ") and "require(" in stripped):
            result["imports"].append(stripped)

        # Loops
        if re.match(r'for\s*\(', stripped) or re.match(r'while\s*\(', stripped):
            loop_type = "for" if "for" in stripped[:5] else "while"
            result["loops"].append({"type": loop_type, "line": i, "content": stripped})

        # Conditionals
        if re.match(r'if\s*\(', stripped):
            result["conditionals"].append({"line": i})

        # ── Risk: Off-by-one in loops (<= .length) ──
        obo_match = re.search(r'(\w+)\s*<=\s*(\w+)\.length', stripped)
        if obo_match:
            result["risks"].append({
                "type": "off_by_one",
                "line": i,
                "message": f"Off-by-one error: '{obo_match.group(1)} <= {obo_match.group(2)}.length' will access one element past the end of the array. Use '<' instead of '<='.",
                "variable": obo_match.group(1),
                "array": obo_match.group(2),
            })

        # ── Risk: Out-of-bounds access (arr[i + 1] or arr[i+1]) inside loop ──
        oob_match = re.search(r'(\w+)\[(\w+)\s*\+\s*(\d+)\]', stripped)
        if oob_match and not re.search(r'(if|while|&&|\|\||\.length)', stripped):
            result["risks"].append({
                "type": "out_of_bounds",
                "line": i,
                "message": f"Potential out-of-bounds access: '{oob_match.group(1)}[{oob_match.group(2)} + {oob_match.group(3)}]' may exceed array length.",
                "array": oob_match.group(1),
            })

        # ── Risk: Null-unsafe member access (param.property without null check) ──
        member_match = re.search(r'(\w+)\.(\w+)(?:\.(\w+))?', stripped)
        if member_match:
            obj_name = member_match.group(1)
            # Only flag if the object is a function parameter (could be null/undefined)
            if obj_name in declared_names and obj_name not in (
                "console", "Math", "JSON", "Object", "Array", "String",
                "Number", "Date", "document", "window", "process", "module",
                "result", "this",
            ):
                # Check if it's a function parameter
                for fn_name, params in func_params.items():
                    if obj_name in params:
                        # Is there a null/undefined guard above this line?
                        has_guard = False
                        for j in range(max(0, i - 5), i - 1):
                            guard_line = lines[j].strip()
                            if obj_name in guard_line and any(kw in guard_line for kw in ['if', '?', '!', '&&', '||', 'null', 'undefined']):
                                has_guard = True
                                break
                        if not has_guard:
                            result["risks"].append({
                                "type": "null_reference",
                                "line": i,
                                "message": f"Null reference risk: '{obj_name}' is a function parameter and could be null or undefined. Accessing '.{member_match.group(2)}' will throw TypeError.",
                                "variable": obj_name,
                            })
                        break

        # ── Risk: Division ──
        div_match = re.search(r'(\w+)\s*/\s*(\w[\w.]*)', stripped)
        if div_match and not stripped.startswith('//') and '//' not in stripped.split(div_match.group(0))[0]:
            divisor = div_match.group(2)
            # Check if there's a guard for zero
            result["risks"].append({
                "type": "division",
                "line": i,
                "message": f"Division by '{divisor}' — potential division by zero if '{divisor}' is 0.",
                "variable": divisor,
            })

        # ── Risk: Undefined variable usage ──
        # Find all identifier-like tokens used in expressions (not declarations)
        if not re.match(r'(?:const|let|var|function|class|import|export|return)\s', stripped):
            # Strip inline comments and string literals to avoid false positives
            clean_line = re.sub(r'//.*$', '', stripped)  # remove inline comments
            clean_line = re.sub(r'"[^"]*"', '""', clean_line)  # remove double-quoted strings
            clean_line = re.sub(r"'[^']*'", "''", clean_line)  # remove single-quoted strings
            clean_line = re.sub(r'`[^`]*`', '``', clean_line)  # remove template literals

            used_ids = re.findall(r'\b([a-zA-Z_]\w*)\b', clean_line)
            for uid in used_ids:
                if uid not in declared_names and uid not in (
                    'if', 'else', 'for', 'while', 'do', 'switch', 'case',
                    'break', 'continue', 'return', 'function', 'class',
                    'const', 'let', 'var', 'new', 'typeof', 'instanceof',
                    'in', 'of', 'this', 'super', 'yield', 'await', 'async',
                    'try', 'catch', 'finally', 'throw', 'import', 'export',
                    'default', 'from', 'as', 'void', 'delete', 'with',
                    'toUpperCase', 'toLowerCase', 'toString', 'valueOf',
                    'push', 'pop', 'shift', 'unshift', 'splice', 'slice',
                    'map', 'filter', 'reduce', 'forEach', 'find', 'some',
                    'every', 'includes', 'indexOf', 'join', 'split', 'trim',
                    'length', 'log', 'error', 'warn', 'info',
                ):
                    result["risks"].append({
                        "type": "undefined_variable",
                        "line": i,
                        "message": f"Undefined variable '{uid}' — this variable is used but never declared. This will cause a ReferenceError at runtime.",
                        "variable": uid,
                    })

        # ── Risk: Function called with null literal ──
        null_call = re.search(r'(\w+)\(\s*null\s*\)', stripped)
        if null_call:
            fn_name = null_call.group(1)
            if fn_name in func_params and fn_name not in ("console", "Math"):
                result["risks"].append({
                    "type": "null_argument",
                    "line": i,
                    "message": f"Passing null to function '{fn_name}()' — if the function accesses properties of this parameter, it will throw TypeError.",
                    "function": fn_name,
                })

        # ── Risk: eval ──
        if "eval(" in stripped:
            result["risks"].append({
                "type": "security",
                "line": i,
                "message": "eval() usage detected — security risk",
            })

        # ── Function calls (for tracking) ──
        call_matches = re.finditer(r'(\w+)\s*\(', stripped)
        for cm in call_matches:
            call_name = cm.group(1)
            if call_name not in ('if', 'for', 'while', 'switch', 'function', 'return'):
                result["function_calls"].append({"name": call_name, "line": i})

    # Deduplicate risks by (type, line)
    seen_risks = set()
    unique_risks = []
    for risk in result["risks"]:
        key = (risk["type"], risk["line"])
        if key not in seen_risks:
            seen_risks.add(key)
            unique_risks.append(risk)
    result["risks"] = unique_risks

    return result


def _parse_generic(code: str) -> dict:
    """Basic parsing for unknown languages."""
    lines = code.splitlines()
    return {
        "functions": [],
        "classes": [],
        "variables": [],
        "imports": [],
        "loops": [],
        "conditionals": [],
        "function_calls": [],
        "risks": [],
        "lines": lines,
        "line_count": len(lines),
    }
