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
# This is the highest-level fix — catches ALL errors from get_api_info()
# regardless of what causes them inside utils.py
routes_path = os.path.join(venv_site, 'gradio', 'routes.py')
if os.path.exists(routes_path):
    src = open(routes_path).read()
    old = '        gradio_api_info = api_info(False)'
    new = ('        try:\n'
           '            gradio_api_info = api_info(False)\n'
           '        except Exception:\n'
           '            gradio_api_info = {}\n')
    if old in src and 'except Exception' not in src[src.find(old)-50:src.find(old)+200]:
        src = src.replace(old, new, 1)
        open(routes_path, 'w').write(src)
        print("✅ Patch 1: routes.py api_info wrapped in try/except")
    elif 'except Exception' in src[src.find('api_info')-50:src.find('api_info')+200]:
        print("ℹ️  routes.py already patched")
    else:
        print(f"⚠️  routes.py: target not found")
        # Show the area around api_info
        idx = src.find('api_info(False)')
        if idx > 0:
            print(f"   Found at: {repr(src[idx-20:idx+50])}")
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
        p = False
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
                p = True
                print(f"✅ Patch 2: blocks.py health-check removed")
                break
            i += 1
        if not p:
            print("ℹ️  blocks.py: pattern not found (may already be patched)")
        open(blocks_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {blocks_path}")

print("Done.")
