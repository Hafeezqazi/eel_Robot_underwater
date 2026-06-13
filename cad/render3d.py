"""
render3d.py  --  Proper shaded 3-D renders of the assembly (SolidWorks-style).

Tessellates each coloured part of the assembly and draws it as a shaded solid
from several viewpoints, so you can SEE the robot without opening a CAD app.
(For full interactive CAD, open output/eel_swim.step in SolidWorks / FreeCAD /
Fusion / Onshape.)

Run:  python render3d.py  ->  output/render3d_iso.png, render3d_views.png
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import params as P
from assembly import pose, swim_angles

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
LIGHT = np.array([0.35, 0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _part_tris(assy, tol=1.0):
    """Yield (triangles Nx3x3, base_rgb) for each coloured part, in world coords."""
    for child in assy.children:
        shape = child.obj
        if hasattr(shape, "val"):
            shape = shape.val()
        if child.loc is not None:
            shape = shape.located(child.loc)
        try:
            verts, tris = shape.tessellate(tol)
        except Exception:
            continue
        V = np.array([[v.x, v.y, v.z] for v in verts])
        T = np.array(tris)
        if len(T) == 0:
            continue
        rgb = (0.6, 0.6, 0.6)
        if child.color is not None:
            rgb = child.color.toTuple()[:3]
        yield V[T], np.array(rgb)


def _shade(tri_pts, rgb):
    """Per-face Lambert shading -> facecolor array."""
    v0, v1, v2 = tri_pts[:, 0], tri_pts[:, 1], tri_pts[:, 2]
    n = np.cross(v1 - v0, v2 - v0)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1.0
    n = n / ln
    inten = 0.45 + 0.55 * np.clip(np.abs(n @ LIGHT), 0, 1)
    return np.clip(np.array(rgb)[None, :] * inten[:, None], 0, 1)


def _draw(ax, assy, elev, azim):
    all_pts, all_cols = [], []
    for tri_pts, rgb in _part_tris(assy):
        all_pts.append(tri_pts)
        all_cols.append(_shade(tri_pts, rgb))
    pts = np.concatenate(all_pts, axis=0)
    cols = np.concatenate(all_cols, axis=0)
    # remap (X,Y,Z)->(Z,X,Y): lay the long body axis horizontal like a fish
    pts = pts[..., [2, 0, 1]]
    pc = Poly3DCollection(pts, facecolors=cols, edgecolors="none", linewidths=0)
    ax.add_collection3d(pc)
    mn = pts.reshape(-1, 3).min(axis=0)
    mx = pts.reshape(-1, 3).max(axis=0)
    rng = mx - mn
    ax.set_xlim(mn[0], mx[0])
    ax.set_ylim(mn[1], mx[1])
    ax.set_zlim(mn[2], mx[2])
    ax.set_box_aspect(rng)                     # true proportions (long + thin)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def main():
    assy = pose(swim_angles(), dive_pitch=12.0)

    # 1) big hero isometric
    fig = plt.figure(figsize=(14, 5))
    ax = fig.add_subplot(111, projection="3d")
    _draw(ax, assy, elev=20, azim=-72)
    ax.set_title("Eel robot — isometric (mid-stroke, dive planes +12°)",
                 fontsize=12)
    fig.tight_layout()
    p1 = os.path.normpath(os.path.join(OUT, "render3d_iso.png"))
    fig.savefig(p1, dpi=130)
    plt.close(fig)
    print(f"[ok] {p1}")

    # 2) three orthographic-ish views
    fig = plt.figure(figsize=(13, 4))
    for i, (elev, azim, lbl) in enumerate([(90, -90, "top"),
                                           (0, -90, "side"),
                                           (12, -52, "3/4")]):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        _draw(ax, pose([0, 0, 0, 0, 0], dive_pitch=0), elev, azim)
        ax.set_title(lbl, fontsize=10)
    fig.suptitle("Eel robot — orthographic views (straight, planes level)",
                 fontsize=11)
    fig.tight_layout()
    p2 = os.path.normpath(os.path.join(OUT, "render3d_views.png"))
    fig.savefig(p2, dpi=130)
    plt.close(fig)
    print(f"[ok] {p2}")


if __name__ == "__main__":
    main()
