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
    """Delete .pyc cache so Python uses patched .py source."""
    # __pycache__/filename.cpython-314.pyc
    base = os.path.splitext(os.path.basename(py_path))[0]
    cache_dir = os.path.join(os.path.dirname(py_path), '__pycache__')
    for pyc in glob.glob(os.path.join(cache_dir, f'{base}.*.pyc')):
        os.remove(pyc)
        print(f"   Deleted cache: {os.path.basename(pyc)}")
    # Also recompile to fresh .pyc
    try:
        py_compile.compile(py_path, doraise=True)
    except Exception as e:
        print(f"   Recompile note: {e}")

# ── Patch blocks.py ───────────────────────────────────────────────────────────
blocks_path = os.path.join(venv_site, 'gradio', 'blocks.py')
if os.path.exists(blocks_path):
    lines = open(blocks_path).readlines()
    p1, p2 = False, False
    i = 0
    while i < len(lines):
        # Fix 1: localhost health-check ValueError
        if not p1 and 'raise ValueError(' in lines[i] and i+1 < len(lines) and 'localhost' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i + 1
            while j < len(lines) and lines[j].strip() not in (')', ');'):
                j += 1
            lines[i:j+1] = [' '*n + 'pass  # health-check disabled\n']
            p1 = True
            print(f"✅ Patch 1: blocks.py health-check removed (line {i+1})")
        # Fix 2: concurrency_count DeprecationWarning
        elif not p2 and 'raise DeprecationWarning(' in lines[i] and i+1 < len(lines) and 'concurrency_count' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i + 1
            while j < len(lines) and lines[j].strip() not in (')', ');'):
                j += 1
            lines[i:j+1] = [' '*n + 'pass  # DeprecationWarning disabled\n']
            p2 = True
            print(f"✅ Patch 2: blocks.py DeprecationWarning removed (line {i+1})")
        if p1 and p2:
            break
        i += 1
    if not p1: print("ℹ️  blocks.py health-check already patched")
    if not p2: print("ℹ️  blocks.py DeprecationWarning already patched")
    open(blocks_path, 'w').writelines(lines)
    delete_pyc(blocks_path)
else:
    print(f"❌ Not found: {blocks_path}")

# ── Patch routes.py ───────────────────────────────────────────────────────────
routes_path = os.path.join(venv_site, 'gradio', 'routes.py')
if os.path.exists(routes_path):
    lines = open(routes_path).readlines()
    p3, p4 = False, False
    for i, line in enumerate(lines):
        if not p3 and 'await app.stop_event.wait()' in line:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'if app.stop_event is not None:\n' +
                        ind + '    await app.stop_event.wait()\n')
            p3 = True
            print(f"✅ Patch 3: routes.py stop_event None guard (line {i+1})")
        if not p4 and 'gradio_api_info = api_info(False)' in line and 'try:' not in line:
            ind = line[:len(line) - len(line.lstrip())]
            ext = ind + '    '
            lines[i] = (ind + 'try:\n' +
                        ext + 'gradio_api_info = api_info(False)\n' +
                        ind + 'except Exception:\n' +
                        ext + 'gradio_api_info = {}\n')
            p4 = True
            print(f"✅ Patch 4: routes.py api_info wrapped (line {i+1})")
    if not p3: print("ℹ️  routes.py stop_event already patched")
    if not p4: print("ℹ️  routes.py api_info already patched")
    open(routes_path, 'w').writelines(lines)
    delete_pyc(routes_path)
else:
    print(f"❌ Not found: {routes_path}")

print("Done.")
