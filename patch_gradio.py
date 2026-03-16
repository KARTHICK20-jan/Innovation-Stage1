#!/usr/bin/env python3
"""Patch gradio 4.44.1 for Python 3.14 on Render."""
import sys, os

venv_site = os.path.normpath(os.path.join(
    os.path.dirname(sys.executable), '..', 'lib',
    f'python{sys.version_info.major}.{sys.version_info.minor}',
    'site-packages'
))
print(f"Patching in: {venv_site}")

# ── Patch 1: gradio/routes.py — fix stop_event None + wrap api_info ──────────
routes_path = os.path.join(venv_site, 'gradio', 'routes.py')
if os.path.exists(routes_path):
    lines = open(routes_path).readlines()
    p1a, p1b = False, False
    for i, line in enumerate(lines):
        # Fix stop_event None crash
        if 'await app.stop_event.wait()' in line and not p1a:
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'if app.stop_event is not None:\n' +
                        ind + '    await app.stop_event.wait()\n')
            p1a = True
            print(f"✅ Patch 1a: routes.py line {i+1} (stop_event None guard)")
        # Wrap api_info
        if 'gradio_api_info = api_info(False)' in line and 'try:' not in line and not p1b:
            ind = line[:len(line) - len(line.lstrip())]
            ext = ind + '    '
            lines[i] = (ind + 'try:\n' +
                        ext + 'gradio_api_info = api_info(False)\n' +
                        ind + 'except Exception:\n' +
                        ext + 'gradio_api_info = {}\n')
            p1b = True
            print(f"✅ Patch 1b: routes.py line {i+1} (api_info wrapped)")
    if not p1a: print("ℹ️  routes.py stop_event already patched")
    if not p1b: print("ℹ️  routes.py api_info already patched")
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
