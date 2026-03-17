#!/usr/bin/env python3
"""Patch gradio 4.44.1 + dependencies for Python 3.14 on Render."""
import sys, os, glob, py_compile, ast

venv_site = os.path.normpath(os.path.join(
    os.path.dirname(sys.executable), '..', 'lib',
    f'python{sys.version_info.major}.{sys.version_info.minor}',
    'site-packages'
))
print(f"Patching in: {venv_site}")

def delete_pyc(py_path):
    base = os.path.splitext(os.path.basename(py_path))[0]
    cache_dir = os.path.join(os.path.dirname(py_path), '__pycache__')
    for pyc in glob.glob(os.path.join(cache_dir, f'{base}.*.pyc')):
        os.remove(pyc)
    try:
        py_compile.compile(py_path, doraise=True)
    except Exception:
        pass

# ── Patch 1: pydub/utils.py ───────────────────────────────────────────────────
pydub_path = os.path.join(venv_site, 'pydub', 'utils.py')
if os.path.exists(pydub_path):
    lines = open(pydub_path).readlines()
    for i, line in enumerate(lines):
        if line.strip() == 'import pyaudioop as audioop':
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'try:\n' +
                        ind + '    import pyaudioop as audioop\n' +
                        ind + 'except ImportError:\n' +
                        ind + '    audioop = None\n')
            open(pydub_path, 'w').writelines(lines)
            delete_pyc(pydub_path)
            print("✅ pydub/utils.py pyaudioop fix")
            break
    else:
        print("ℹ️  pydub already patched")

# ── Patch 2: gradio/blocks.py ─────────────────────────────────────────────────
blocks_path = os.path.join(venv_site, 'gradio', 'blocks.py')
if os.path.exists(blocks_path):
    lines = open(blocks_path).readlines()
    p1, p2 = False, False
    i = 0
    while i < len(lines):
        if not p1 and 'raise ValueError(' in lines[i] and i+1 < len(lines) and 'localhost' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i+1
            while j < len(lines) and lines[j].strip() not in (')', ');'): j += 1
            lines[i:j+1] = [' '*n + 'pass  # health-check disabled\n']
            p1 = True
            print("✅ blocks.py health-check removed")
        elif not p2 and 'raise DeprecationWarning(' in lines[i] and i+1 < len(lines) and 'concurrency_count' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i+1
            while j < len(lines) and lines[j].strip() not in (')', ');'): j += 1
            lines[i:j+1] = [' '*n + 'pass  # DeprecationWarning disabled\n']
            p2 = True
            print("✅ blocks.py DeprecationWarning removed")
        if p1 and p2: break
        i += 1
    if not p1: print("ℹ️  blocks.py health-check already patched")
    if not p2: print("ℹ️  blocks.py DeprecationWarning already patched")
    open(blocks_path, 'w').writelines(lines)
    delete_pyc(blocks_path)

# ── Patch 3: gradio_client/utils.py — replace get_type + guard entry ──────────
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    lines = open(utils_path).readlines()

    # Step A: guard the entry point (line 893/894)
    for i, line in enumerate(lines):
        if 'type_ = _json_schema_to_python_type(schema, schema.get("$defs"))' in line:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'if not isinstance(schema, dict):\n' +
                        ind + '    type_ = "str"\n' +
                        ind + 'else:\n' +
                        ind + '    type_ = _json_schema_to_python_type(schema, schema.get("$defs"))\n')
            print("✅ utils.py entry guard (schema.get)")
            break

    # Step B: replace entire get_type function body to guard ALL checks
    new_get_type_body = [
        '    if not isinstance(schema, dict):\n',
        '        return "str"\n',
        '    if "const" in schema:\n',
        '        return f\'"{schema["const"]}"\'\n',
        '    if "enum" in schema:\n',
        '        return "str"\n',
        '    if "$ref" in schema:\n',
        '        return schema["$ref"].split("/")[-1]\n',
        '    if "type" not in schema and "anyOf" not in schema and "oneOf" not in schema:\n',
        '        return "Dict[str, Any]"\n',
        '    _type = schema.get("type", "")\n',
        '    if _type == "string":\n',
        '        return "str"\n',
        '    elif _type == "number":\n',
        '        return "float"\n',
        '    elif _type == "integer":\n',
        '        return "int"\n',
        '    elif _type == "boolean":\n',
        '        return "bool"\n',
        '    elif _type == "array":\n',
        '        items = schema.get("items", {})\n',
        '        return f"List[{get_type(items) if isinstance(items, dict) else \'str\'}]"\n',
        '    elif _type == "object":\n',
        '        add = schema.get("additionalProperties", {})\n',
        '        return f"Dict[str, {get_type(add) if isinstance(add, dict) else \'str\'}]"\n',
        '    return "str"\n',
    ]

    # Find get_type function and replace its body
    in_get_type = False
    func_start = None
    func_indent = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith('def get_type(schema'):
            in_get_type = True
            func_start = i
            func_indent = indent
            continue
        if in_get_type:
            # Find end of function (next def at same or lower indent)
            if stripped.startswith('def ') and indent <= func_indent:
                # Replace function body
                func_def_line = lines[func_start]
                lines[func_start:i] = [func_def_line] + new_get_type_body
                print("✅ utils.py get_type replaced")
                break

    open(utils_path, 'w').writelines(lines)
    delete_pyc(utils_path)

# ── Patch 4: gradio/routes.py ─────────────────────────────────────────────────
routes_path = os.path.join(venv_site, 'gradio', 'routes.py')
if os.path.exists(routes_path):
    lines = open(routes_path).readlines()
    p4, p5 = False, False
    for i, line in enumerate(lines):
        if not p4 and 'await app.stop_event.wait()' in line:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'if app.stop_event is not None:\n' +
                        ind + '    await app.stop_event.wait()\n')
            p4 = True
            print("✅ routes.py stop_event guard")
        if not p5 and '"Content-Type": "text/event-stream"' in line:
            lines[i] = line.replace(
                '"Content-Type": "text/event-stream"',
                '"Content-Type": "text/event-stream", "X-Accel-Buffering": "no", "Cache-Control": "no-cache"'
            )
            p5 = True
            print("✅ routes.py SSE headers")
    if not p4: print("ℹ️  routes.py stop_event already patched")
    if not p5: print("ℹ️  routes.py SSE headers already patched")
    open(routes_path, 'w').writelines(lines)
    delete_pyc(routes_path)

print("All patches done.")
