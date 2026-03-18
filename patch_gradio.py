#!/usr/bin/env python3
"""Patch gradio 4.44.1 + dependencies for Python 3.14 on Render."""
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
    except Exception as e:
        print(f"   compile warning: {e}")

# ── Patch 1: pydub/utils.py ───────────────────────────────────────────────────
pydub_path = os.path.join(venv_site, 'pydub', 'utils.py')
if os.path.exists(pydub_path):
    lines = open(pydub_path).readlines()
    for i, line in enumerate(lines):
        if line.strip() == 'import pyaudioop as audioop':
            ind = line[:len(line) - len(line.lstrip())]
            lines[i] = (ind + 'try:\n' +
                        ind + '    import pyaudioop as audioop\n' +
                        ind + 'except ImportError:\n' +
                        ind + '    audioop = None\n')
            open(pydub_path, 'w').writelines(lines)
            delete_pyc(pydub_path)
            print("✅ pydub/utils.py pyaudioop fix")
            break
    else:
        print("ℹ️  pydub already patched")

# ── Patch 2: gradio/blocks.py ─────────────────────────────────────────────────
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
            print("✅ blocks.py health-check removed")
        elif not p2 and 'raise DeprecationWarning(' in lines[i] and i+1 < len(lines) and 'concurrency_count' in lines[i+1]:
            n = len(lines[i]) - len(lines[i].lstrip())
            j = i+1
            while j < len(lines) and lines[j].strip() not in (')', ');'): j += 1
            lines[i:j+1] = [' '*n + 'pass  # DeprecationWarning disabled\n']
            p2 = True
            print("✅ blocks.py DeprecationWarning removed")
        if p1 and p2: break
        i += 1
    if not p1: print("ℹ️  blocks.py health-check already patched")
    if not p2: print("ℹ️  blocks.py DeprecationWarning already patched")
    open(blocks_path, 'w').writelines(lines)
    delete_pyc(blocks_path)

# ── Patch 3: gradio_client/utils.py ──────────────────────────────────────────
# Fix ALL crash points in the call chain by patching _json_schema_to_python_type
# to guard against non-dict schema at the very start
utils_path = os.path.join(venv_site, 'gradio_client', 'utils.py')
if os.path.exists(utils_path):
    lines = open(utils_path).readlines()
    
    # Find _json_schema_to_python_type function and insert guard at top
    changed = False
    for i, line in enumerate(lines):
        if 'def _json_schema_to_python_type(schema' in line and not changed:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and 'not isinstance' not in lines[j]:
                ind = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                lines.insert(j, ind + 'if not isinstance(schema, dict): return "str"\n')
                changed = True
                print("✅ utils.py _json_schema_to_python_type guard inserted")
            else:
                print("ℹ️  utils.py _json_schema_to_python_type already guarded")
            break

    # Also guard get_type
    for i, line in enumerate(lines):
        if 'def get_type(schema' in line:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and 'not isinstance' not in lines[j]:
                ind = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                lines.insert(j, ind + 'if not isinstance(schema, dict): return "str"\n')
                changed = True
                print("✅ utils.py get_type guard inserted")
            else:
                print("ℹ️  utils.py get_type already guarded")
            break

    # Also guard json_schema_to_python_type (top-level entry)
    for i, line in enumerate(lines):
        if 'def json_schema_to_python_type(schema' in line:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and 'not isinstance' not in lines[j]:
                ind = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                lines.insert(j, ind + 'if not isinstance(schema, dict): return "str"\n')
                changed = True
                print("✅ utils.py json_schema_to_python_type guard inserted")
            else:
                print("ℹ️  utils.py json_schema_to_python_type already guarded")
            break

    if not changed:
        print("ℹ️  utils.py all already patched")
    open(utils_path, 'w').writelines(lines)
    delete_pyc(utils_path)

# ── Patch 4: gradio/routes.py ─────────────────────────────────────────────────
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
            print("✅ routes.py stop_event guard")
        if not p5 and '"Content-Type": "text/event-stream"' in line:
            lines[i] = line.replace(
                '"Content-Type": "text/event-stream"',
                '"Content-Type": "text/event-stream", "X-Accel-Buffering": "no", "Cache-Control": "no-cache"'
            )
            p5 = True
            print("✅ routes.py SSE headers")
    if not p4: print("ℹ️  routes.py stop_event already patched")
    if not p5: print("ℹ️  routes.py SSE headers already patched")
    open(routes_path, 'w').writelines(lines)
    delete_pyc(routes_path)


# ── Patch 5: gradio/queueing.py — ALL async locks/events ─────────────────────
# Queue.__init__ sets ALL async primitives to None (Lock, Event, etc.).
# They are only created inside Queue.start() which runs as an async coroutine
# AFTER the server starts. On Render, requests arrive before start() completes,
# causing TypeError: 'NoneType' does not support the asynchronous context manager.
#
# Known None attributes in gradio 4.44.1 Queue:
#   pending_message_lock, delete_lock, server_app (and possibly others)
#
# Strategy: Scan queueing.py for EVERY pattern of the form
#   `async with self.<attr>:` or `await self.<attr>.wait()`
# and inject a guard before each one that creates the primitive if None.

queueing_path = os.path.join(venv_site, 'gradio', 'queueing.py')
if os.path.exists(queueing_path):
    src = open(queueing_path).read()

    if '# RENDER_ALL_LOCKS_PATCHED' not in src:
        import re as _re

        lines = src.splitlines(keepends=True)
        new_lines = []
        patch_count = 0

        for line in lines:
            stripped = line.lstrip()
            ind = line[:len(line) - len(stripped)]

            # Pattern 1: `async with self.<attr>:` → Lock guard
            m = _re.match(r'async with self\.(\w+):', stripped)
            if m:
                attr = m.group(1)
                new_lines.append(ind + f'if getattr(self, "{attr}", None) is None:\n')
                new_lines.append(ind + f'    import asyncio as _aq; self.{attr} = _aq.Lock()\n')
                patch_count += 1

            # Pattern 2: `await self.<attr>.wait()` → Event guard
            m2 = _re.match(r'await self\.(\w+)\.wait\(\)', stripped)
            if m2:
                attr = m2.group(1)
                new_lines.append(ind + f'if getattr(self, "{attr}", None) is None:\n')
                new_lines.append(ind + f'    import asyncio as _aq; self.{attr} = _aq.Event()\n')
                patch_count += 1

            # Pattern 3: `await self.<attr>.set()` or `.clear()` → Event guard
            m3 = _re.match(r'(?:await )?self\.(\w+)\.(set|clear)\(\)', stripped)
            if m3:
                attr = m3.group(1)
                new_lines.append(ind + f'if getattr(self, "{attr}", None) is None:\n')
                new_lines.append(ind + f'    import asyncio as _aq; self.{attr} = _aq.Event()\n')
                patch_count += 1

            new_lines.append(line)

        # Add sentinel so we don't double-patch
        new_lines.insert(0, '# RENDER_ALL_LOCKS_PATCHED\n')

        open(queueing_path, 'w').writelines(new_lines)
        delete_pyc(queueing_path)
        print(f"✅ queueing.py: {patch_count} async primitive guards inserted")
    else:
        print("ℹ️  queueing.py already fully patched")
else:
    print("ℹ️  queueing.py not found — skipping")

print("All patches done.")
