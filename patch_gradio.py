#!/usr/bin/env python3
"""Patch gradio 4.44.1 for Python 3.14 on Render."""
import sys, os

venv_site = os.path.normpath(os.path.join(
    os.path.dirname(sys.executable), '..', 'lib',
    f'python{sys.version_info.major}.{sys.version_info.minor}',
    'site-packages'
))
print(f"Patching in: {venv_site}")

# ── Patch 1: gradio_client/utils.py — fix bool TypeError ─────────────────────
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    lines = open(utils_path).readlines()
    p1 = False
    for i, line in enumerate(lines):
        # Fix 1a: "const" in schema crashes when schema is bool
        if line.strip() == 'if "const" in schema:' and not p1:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = ind + 'if isinstance(schema, dict) and "const" in schema:\n'
            p1 = True
            print(f"✅ Patch 1a: utils.py line {i+1} (const check)")
    # Fix 1b: also wrap get_type to never crash on non-dict schema
    for i, line in enumerate(lines):
        if 'def get_type(schema)' in line and 'try:' not in (lines[i+1] if i+1 < len(lines) else ''):
            ind = line[:len(line) - len(line.lstrip())]
            # Insert try/except around the whole function body
            # Instead, add a guard at the top
            if i+1 < len(lines):
                body_ind = lines[i+1][:len(lines[i+1]) - len(lines[i+1].lstrip())]
                guard = body_ind + 'if not isinstance(schema, dict): return "any"\n'
                lines.insert(i+1, guard)
                print(f"✅ Patch 1b: utils.py line {i+1} (get_type guard)")
            break
    if not p1:
        print(f"⚠️  Patch 1a not applied — showing lines 860-866:")
        for j in range(859, min(866, len(lines))):
            print(f"   L{j+1}: {repr(lines[j])}")
    open(utils_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {utils_path}")

# ── Patch 2: gradio/routes.py — wrap api_info in try/except ──────────────────
routes_path = os.path.join(venv_site, 'gradio', 'routes.py')
if os.path.exists(routes_path):
    lines = open(routes_path).readlines()
    p2 = False
    for i, line in enumerate(lines):
        if 'gradio_api_info = api_info(False)' in line and not p2:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (
                ind + 'try:\n' +
                ind + '    gradio_api_info = api_info(False)\n' +
                ind + 'except Exception:\n' +
                ind + '    gradio_api_info = {}\n'
            )
            p2 = True
            print(f"✅ Patch 2: routes.py line {i+1} (api_info wrapped)")
    if not p2:
        print("⚠️  Patch 2 not applied")
    open(routes_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {routes_path}")

# ── Patch 3: gradio/blocks.py — remove localhost health-check ─────────────────
blocks_path = os.path.join(venv_site, 'gradio', 'blocks.py')
if os.path.exists(blocks_path):
    src = open(blocks_path).read()
    if 'health-check disabled' in src:
        print("ℹ️  blocks.py already patched")
    else:
        lines = src.splitlines(keepends=True)
        p3 = False
        i = 0
        while i < len(lines):
            if ('raise ValueError(' in lines[i] and
                    i + 1 < len(lines) and
                    'localhost' in lines[i + 1]):
                n = len(lines[i]) - len(lines[i].lstrip())
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() in (')', ');'):
                        break
                    j += 1
                lines[i:j+1] = [' '*n + 'pass  # health-check disabled\n']
                p3 = True
                print(f"✅ Patch 3: blocks.py line {i+1} (health-check removed)")
                break
            i += 1
        if not p3:
            print("⚠️  Patch 3 not applied")
        open(blocks_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {blocks_path}")

print("Done.")
