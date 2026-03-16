#!/usr/bin/env python3
"""
Post-install patcher for gradio 4.44.1 on Python 3.14 / Render
Fixes two bugs that prevent the app from running:
1. gradio_client/utils.py: TypeError when schema is bool
2. gradio/blocks.py: ValueError health-check that kills the process
"""
import sys, os

venv_site = os.path.join(os.path.dirname(sys.executable), '..', 'lib',
                          f'python{sys.version_info.major}.{sys.version_info.minor}',
                          'site-packages')
venv_site = os.path.normpath(venv_site)
print(f"Patching gradio in: {venv_site}")

# ── Patch 1: gradio_client/utils.py ─────────────────────────────────────────
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    with open(utils_path, 'r') as f:
        src = f.read()
    old = '        if "const" in schema:'
    new = '        if isinstance(schema, dict) and "const" in schema:'
    if old in src and new not in src:
        src = src.replace(old, new, 1)
        with open(utils_path, 'w') as f:
            f.write(src)
        print("✅ Patched gradio_client/utils.py (bool-schema TypeError)")
    else:
        print("ℹ️  gradio_client/utils.py already patched or different version")
else:
    print(f"❌ Not found: {utils_path}")

# ── Patch 2: gradio/blocks.py ────────────────────────────────────────────────
blocks_path = os.path.join(venv_site, 'gradio', 'blocks.py')
if os.path.exists(blocks_path):
    with open(blocks_path, 'r') as f:
        src = f.read()
    # Remove the localhost health-check ValueError
    old = ('                if not self.share:\n'
           '                    raise ValueError(\n'
           '                        "When localhost is not accessible, a shareable link must be created. '
           'Please set share=True or check your proxy settings to allow access to localhost."\n'
           '                    )\n')
    new = '                pass  # health-check disabled for Render\n'
    if old in src:
        src = src.replace(old, new, 1)
        with open(blocks_path, 'w') as f:
            f.write(src)
        print("✅ Patched gradio/blocks.py (localhost health-check)")
    else:
        # Try line-by-line approach
        lines = src.splitlines()
        patched = False
        for i, line in enumerate(lines):
            if 'raise ValueError(' in line and i > 0:
                prev = lines[i-1] if i > 0 else ''
                if 'not self.share' in prev or (i > 1 and 'not self.share' in lines[i-2]):
                    # Check if next lines contain the localhost message
                    block = ' '.join(lines[i:i+4])
                    if 'localhost' in block and 'shareable' in block:
                        # Remove lines i-1 through i+3
                        end = i + 1
                        while end < len(lines) and (')' not in lines[end] or lines[end].strip() == ')'):
                            end += 1
                        lines[i-1:end+1] = ['                pass  # health-check disabled']
                        src = '\n'.join(lines)
                        with open(blocks_path, 'w') as f:
                            f.write(src)
                        print("✅ Patched gradio/blocks.py via line search")
                        patched = True
                        break
        if not patched:
            print("ℹ️  gradio/blocks.py: pattern not found, may already be patched")
else:
    print(f"❌ Not found: {blocks_path}")

print("Done.")
