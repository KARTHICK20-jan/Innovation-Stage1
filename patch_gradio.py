#!/usr/bin/env python3
"""Patch gradio 4.44.1 for Python 3.14 on Render."""
import sys, os, glob, py_compile, re

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

# ── Patch 1: gradio/blocks.py ─────────────────────────────────────────────────
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
            print(f"✅ Patch 1: blocks.py health-check (line {i+1})")
        elif not p2 and 'raise DeprecationWarning(' in lines[i] and i+1 < len(lines) and 'concurrency_count' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i+1
            while j < len(lines) and lines[j].strip() not in (')', ');'): j += 1
            lines[i:j+1] = [' '*n + 'pass  # DeprecationWarning disabled\n']
            p2 = True
            print(f"✅ Patch 2: blocks.py DeprecationWarning (line {i+1})")
        if p1 and p2: break
        i += 1
    if not p1: print("ℹ️  blocks.py health-check already patched")
    if not p2: print("ℹ️  blocks.py DeprecationWarning already patched")
    open(blocks_path, 'w').writelines(lines)
    delete_pyc(blocks_path)

# ── Patch 2: gradio_client/utils.py — replace entire get_type function ────────
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    src = open(utils_path).read()

    # Replace the entire get_type function with a safe version
    new_get_type = '''def get_type(schema):
    if not isinstance(schema, dict):
        return "str"
    if "const" in schema:
        return f\'"{schema["const"]}"\'
    if "enum" in schema:
        vals = schema["enum"]
        if isinstance(vals, list):
            return "Literal[" + ", ".join([json.dumps(v) for v in vals]) + "]"
        return "str"
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "type" not in schema and "anyOf" not in schema and "oneOf" not in schema:
        return "Dict[str, Any]"
    _type = schema.get("type", "")
    if _type == "string":
        return "str"
    elif _type == "number":
        return "float"
    elif _type == "integer":
        return "int"
    elif _type == "boolean":
        return "bool"
    elif _type == "array":
        items = schema.get("items", {})
        return f"List[{get_type(items) if isinstance(items, dict) else \'str\'}]"
    elif _type == "object":
        add = schema.get("additionalProperties", {})
        return f"Dict[str, {get_type(add) if isinstance(add, dict) else \'str\'}]"
    elif "anyOf" in schema or "oneOf" in schema:
        key = "anyOf" if "anyOf" in schema else "oneOf"
        opts = schema[key]
        if not isinstance(opts, list):
            return "str"
        types = [get_type(o) for o in opts if isinstance(o, dict) and o.get("type") != "null"]
        return ("Optional[" + " | ".join(types) + "]") if types else "Optional[str]"
    return "str"
'''

    # Find and replace the existing get_type function
    # Match: def get_type(schema): ... until next def at same indent
    pattern = r'(def get_type\(schema\):.*?)(?=\ndef |\Z)'
    match = re.search(pattern, src, re.DOTALL)
    if match:
        src = src[:match.start()] + new_get_type + src[match.end():]
        open(utils_path, 'w').write(src)
        delete_pyc(utils_path)
        print("✅ Patch 3: utils.py get_type replaced with safe version")
    else:
        print("⚠️  utils.py get_type not found — trying line-by-line")
        lines = src.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.strip() == 'if "const" in schema:':
                ind = line[:len(line)-len(line.lstrip())]
                lines[i] = ind + 'if isinstance(schema, dict) and "const" in schema:\n'
                print(f"✅ Patch 3 fallback: utils.py const check (line {i+1})")
                break
        open(utils_path, 'w').writelines(lines)
        delete_pyc(utils_path)

# ── Patch 3: gradio/routes.py ─────────────────────────────────────────────────
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
            print(f"✅ Patch 4: routes.py stop_event (line {i+1})")
        if not p5 and '"Content-Type": "text/event-stream"' in line:
            lines[i] = line.replace(
                '"Content-Type": "text/event-stream"',
                '"Content-Type": "text/event-stream", "X-Accel-Buffering": "no", "Cache-Control": "no-cache"'
            )
            p5 = True
            print(f"✅ Patch 5: routes.py SSE headers (line {i+1})")
    if not p4: print("ℹ️  routes.py stop_event already patched")
    if not p5: print("ℹ️  routes.py SSE headers already patched")
    open(routes_path, 'w').writelines(lines)
    delete_pyc(routes_path)

print("Done.")
