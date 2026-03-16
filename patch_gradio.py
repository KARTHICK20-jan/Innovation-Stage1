#!/usr/bin/env python3
"""Patch gradio 4.44.1 for Python 3.14 on Render."""
import sys, os

venv_site = os.path.normpath(os.path.join(
    os.path.dirname(sys.executable), '..', 'lib',
    f'python{sys.version_info.major}.{sys.version_info.minor}',
    'site-packages'
))
print(f"Patching in: {venv_site}")

# ── Patch 1: gradio/routes.py — wrap api_info in try/except ──────────────────
routes_path = os.path.join(venv_site, 'gradio', 'routes.py')
if os.path.exists(routes_path):
    lines = open(routes_path).readlines()
    p1 = False
    for i, line in enumerate(lines):
        if 'gradio_api_info = api_info(False)' in line and 'try:' not in line:
            indent = line[:len(line) - len(line.lstrip())]
            extra  = indent + '    '
            lines[i] = (
                indent + 'try:\n' +
                extra  + 'gradio_api_info = api_info(False)\n' +
                indent + 'except Exception:\n' +
                extra  + 'gradio_api_info = {}\n'
            )
            p1 = True
            print(f"✅ Patch 1: routes.py line {i+1} (api_info wrapped)")
            break
    if not p1:
        print("ℹ️  routes.py already patched")
    open(routes_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {routes_path}")

# ── Patch 2: gradio/blocks.py — remove localhost health-check ─────────────────
blocks_path = os.path.join(venv_site, 'gradio', 'blocks.py')
if os.path.exists(blocks_path):
    src = open(blocks_path).read()
    if 'health-check disabled' in src:
        print("ℹ️  blocks.py already patched")
    else:
        lines = src.splitlines(keepends=True)
        p2, i = False, 0
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
                p2 = True
                print(f"✅ Patch 2: blocks.py health-check removed")
                break
            i += 1
        if not p2:
            print("ℹ️  blocks.py already patched")
        open(blocks_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {blocks_path}")

print("Done.")
