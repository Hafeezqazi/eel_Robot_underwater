"""
verify_all.py  --  Run the whole design pipeline and report PASS/FAIL.

One command to confirm every script still runs and produces its outputs after a
change. Order matters: the analysis scripts write output/*_report.txt FIRST, then
the consolidated design page embeds them. Run:  python verify_all.py
(exit code 0 = all pass; non-zero = something broke.)
"""

import os
import sys
import time
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# dependency order: analysis (reports) -> firmware -> CAD parts/exports ->
# CFD case -> consolidated pages/renders (which consume the above)
ORDER = [
    "cad/params.py",
    "analysis/sizing.py", "analysis/structures.py", "analysis/stability.py",
    "analysis/power.py", "analysis/tail_stiffness.py", "analysis/dive.py",
    "analysis/dive_linkage.py", "analysis/swim_sim.py",
    "firmware/gait.py",
    "cad/body.py", "cad/joints.py", "cad/head_bay.py", "cad/dive_planes.py",
    "cad/internals.py", "cad/skin.py", "cad/hull_solid.py", "cad/assembly.py",
    "cad/test_rig.py", "cad/joint_detail.py",
    "cad/test_coupons.py", "cad/ballast.py", "cad/tail_flexure.py",
    "cfd/case_setup.py",
    "cad/design_page.py", "cad/web_viewer.py", "cad/render.py", "cad/render3d.py",
]


def run(rel):
    path = os.path.join(HERE, *rel.split("/"))
    if not os.path.exists(path):
        return ("MISS", 0.0, "file not found")
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, path], capture_output=True,
                           text=True, timeout=420)
    except subprocess.TimeoutExpired:
        return ("TIME", time.time() - t0, "exceeded 420 s")
    dt = time.time() - t0
    if p.returncode == 0:
        return ("PASS", dt, "")
    err = (p.stderr or p.stdout or "").strip().splitlines()
    return ("FAIL", dt, err[-1] if err else f"exit {p.returncode}")


def main():
    print("=" * 64)
    print("EEL ROBOT  --  full pipeline verification")
    print("=" * 64)
    fails, misses = [], []
    for rel in ORDER:
        status, dt, msg = run(rel)
        mark = {"PASS": "PASS", "FAIL": "FAIL", "TIME": "TIME",
                "MISS": "MISS"}[status]
        print(f"  {mark}  {rel:28s} {dt:6.1f}s  {msg}")
        if status == "FAIL" or status == "TIME":
            fails.append(rel)
        elif status == "MISS":
            misses.append(rel)
    print("=" * 64)
    n = len(ORDER)
    print(f"{n - len(fails) - len(misses)}/{n} passed"
          + (f", {len(fails)} FAILED: {', '.join(fails)}" if fails else "")
          + (f", {len(misses)} missing" if misses else ""))
    print("=" * 64)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
