"""
internals.py  --  Internal layout: dive servo + electronics/battery placement.

These were missing from the model. This module adds:
  * the dive-plane servo (the 4th and last servo) at the dive shaft, and
  * the electronics stack INSIDE the head bay (battery, ESP32, PCA9685, IMU,
    depth sensor, buck) on a tray that slides in from the rear lid.

All in HEAD/BASE-frame coords (z = body axis, 0..HEAD_LEN; x lateral; y up).
Sizes are realistic module footprints; tweak to your exact parts. Consumed by
assembly.py, web_viewer.py and design_page.py so every view shows them.
"""

import cadquery as cq
import params as P


def _box(dx, dy, dz, pos):
    return cq.Workplane("XY").box(dx, dy, dz).translate(pos)


# (item-id, colour, solid)  -- electronics + tray, in head-bay coords
def components():
    C = []
    C.append(("tray",   "#3a4150", _box(40, 3, 78, (0, -15, 74))))
    C.append(("battery", "#c0392b", _box(26, 16, 46, (0, -5, 80))))
    C.append(("esp32",  "#2d6cdf", _box(20, 9, 44, (-18, 6, 72))))
    C.append(("pca9685", "#27ae60", _box(20, 7, 44, (18, 6, 72))))
    C.append(("mpu6050", "#8e44ad", _box(15, 6, 15, (0, 15, 52))))
    C.append(("buck",   "#e67e22", _box(16, 9, 16, (0, 14, 100))))
    # depth sensor: mounts on the lid end cap, face epoxied into the lid's
    # sensor port (gel side to the water in the flooded seg1 behind)
    C.append(("ms5837", "#16a085",
              cq.Workplane("XY").cylinder(8, 8).translate((P.SENSOR_PORT_X,
                                                           0, 129))))
    # FPV camera + LED headlight: look forward through the nose window
    C.append(("camera", "#222a36",
              _box(16, 16, 20, (0, 3, P.WINDOW_Z + 15))))
    C.append(("led", "#f5d76e",
              cq.Workplane("XY").cylinder(4, 4).translate((0, -7,
                                                           P.WINDOW_Z + 7))))
    # --- stability hardware (from analysis/stability.py) ---
    # lead KEEL: low + forward, drops CG for roll & sets trim. Compact block
    # (~same lead volume) sized so it stays BEHIND the nose face (z>=WINDOW_Z)
    # instead of spiking out the front; centroid unchanged -> stability identical.
    C.append(("keel", "#2b2b2b",
              _box(26, 16, 42, (0, P.KEEL_Y, P.KEEL_Z))))
    # NB: the buoyancy FOAM is NOT here -- it's a bore-fitting plug that lives
    # inside a flexing body segment, so callers add foam_plug() to that
    # segment's group (see design_page.build_geo) rather than the static frame.
    return C


def foam_plugs():
    """Closed-cell buoyancy foam discs shaped to the bore: tapered plugs that
    slide INSIDE the free-flooding cones (rear-mid bays). Returns
    [(z_centre, solid)] with each solid centred at LOCAL z=0 so the caller drops
    it into the segment that spans z_centre -- it then bends with that segment
    instead of floating in the base frame. Frustum follows the body taper
    (wider front face); volumes sum to P.FOAM_VOL."""
    out = []
    for zc, length, r0, r1, _vol in P.FOAM_PLUGS:
        half = length / 2.0
        s = (cq.Workplane("XY")
             .circle(r0).workplane(offset=length).circle(r1).loft(combine=True)
             .translate((0, P.FOAM_Y, -half)))
        out.append((zc, s))
    return out


# the dive servo (4th): drives the dive-plane shaft (axis X), sits just below
# the shaft at DIVE_PLANE_Z. Returned in BASE-frame coords.
def dive_servo():
    # sits AFT of the joint-1 servo (which occupies the seg1 front, ~z140-163)
    # so they don't overlap; drives the dive shaft at DIVE_PLANE_Z via a short
    # forward crank/link.
    return _box(22, 17, 13, (-3, -9, P.DIVE_PLANE_Z + 12))


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "output")
    comp = cq.Workplane("XY")
    for _, _, s in components():
        comp = comp.union(s)
    comp = comp.union(dive_servo())
    for zc, s in foam_plugs():                       # foam discs at their bays
        comp = comp.union(s.translate((0, 0, zc)))
    path = os.path.normpath(os.path.join(out, "internals_layout.stl"))
    cq.exporters.export(comp, path)
    print(f"[ok] {len(components())} components + dive servo -> {path}")
