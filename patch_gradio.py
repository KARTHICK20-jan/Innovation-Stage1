#!/usr/bin/env python3
"""Patch gradio 4.44.1 for Python 3.14 on Render."""
import sys, os, glob, py_compile

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

# ── Patch 2: gradio_client/utils.py — fix json_schema_to_python_type ──────────
# The crash chain:
# json_schema_to_python_type(schema) → schema.get("$defs") crashes if schema=bool
# _json_schema_to_python_type(schema['additionalProperties']) → bool passed in
# get_type(bool_schema) → "const" in bool_schema → TypeError
# Fix ALL three entry points
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    src = open(utils_path).read()
    changes = 0

    # Fix A: json_schema_to_python_type top-level entry
    old_a = 'type_ = _json_schema_to_python_type(schema, schema.get("$defs"))'
    new_a = ('if not isinstance(schema, dict):\n'
             '        type_ = "str"\n'
             '    else:\n'
             '        type_ = _json_schema_to_python_type(schema, schema.get("$defs"))')
    if old_a in src and new_a not in src:
        src = src.replace(old_a, new_a, 1)
        changes += 1
        print("✅ Patch 3a: utils.py top-level guard")

    # Fix B: "const" in schema check
    old_b = '    if "const" in schema:'
    new_b = '    if isinstance(schema, dict) and "const" in schema:'
    if old_b in src and new_b not in src:
        src = src.replace(old_b, new_b, 1)
        changes += 1
        print("✅ Patch 3b: utils.py const check")

    # Fix C: additionalProperties bool crash
    old_c = 'f"str, {_json_schema_to_python_type(schema[\'additionalProperties\'], defs)}"'
    new_c = ('f"str, {_json_schema_to_python_type(schema[\'additionalProperties\'], defs) if isinstance(schema.get(\'additionalProperties\'), dict) else \'str\'}"')
    if old_c in src and new_c not in src:
        src = src.replace(old_c, new_c, 1)
        changes += 1
        print("✅ Patch 3c: utils.py additionalProperties guard")

    if changes == 0:
        print("ℹ️  utils.py already patched")
    open(utils_path, 'w').write(src)
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
