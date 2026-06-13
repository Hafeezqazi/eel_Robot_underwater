"""
head_bay.py  --  Sealed dry electronics bay (the eel's head, segment 0).

Unlike the free-flooding body segments, the head is WATERTIGHT: it houses
the MCU, battery buffer, IMU, depth sensor, CAMERA and LED light. Features:
  * elliptical-ogive nose TRUNCATED at WINDOW_Z into a flat face with a
    recessed seat for a clear acrylic disc -- the camera + headlight look
    out through it from inside the dry bay (no extra waterproofing);
  * internal dry cavity (wall = BAY_WALL);
  * plain rear bore that accepts a removable LID (the O-ring rides in a
    groove on the LID plug -- one groove, one seal, BlueROV-style);
  * the LID carries the joint-1 TONGUE that plugs into seg1's clevis, so
    unpinning joint 1 lets the lid (and the electronics tray behind it)
    slide straight out;
  * THREE lid penetrations: tether penetrator (offset +Y above the tongue),
    servo/leak-probe wire gland (offset -Y, potted with epoxy), and the
    MS5837 depth-sensor port (offset +X, sensor face epoxied in, gel side
    to the water).

The head is the fixed BASE of the kinematic chain (no driven joint at its
front). Run directly to export the head + lid:
    python head_bay.py   ->  output/head.stl, output/lid.stl
"""

import os
import math
import cadquery as cq
import params as P
from joints import tongue

NOSE_R = P.radius_profile(0.0)          # 3 mm rounded tip (R_NOSE_TIP)
REAR_R = P.radius_profile(P.HEAD_LEN)   # 35 mm


def _loft_profile(z0, z1, radii_fn, n=16):
    """Multi-section loft following radii_fn(z) -> smooth ogive (not a cone)."""
    dz = (z1 - z0) / n
    wp = cq.Workplane("XY", origin=(0, 0, z0))
    for i in range(n + 1):
        wp = wp.circle(max(radii_fn(z0 + i * dz), 0.6))
        if i < n:
            wp = wp.workplane(offset=dz)
    return wp.loft(combine=True)


# front wall behind the window seat: seat depth + a 2 mm lip the acrylic
# disc bonds onto (the Ø WINDOW_BORE_D aperture punches through the lip)
WINDOW_WALL = P.WINDOW_SEAT_T + 2.0


def build_head():
    L = P.HEAD_LEN
    # outer body follows the ELLIPTICAL nose profile (smooth, low-drag),
    # TRUNCATED at WINDOW_Z into the flat camera-window face. The loft
    # simply starts at WINDOW_Z, which leaves the flat front disc.
    outer = _loft_profile(P.WINDOW_Z, L, P.radius_profile)

    # dry cavity: starts behind the window wall, open rear (to z=L).
    # The rear bore is PLAIN -- the O-ring groove lives on the lid plug
    # (one groove, one seal; a second groove in the bore would only add a
    # leak path and confuse assembly).
    cav = _loft_profile(P.WINDOW_Z + WINDOW_WALL, L,
                        lambda z: P.radius_profile(z) - P.BAY_WALL)
    head = outer.cut(cav)

    # camera window: recessed seat for the acrylic disc (flush with the
    # face, epoxy-bonded) + clear aperture through the lip into the bay
    seat = (cq.Workplane("XY", origin=(0, 0, P.WINDOW_Z))
            .circle(P.WINDOW_SEAT_D / 2.0).extrude(P.WINDOW_SEAT_T))
    bore = (cq.Workplane("XY", origin=(0, 0, P.WINDOW_Z - 1.0))
            .circle(P.WINDOW_BORE_D / 2.0).extrude(WINDOW_WALL + 2.0))
    head = head.cut(seat).cut(bore)

    # lid-clamp bolt ears on the rear rim: M3 into brass heat-set inserts. The
    # radial O-ring seals with NO clamp force and the joint-1 pin is the primary
    # axial retention; these ears positively lock the lid against handling/rock
    # and the drivetrain pull on the flange (so it is NOT O-ring friction).
    for i in range(P.LID_BOLTS):
        a = math.radians(90.0 + i * 360.0 / P.LID_BOLTS)
        x, y = P.LID_BOLT_PCR * math.cos(a), P.LID_BOLT_PCR * math.sin(a)
        ear = (cq.Workplane("XY", origin=(x, y, L - P.LID_EAR_LEN))
               .circle(P.LID_EAR_R).extrude(P.LID_EAR_LEN))
        head = head.union(ear)                         # boss forward of the rim
        head = head.cut(cq.Workplane("XY", origin=(x, y, L - P.LID_INSERT_DEPTH))
                        .circle(P.LID_INSERT_D / 2).extrude(P.LID_INSERT_DEPTH + 0.2))

    return head


