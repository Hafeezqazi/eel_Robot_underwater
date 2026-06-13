"""
open_in_solidworks.py  --  Launch SolidWorks (via COM) and import the parts.

Quick one-shot bridge: connects to SolidWorks through its COM API (pywin32),
makes it visible, and imports the STEP assembly so you can see the whole
robot. No MCP server needed for this. SolidWorks must be installed.

Run on the Windows machine that has SolidWorks:
    python open_in_solidworks.py
(If SolidWorks isn't already running it will be launched -- first start can
take 30-90 s. Dismiss any SolidWorks license/startup dialog if it appears.)
"""

import os
import sys
import time
import win32api
import win32com.client.dynamic   # LATE binding (required for SW pass-by-ref args)

OUT = r"D:\Codex_Projects\test_game_claude\eel_robot\output"

# Which file(s) to load. Default = the whole robot assembly. Override from the
# command line, e.g.:
#     python open_in_solidworks.py                 -> eel_straight.step (whole robot)
#     python open_in_solidworks.py eel_swim.step   -> the swimming pose
#     python open_in_solidworks.py cfd_hull.step   -> just the smooth hull
# STEP files work via the shell-import path; STL may open in a mesh viewer.
TARGETS = sys.argv[1:] or ["eel_straight.step"]


def _call(obj, name, *args):
    """Call a SW member whether late-binding resolved it as method or property."""
    v = getattr(obj, name)
    return v(*args) if callable(v) else v


def _connect():
    """Late-binding connect; SW rejects early-bound pass-by-ref out-params."""
    sw = win32com.client.dynamic.Dispatch("SldWorks.Application")
    sw.Visible = True
    return sw


def _open(sw, path, timeout=60):
    """SW-2025 STEP import via the Windows shell handler (OpenDoc6 is broken
    for foreign formats on 2025). Poll GetDocumentCount, grab ActiveDoc."""
    n0 = int(_call(sw, "GetDocumentCount"))
    win32api.ShellExecute(0, "open", path, None, None, 1)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(0.5)
        try:
            if int(_call(sw, "GetDocumentCount")) > n0:
                time.sleep(1.0)            # settle: SW marks active before done
                return sw.ActiveDoc
        except Exception:
            continue
    return None


def main():
    print("Connecting to SolidWorks (launches it if needed; first start ~30-90 s)...")
    sw = _connect()
    print("SolidWorks connected. Version:", sw.RevisionNumber)
    time.sleep(4)

    for name in TARGETS:
        path = os.path.join(OUT, name)
        if not os.path.exists(path):
            print(f"  [skip] not found: {path}")
            continue
        doc = _open(sw, path)
        if doc is None:
            print(f"  [fail] {name}: could not import (RPC). If a SolidWorks "
                  f"dialog is open, close it and re-run in your own terminal.")
        else:
            print(f"  [ok]   imported {name}")
            try:
                _call(doc, "ShowNamedView2", "*Isometric", 7)
                _call(doc, "ViewZoomtofit2")
            except Exception as e:
                print("         (view fit note:", e, ")")
    print("Done — SolidWorks should be showing the robot. Rotate with the "
          "middle mouse button; the tree on the left lists every solid body.")


if __name__ == "__main__":
    main()
