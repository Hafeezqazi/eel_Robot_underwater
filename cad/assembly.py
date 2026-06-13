"""
assembly.py  --  Full eel kinematic assembly + exports.

Marches a forward-kinematics chain through the 5 revolute (yaw) joints:
head (fixed base) -> seg1 -> ... -> seg5 -> tail fin. Each segment is
placed at its joint pivot and rotated by the CUMULATIVE joint angle, so
feeding a joint-angle vector re-poses the whole body. A servo mock and a
pin are shown at every joint to prove the revolute hardware lines up.

Exports (to ../output):
  * eel_straight.step / .svg   -- all joints at 0 deg
  * eel_swim.step / .svg       -- a mid-stroke travelling-wave S-pose
  * print_*.stl                -- each unique part, flat, ready to slice

Run:  python assembly.py
"""

import os
import math
import cadquery as cq
import params as P
from body import driven_segments, servo_mock
from head_bay import build_head, build_lid
from joints import pin, servo_horn
import dive_planes
import internals


def _hexcol(hx):
    hx = hx.lstrip("#")
    return cq.Color(int(hx[0:2], 16) / 255, int(hx[2:4], 16) / 255,
                    int(hx[4:6], 16) / 255)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")


def _loc(px, pz, theta_deg):
    """Place a part: rotate about Y by theta, then move pivot to (px,0,pz)."""
    return (cq.Location(cq.Vector(px, 0, pz)) *
            cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), theta_deg))


def tail_fin():
    """Passive vertical caudal fin (sweeps water laterally during yaw)."""
    Lf = P.TAILFIN_LEN
    h0 = 2.0 * P.radius_profile(P.TAILFIN_Z)     # root height
    h1 = 1.4 * P.R_MAX                           # tip height (fanned)
    pts = [(0, -h0 / 2), (Lf, -h1 / 2), (Lf, h1 / 2), (0, h0 / 2)]
    return (cq.Workplane(cq.Plane(origin=(0, 0, 0), xDir=(0, 0, 1),
                                  normal=(1, 0, 0)))
            .polyline(pts).close().extrude(1.5, both=True))


def swim_angles(t=0.0):
    """Illustrative joint angles (deg) for a mid-stroke S-pose snapshot.

    Uses ~1.5 spatial waves over the 5 joints so the preview shows the
    characteristic anguilliform S. The flight firmware (firmware/gait.py +
    eel_gait.ino) uses the physically-derived phase offsets, not this.
    """
    # amplitude kept within what the SEGMENT_GAP clears (no shell collision)
    amp = min(7.0, P.JOINT_TRAVEL_DEG)
    out = []
    for i in range(P.N_JOINTS):
        phase = 2 * math.pi * (i / 2.5) - 2 * math.pi * t
        out.append(amp * math.sin(phase))
    return out