def build_lid():
    """Removable rear lid: plug + rim O-ring groove + penetrator + tongue.

    Carries the joint-1 TONGUE on its rear face: the whole drivetrain pulls
    on the lid flange (large bearing area), and removing the lid is possible
    in the first place -- a tongue fixed to the head rim would sit right in
    the lid's exit path AND in front of the tether penetrator.
    """
    bore_r = REAR_R - P.BAY_WALL
    plug_r = bore_r - 0.2                      # slip fit into the bore
    lid = cq.Workplane("XY").circle(plug_r).extrude(P.LID_LEN)
    # outer flange cap so the lid can't push in past the rim
    flange = (cq.Workplane("XY", origin=(0, 0, P.LID_LEN - 3.0))
              .circle(REAR_R).extrude(3.0))
    lid = lid.union(flange)
    # rim O-ring groove (the single sealing groove of the bay)
    g_outer = (cq.Workplane("XY", origin=(0, 0, P.LID_LEN / 2 - P.ORING_GROOVE_W / 2))
               .circle(plug_r).extrude(P.ORING_GROOVE_W))
    g_inner = (cq.Workplane("XY", origin=(0, 0, P.LID_LEN / 2 - P.ORING_GROOVE_W / 2))
               .circle(plug_r - P.ORING_GROOVE_D).extrude(P.ORING_GROOVE_W))
    lid = lid.cut(g_outer.cut(g_inner))
    # hollow it into a cup (3 mm side wall, 5 mm end cap) -> light, holds tray
    lid = lid.cut(cq.Workplane("XY", origin=(0, 0, -0.1))
                  .circle(plug_r - 3.0).extrude(P.LID_LEN - 5.0))
    # tether penetrator bore (axial, offset above the tongue so the cable
    # exits clear of the joint-1 blade)
    lid = lid.cut(cq.Workplane("XY", origin=(0, P.PENETRATOR_OFF_Y, 0))
                  .circle(P.PENETRATOR_D / 2)
                  .extrude(P.LID_LEN + 6.0))
    # servo / leak-probe wire gland (below the tongue; pot solid with epoxy)
    lid = lid.cut(cq.Workplane("XY", origin=(0, -P.PENETRATOR_OFF_Y, 0))
                  .circle(P.WIRE_GLAND_D / 2)
                  .extrude(P.LID_LEN + 6.0))
    # MS5837 depth-sensor port (sensor face epoxied in from the dry side,
    # gel side open to the water)
    lid = lid.cut(cq.Workplane("XY", origin=(P.SENSOR_PORT_X, 0, 0))
                  .circle(P.SENSOR_PORT_D / 2)
                  .extrude(P.LID_LEN + 6.0))
    # joint-1 tongue on the rear face (plugs into seg1's clevis)
    lid = lid.union(tongue().translate((0, 0, P.LID_LEN)))

    # matching lid-clamp tabs: small bosses projecting rearward from the flange
    # (into the head<->seg1 gap) with M3 clearance holes that line up with the
    # head-rim insert ears -> 3 cap screws bolt the lid to the head positively.
    for i in range(P.LID_BOLTS):
        a = math.radians(90.0 + i * 360.0 / P.LID_BOLTS)
        x, y = P.LID_BOLT_PCR * math.cos(a), P.LID_BOLT_PCR * math.sin(a)
        tab = (cq.Workplane("XY", origin=(x, y, P.LID_LEN))
               .circle(P.LID_EAR_R).extrude(P.LID_EAR_TAB))
        lid = lid.union(tab)
        lid = lid.cut(cq.Workplane("XY", origin=(x, y, P.LID_LEN - 2.0))
                      .circle(P.LID_BOLT_CLR_D / 2).extrude(P.LID_EAR_TAB + 4.0))
    return lid


def _test():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    head, lid = build_head(), build_lid()
    for name, sol in (("head", head), ("lid", lid)):
        path = os.path.normpath(os.path.join(out_dir, name + ".stl"))
        cq.exporters.export(sol, path)
        vol = sol.val().Volume() / 1000.0
        print(f"[ok] {name}: volume {vol:6.1f} cm^3  -> {path}")

    # lid-clamp section render: head + lid assembled, side projection so the
    # bolt ears + their rear screw access are visible (Codex review C2-P1-3).
    asm = head.union(lid.translate((0, 0, P.HEAD_LEN - P.LID_LEN)))
    svg = os.path.normpath(os.path.join(out_dir, "lid_clamp.svg"))
    cq.exporters.export(asm, svg, opt={"projectionDir": (0, -1, 0),
                                       "showHidden": True, "width": 800})
    print(f"[ok] lid-clamp section -> {svg}")


if __name__ == "__main__":
    _test()
