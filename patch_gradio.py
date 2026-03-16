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
            print(f"✅ Patch 1: blocks.py health-check removed (line {i+1})")
        elif not p2 and 'raise DeprecationWarning(' in lines[i] and i+1 < len(lines) and 'concurrency_count' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i+1
            while j < len(lines) and lines[j].strip() not in (')', ');'): j += 1
            lines[i:j+1] = [' '*n + 'pass  # DeprecationWarning disabled\n']
            p2 = True
            print(f"✅ Patch 2: blocks.py DeprecationWarning removed (line {i+1})")
        if p1 and p2: break
        i += 1
    if not p1: print("ℹ️  blocks.py health-check already patched")
    if not p2: print("ℹ️  blocks.py DeprecationWarning already patched")
    open(blocks_path, 'w').writelines(lines)
    delete_pyc(blocks_path)

# ── Patch 2: gradio_client/utils.py ──────────────────────────────────────────
# Fix the exact line that crashes: if "const" in schema (when schema is bool)
# AND fix _json_schema_to_python_type to guard non-dict schema at entry
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    lines = open(utils_path).readlines()
    changes = 0
    for i, line in enumerate(lines):
        # Fix 1: guard "const" in schema when schema is bool
        if line.strip() == 'if "const" in schema:' and changes == 0:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = ind + 'if isinstance(schema, dict) and "const" in schema:\n'
            changes += 1
            print(f"✅ Patch 3a: utils.py const check (line {i+1})")
        # Fix 2: guard schema.get() call at top of _json_schema_to_python_type
        if 'type_ = _json_schema_to_python_type(schema, schema.get' in line:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'if not isinstance(schema, dict):\n' +
                       ind + '    type_ = "str"\n' +
                       ind + 'else:\n' +
                       ind + '    type_ = _json_schema_to_python_type(schema, schema.get("$defs"))\n')
            changes += 1
            print(f"✅ Patch 3b: utils.py schema.get guard (line {i+1})")
    if changes == 0:
        print("ℹ️  utils.py already patched")
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
            print(f"✅ Patch 4: routes.py stop_event guard (line {i+1})")
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