def pose(joint_angles_deg, with_internals=True, dive_pitch=0.0,
         internals_geo=False):
    """Build a cq.Assembly of the whole eel at the given joint angles.

    dive_pitch (deg) sets the bow dive-plane angle of attack (+ = dive).
    internals_geo adds the electronics/battery + dive servo (for STEP export).
    """
    assy = cq.Assembly(name="eel")
    assy.add(build_head(), name="head", loc=_loc(0, 0, 0),
             color=cq.Color("seagreen"))
    assy.add(build_lid(), name="lid",
             loc=_loc(0, P.HEAD_LEN - P.LID_LEN, 0), color=cq.Color("gray"))

    # bow dive planes on the transverse shaft (ride on the front body)
    for s in (+1, -1):                                  # +dive_pitch = dive
        pl = (dive_planes.plane(s)
              .rotate((0, 0, 0), (1, 0, 0), -dive_pitch)
              .translate((0, 0, P.DIVE_PLANE_Z)))
        assy.add(pl, name=f"dive_plane_{'R' if s > 0 else 'L'}",
                 color=cq.Color("orange"))
    assy.add(dive_planes.shaft().translate((0, 0, P.DIVE_PLANE_Z)),
             name="dive_shaft", color=cq.Color("gray"))

    px, pz, theta = 0.0, float(P.HEAD_LEN), 0.0   # pivot of joint 1
    for i, (name, sol, part) in enumerate(driven_segments()):
        theta += joint_angles_deg[i]              # cumulative heading
        loc = _loc(px, pz, theta)
        # passive (rear) segments tinted lighter to read as the compliant tail
        col = cq.Color("steelblue") if part["driven"] else cq.Color(0.55, 0.72, 0.92)
        assy.add(sol, name=name, loc=loc, color=col)
        if with_internals:
            if part["driven"]:                    # servo + horn on driven joints
                assy.add(servo_mock(), name=name + "_servo", loc=loc,
                         color=cq.Color("gray"))
                assy.add(servo_horn(), name=name + "_horn", loc=loc,
                         color=cq.Color(0.82, 0.31, 0.63))      # pink horn
            # (passive joints: the rubber-band anchors are printed into the
            #  segment solids themselves -- see body.hang_post)
            assy.add(pin(), name=name + "_pin", loc=loc,
                     color=cq.Color("gold"))
        L = part["z1"] - part["z0"]
        thr = math.radians(theta)
        px += math.sin(thr) * L                   # advance pivot to seg rear
        pz += math.cos(thr) * L
    assy.add(tail_fin(), name="tailfin", loc=_loc(px, pz, theta),
             color=cq.Color("seagreen"))
    if internals_geo:                       # electronics/battery + dive servo
        for it, c, sol in internals.components():
            assy.add(sol, name=it, color=_hexcol(c))
        assy.add(internals.dive_servo(), name="dive_servo",
                 color=cq.Color("gray"))
    return assy


def _svg(shape, path):
    cq.exporters.export(
        shape, path, exportType="SVG",
        opt={"width": 1100, "height": 360, "showAxes": False,
             "projectionDir": (0, 1, 0),          # top-down (swim plane)
             "strokeWidth": 0.4, "showHidden": False})


def export_prints():
    """One STL per unique printable part, in its own (unposed) frame."""
    parts = {p["name"]: p for p in P.segment_table()}
    items = {"head": build_head(), "lid": build_lid(),
             "tailfin": tail_fin(), "pin": pin(),
             "dive_plane": dive_planes.plane(+1),
             "dive_shaft": dive_planes.shaft(),
             "dive_crank": dive_planes.dive_crank()}
    for name, sol, part in driven_segments():
        items[name] = sol
    for name, sol in items.items():
        path = os.path.normpath(os.path.join(OUT, "print_" + name + ".stl"))
        cq.exporters.export(sol, path)
    return list(items.keys())


def main():
    # straight
    a0 = pose([0, 0, 0, 0, 0])
    _svg(a0.toCompound(), os.path.normpath(os.path.join(OUT, "eel_straight.svg")))
    pose([0, 0, 0, 0, 0], internals_geo=True).export(
        os.path.normpath(os.path.join(OUT, "eel_straight.step")))
    # swim snapshot
    sw = swim_angles()
    a1 = pose(sw)
    _svg(a1.toCompound(), os.path.normpath(os.path.join(OUT, "eel_swim.svg")))
    pose(sw, internals_geo=True).export(
        os.path.normpath(os.path.join(OUT, "eel_swim.step")))
    # print parts
    printed = export_prints()

    bb = a0.toCompound().BoundingBox()
    print("=" * 56)
    print("EEL ASSEMBLY EXPORTED")
    print("=" * 56)
    print(f"  parts in assembly : head, lid, seg1-3 (driven) + seg4-5 (passive),"
          f" {P.N_DRIVEN}x servo, {P.N_JOINTS}x pin, tailfin")
    print(f"  straight bbox     : {bb.xlen:.0f} x {bb.ylen:.0f} x "
          f"{bb.zlen:.0f} mm (X,Y,Z)")
    print(f"  swim joint angles : "
          f"{[round(a, 1) for a in sw]} deg (cumulative pose)")
    print(f"  printable STLs    : {len(printed)} -> print_*.stl")
    print(f"  STEP + SVG (top)  : eel_straight.*, eel_swim.*")
    print("=" * 56)


if __name__ == "__main__":
    main()
