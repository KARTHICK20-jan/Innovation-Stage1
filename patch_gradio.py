#!/usr/bin/env python3
"""
Post-install patcher for gradio 4.44.1 on Python 3.14 / Render.
Fixes:
  1. gradio_client/utils.py line 863 — TypeError: 'bool' not iterable
  2. gradio/blocks.py line ~2465 — ValueError: localhost health-check crash
"""
import sys, os

venv_site = os.path.normpath(os.path.join(
    os.path.dirname(sys.executable), '..', 'lib',
    f'python{sys.version_info.major}.{sys.version_info.minor}',
    'site-packages'
))
print(f"Patching gradio in: {venv_site}")

# ── Patch 1: gradio_client/utils.py ──────────────────────────────────────────
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    src = open(utils_path).read()
    old = '        if "const" in schema:'
    new = '        if isinstance(schema, dict) and "const" in schema:'
    if old in src and new not in src:
        open(utils_path, 'w').write(src.replace(old, new, 1))
        print("✅ Patched gradio_client/utils.py")
    else:
        print("ℹ️  gradio_client/utils.py — already patched or not needed")
else:
    print(f"❌ Not found: {utils_path}")

# ── Patch 2: gradio/blocks.py ─────────────────────────────────────────────────
blocks_path = os.path.join(venv_site, 'gradio', 'blocks.py')
if os.path.exists(blocks_path):
    src = open(blocks_path).read()

    if 'health-check disabled' in src:
        print("ℹ️  gradio/blocks.py — already patched")
    else:
        lines = src.splitlines(keepends=True)
        patched = False
        i = 0
        while i < len(lines):
            # Look for: raise ValueError( on one line
            # followed by the localhost message on the next
            if ('raise ValueError(' in lines[i] and
                    i + 1 < len(lines) and
                    'localhost' in lines[i + 1]):
                # Get exact indent of the raise line
                raise_line = lines[i]
                n_spaces = len(raise_line) - len(raise_line.lstrip())
                indent = ' ' * n_spaces
                # Find the closing ) of the ValueError call
                j = i + 1
                while j < len(lines):
                    s = lines[j].strip()
                    if s == ')' or s == ');':
                        break
                    j += 1
                # Replace raise ValueError(...) block with pass
                lines[i:j + 1] = [indent + 'pass  # health-check disabled\n']
                patched = True
                print("✅ Patched gradio/blocks.py (ValueError removed)")
                break
            i += 1

        if not patched:
            print("⚠️  gradio/blocks.py — target line not found, skipping")

        open(blocks_path, 'w').writelines(lines)
else:
    print(f"❌ Not found: {blocks_path}")

print("Patch complete.")
