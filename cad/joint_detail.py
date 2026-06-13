"""
joint_detail.py  --  Exploded close-up of ONE joint, so the connection is clear.

Renders two shaded 3-D panels:
  * DRIVEN joint: tongue + clevis + pin + servo + horn, pulled apart, showing
    how the servo's arm (horn) bolts to the tongue.
  * PASSIVE joint: tongue + clevis + pin + 2 rubber-band posts (no servo).

Run:  python joint_detail.py  ->  output/joint_detail.png
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import joints as J
import params as P
import dive_planes as DP
from body import servo_mock, servo_mount, build_segment

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
LIGHT = np.array([0.35, 0.5, 0.78]); LIGHT = LIGHT / np.linalg.norm(LIGHT)

C = {"tongue": "#e0a020", "clevis": "#3a6ea5", "pin": "#c9d2db",
     "servo": "#6b6f76", "horn": "#d14fa0", "post": "#2f9e6e"}   # horn = pink (stands out)
BG = "#0d1117"


def _tris(sol, off=(0, 0, 0), tol=0.4):
    s = sol.val() if hasattr(sol, "val") else sol
    v, t = s.tessellate(tol)
    V = np.array([[p.x + off[0], p.y + off[1], p.z + off[2]] for p in v])
    return V, np.array(t)


def _draw(ax, parts, title, elev=22, azim=-60):
    polys, cols = [], []
    for item in parts:
        sol, rgb, off = item[0], item[1], item[2]
        alpha = item[3] if len(item) > 3 else 1.0
        V, T = _tris(sol, off)
        if len(T) == 0:
            continue
        tri = V[T]                                   # (n,3,3) -> remap to Z,X,Y
        tri = tri[:, :, [2, 0, 1]]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
        inten = 0.5 + 0.5 * np.clip(np.abs((n / ln) @ LIGHT), 0, 1)
        base = np.array([int(rgb[1:3], 16), int(rgb[3:5], 16),
                         int(rgb[5:7], 16)]) / 255.0
        rgba = np.concatenate([np.clip(base[None] * inten[:, None], 0, 1),
                               np.full((len(inten), 1), alpha)], axis=1)
        polys.append(tri); cols.append(rgba)
    Pp = np.concatenate(polys); CC = np.concatenate(cols)
    ax.add_collection3d(Poly3DCollection(Pp, facecolors=CC, edgecolors="none"))
    pts = Pp.reshape(-1, 3); mn = pts.min(0); mx = pts.max(0)
    ax.set_xlim(mn[0], mx[0]); ax.set_ylim(mn[1], mx[1]); ax.set_zlim(mn[2], mx[2])
    ax.set_box_aspect(mx - mn); ax.view_init(elev=elev, azim=azim)
    ax.set_facecolor(BG)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor(BG); axis.pane.set_edgecolor(BG)
        axis.line.set_color(BG)
    ax.set_axis_off()
    ax.set_title(title, fontsize=12, color="#e8eef5")


def main():
    fig = plt.figure(figsize=(13, 6))

    # --- DRIVEN joint, exploded ---
    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    driven = [
        (J.clevis(),     C["clevis"], (0, 0, 0)),       # aft fork
        (J.tongue(),     C["tongue"], (0, 0, -34)),      # forward blade pulled out
        (J.servo_horn(), C["horn"],   (0, 22, -34)),     # horn above tongue
        (J.pin(),        C["pin"],    (0, 34, 6)),        # pin pulled up
        (servo_mock(),   C["servo"],  (0, -40, 0)),       # servo pulled down
    ]
    _draw(ax1, driven, "DRIVEN joint (front 3)  —  exploded")
    leg1 = [Line2D([0], [0], marker='s', ls='', mfc=C[k], mec='none', ms=11,
                   label=v) for k, v in [("tongue", "tongue (segment B)"),
            ("clevis", "clevis (segment A)"), ("pin", "pin = hinge"),
            ("servo", "servo (in A)"), ("horn", "horn → bolts to tongue")]]
    ax1.legend(handles=leg1, loc="upper center", bbox_to_anchor=(0.5, 0.04),
               ncol=2, fontsize=9, frameon=False, labelcolor="#ccd3da")

    # --- PASSIVE joint, exploded ---
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    passive = [
        (J.clevis(),  C["clevis"], (0, 0, 0)),
        (J.tongue(),  C["tongue"], (0, 0, -34)),
        (J.pin(),     C["pin"],    (0, 34, 6)),
        (J.band_post(x=0, z=-30),  C["post"], (0, 4, 0)),   # post on segment B
        (J.band_post(x=0, z=10),   C["post"], (0, 4, 0)),   # post on segment A
    ]
    _draw(ax2, passive, "PASSIVE joint (back 2)  —  exploded")
    leg2 = [Line2D([0], [0], marker='s', ls='', mfc=C[k], mec='none', ms=11,
                   label=v) for k, v in [("tongue", "tongue"),
            ("clevis", "clevis"), ("pin", "pin = hinge"),
            ("post", "posts → rubber band loops over")]]
    ax2.legend(handles=leg2, loc="upper center", bbox_to_anchor=(0.5, 0.04),
               ncol=2, fontsize=9, frameon=False, labelcolor="#ccd3da")

    fig.suptitle("One joint, close up:  pin = the hinge  ·  "
                 "servo+horn drives the front 3  ·  rubber band springs the back 2",
                 fontsize=12, color="#e8eef5")
    fig.tight_layout()
    path = os.path.normpath(os.path.join(OUT, "joint_detail.png"))
    fig.savefig(path, dpi=125, facecolor=BG)
    plt.close(fig)
    print(f"[ok] {path}")
    _mount_view()


def _mount_view():
    """Second figure: how the servo is mounted INSIDE a driven segment."""
    seg1 = next(p for p in P.segment_table() if p["name"] == "seg1")
    r0 = seg1["r0"]
    parts = [
        (build_segment(seg1, "tongue"), C["clevis"], (0, 0, 0), 0.16),  # see-through shell
        (servo_mount(r0),  C["post"],   (0, 0, 0)),       # the screw bosses (green)
        (servo_mock(),     C["servo"],  (0, 0, 0)),       # servo body + flanges
        (J.servo_horn(),   C["horn"],   (0, 0, 0)),       # horn on the shaft
        (J.pin(),          C["pin"],    (0, 0, 0)),       # joint pin
    ]
    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111, projection="3d")
    _draw(ax, parts, "Servo mounted in a driven segment", elev=20, azim=-66)
    leg = [Line2D([0], [0], marker='s', ls='', mfc=C[k], mec='none', ms=11,
                  label=v) for k, v in [("clevis", "segment shell (see-through)"),
           ("post", "screw bosses (servo bolts to these)"),
           ("servo", "servo body + flanges"), ("horn", "horn"),
           ("pin", "pin")]]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, 0.02),
              ncol=2, fontsize=9, frameon=False, labelcolor="#ccd3da")
    fig.suptitle("How the actuator mounts: servo drops in, flanges screw to the "
                 "two bosses, shaft up to the horn", fontsize=12, color="#e8eef5")
    fig.tight_layout()
    path = os.path.normpath(os.path.join(OUT, "servo_mount.png"))
    fig.savefig(path, dpi=125, facecolor=BG)
    plt.close(fig)
    print(f"[ok] {path}")
    _dive_drive_view()


def _dive_drive_view():
    """Third figure: how ONE servo drives BOTH fins through one rod + a bushing."""
    hr = DP.HULL_R
    parts = [
        (DP.shaft(), C["pin"], (0, 0, 0)),                       # the rod
        (DP.plane(+1), C["tongue"], (0, 0, 0), 0.30),            # fins (faded)
        (DP.plane(-1), C["tongue"], (0, 0, 0), 0.30),
        (DP.dive_bushing(+hr), "#9aa6b2", (0, 0, 0)),            # bushings
        (DP.dive_bushing(-hr), "#9aa6b2", (0, 0, 0)),
        (DP.dive_servo(), C["servo"], (0, 0, 0)),                # the servo
        (DP.dive_servo_horn(), C["horn"], (0, 0, 0)),            # horn
        (DP.dive_link(), "#e0c020", (0, 0, 0)),                  # link
        (DP.dive_crank(), C["post"], (0, 0, 0)),                 # crank on rod
    ]
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111, projection="3d")
    _draw(ax, parts, "Fin drive: 1 servo turns the whole rod", elev=18, azim=-72)
    leg = [Line2D([0], [0], marker='s', ls='', mfc=c, mec='none', ms=11, label=v)
           for c, v in [(C["pin"], "one rod (both fins keyed to it)"),
           (C["tongue"], "fins (move together)"),
           ("#9aa6b2", "bushings (far-end support, not a motor)"),
           (C["servo"], "ONE servo"), (C["horn"], "horn"),
           ("#e0c020", "link"), (C["post"], "crank on rod")]]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, 0.0),
              ncol=2, fontsize=9, frameon=False, labelcolor="#ccd3da")
    fig.suptitle("Fin actuator = 1 single-shaft servo. Its arm drives a link → "
                 "crank → the rod turns → both fins pitch together.",
                 fontsize=11.5, color="#e8eef5")
    fig.tight_layout()
    path = os.path.normpath(os.path.join(OUT, "dive_drive.png"))
    fig.savefig(path, dpi=125, facecolor=BG)
    plt.close(fig)
    print(f"[ok] {path}")


if __name__ == "__main__":
    main()
