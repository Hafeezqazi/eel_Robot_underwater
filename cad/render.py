"""
render.py  --  Quick matplotlib previews of the posed eel (QA + docs).

Tessellates the assembly compound and projects a top-down view (looking
down the Y / pin axis) so the lateral swimming undulation and the joint
articulation are visible. Not part of the CAD deliverable - just a viewer.

Run:  python render.py   ->  output/preview_straight.png, preview_swim.png
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

import cadquery as cq
import params as P
import dive_planes
from assembly import pose, swim_angles

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")


def _tris(compound, tol=0.4):
    verts, tris = compound.tessellate(tol)
    V = np.array([[v.x, v.y, v.z] for v in verts])
    T = np.array(tris)
    return V, T


def _topview(ax, assy, title):
    V, T = _tris(assy.toCompound())
    polys, depth = [], []
    for (i, j, k) in T:
        tri = V[[i, j, k]]
        polys.append(tri[:, [2, 0]])           # (Z horizontal, X vertical)
        depth.append(tri[:, 1].mean())         # Y for shading
    depth = np.array(depth)
    shade = (depth - depth.min()) / (np.ptp(depth) + 1e-9)
    colors = plt.cm.viridis(0.25 + 0.6 * shade)
    pc = PolyCollection(polys, facecolors=colors, edgecolors="none")
    ax.add_collection(pc)
    ax.set_xlim(-20, P.BODY_LENGTH + 20)
    ax.set_ylim(-160, 160)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("body axis  Z (mm)")
    ax.set_ylabel("lateral  X (mm)")
    # mark joint pivot stations
    for z in P.JOINT_Z:
        ax.axvline(z, color="r", lw=0.5, ls=":", alpha=0.4)


def _sideview(ax, assy, title):
    """Side projection (look along X): shows dive-plane pitch in the Y-Z plane."""
    V, T = _tris(assy.toCompound())
    polys, depth = [], []
    for (i, j, k) in T:
        tri = V[[i, j, k]]
        polys.append(tri[:, [2, 1]])           # (Z horizontal, Y vertical)
        depth.append(tri[:, 0].mean())
    depth = np.array(depth)
    shade = (depth - depth.min()) / (np.ptp(depth) + 1e-9)
    pc = PolyCollection(polys, facecolors=plt.cm.viridis(0.25 + 0.6 * shade),
                        edgecolors="none")
    ax.add_collection(pc)
    ax.axvline(P.DIVE_PLANE_Z, color="b", lw=0.6, ls=":", alpha=0.5)
    ax.set_xlim(-20, P.BODY_LENGTH + 20)
    ax.set_ylim(-110, 110)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("body axis  Z (mm)")
    ax.set_ylabel("vertical  Y (mm)")


def main():
    cfgs = [("straight", [0, 0, 0, 0, 0], "preview_straight.png",
             "Eel - straight (all joints 0 deg)"),
            ("swim", swim_angles(), "preview_swim.png",
             "Eel - mid-stroke (5-joint travelling wave)")]
    for _, ang, fname, title in cfgs:
        fig, ax = plt.subplots(figsize=(12, 3.6))
        _topview(ax, pose(ang), title)
        fig.tight_layout()
        path = os.path.normpath(os.path.join(OUT, fname))
        fig.savefig(path, dpi=110)
        plt.close(fig)
        print(f"[ok] {path}")

    # dive-plane detail: planes-only, side projection, 3 pitch settings
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.0))
    for ax, pitch, lbl in zip(axes, (-15, 0, +15),
                              ("climb -15 deg", "level 0 deg", "dive +15 deg")):
        dp = cq.Assembly()
        for s in (+1, -1):                              # +pitch = dive (LE down)
            dp.add(dive_planes.plane(s).rotate((0, 0, 0), (1, 0, 0), -pitch))
        dp.add(dive_planes.shaft())
        V, T = _tris(dp.toCompound(), tol=0.3)
        polys = [V[[i, j, k]][:, [2, 1]] for (i, j, k) in T]   # Z horiz, Y vert
        ax.add_collection(PolyCollection(polys, facecolors="#d79b00",
                                         edgecolors="#7a5800", linewidths=0.1))
        ax.set_xlim(-40, 40); ax.set_ylim(-30, 30); ax.set_aspect("equal")
        ax.axhline(0, color="b", lw=0.5, ls=":")
        ax.set_title(f"dive plane: {lbl}", fontsize=9)
        ax.set_xlabel("chord Z (mm)")
    axes[0].set_ylabel("vertical Y (mm)")
    fig.suptitle("Bow dive-plane pitch authority (side view, flow ->)",
                 fontsize=10)
    fig.tight_layout()
    path = os.path.normpath(os.path.join(OUT, "preview_dive.png"))
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"[ok] {path}")


if __name__ == "__main__":
    main()
