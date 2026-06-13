"""
render_anim.py  --  animated GIF of the eel swimming + diving, rendered straight
from the CAD (the same model the HTML viewer shows). For the README / repo page.

Speed trick: each rigid part is tessellated ONCE into local-frame triangles, then
re-posed every frame with cheap numpy transforms (no CAD rebuild per frame). The
body wave uses assembly.swim_angles(t); a gentle dive-and-recover pitches the
nose down and drops the body so the depth control reads on screen.

Run:  python render_anim.py  ->  output/eel_demo.gif
"""

import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import imageio.v2 as imageio

import params as P
from assembly import swim_angles, tail_fin
from head_bay import build_head, build_lid
from body import driven_segments
import dive_planes

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
BG = (13 / 255, 17 / 255, 23 / 255)          # #0d1117, like the HTML viewer
LIGHT = np.array([0.35, 0.55, 0.75]); LIGHT /= np.linalg.norm(LIGHT)
TOL = 2.0
N_FRAMES = 28
DIVE_PLANE_MAX = 18.0                          # deg, plane deflection on screen
BODY_PITCH_MAX = 15.0                          # deg, nose-down body attitude
DESCENT = 28.0                                 # mm, vertical drop at full dive


def tess(shape):
    if hasattr(shape, "val"):
        shape = shape.val()
    verts, tris = shape.tessellate(TOL)
    V = np.array([[v.x, v.y, v.z] for v in verts], dtype=float)
    T = np.array(tris, dtype=int)
    return V, T


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def shade(tri, rgb):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
    inten = 0.42 + 0.58 * np.clip(np.abs((n / ln) @ LIGHT), 0, 1)
    return np.clip(np.array(rgb)[None, :] * inten[:, None], 0, 1)


# ---- build + tessellate every part ONCE (local frames) ----
HEAD = tess(build_head())
LID = tess(build_lid()); LID[0][:] += np.array([0, 0, P.HEAD_LEN - P.LID_LEN])
SHAFT = tess(dive_planes.shaft()); SHAFT[0][:] += np.array([0, 0, P.DIVE_PLANE_Z])
PLANES = [tess(dive_planes.plane(+1)), tess(dive_planes.plane(-1))]
SEGS = [(tess(sol), part) for _, sol, part in driven_segments()]
TAIL = tess(tail_fin())

COL = {"head": (0.18, 0.55, 0.34), "lid": (0.5, 0.5, 0.5), "shaft": (0.5, 0.5, 0.5),
       "plane": (1.0, 0.55, 0.0), "drv": (0.27, 0.51, 0.71),
       "pas": (0.55, 0.72, 0.92), "tail": (0.18, 0.55, 0.34)}


def world_tris(t):
    """All world-space triangles + colours for swim phase + dive state at time t."""
    dive = math.sin(2 * math.pi * t)                  # -1..1 dive/climb
    plane_ang = math.radians(DIVE_PLANE_MAX * dive)
    out = []                                           # (Nx3x3, rgb)

    def add(VT, rgb, R=None, off=None):
        V, T = VT
        W = V @ R.T if R is not None else V.copy()
        if off is not None:
            W = W + off
        out.append((W[T], rgb))

    add(HEAD, COL["head"]); add(LID, COL["lid"]); add(SHAFT, COL["shaft"])
    for VT in PLANES:                                  # planes pitch on their shaft
        add(VT, COL["plane"], R=rot_x(-plane_ang),
            off=np.array([0, 0, P.DIVE_PLANE_Z]))
    # body wave FK (cumulative yaw per joint), same as assembly.pose()
    angles = swim_angles(t)
    px, pz, theta = 0.0, float(P.HEAD_LEN), 0.0
    for (VT, part), aj in zip(SEGS, angles):
        theta += aj
        R = rot_y(math.radians(theta)); off = np.array([px, 0.0, pz])
        add(VT, COL["drv"] if part["driven"] else COL["pas"], R=R, off=off)
        L = part["z1"] - part["z0"]; thr = math.radians(theta)
        px += math.sin(thr) * L; pz += math.cos(thr) * L
    add(TAIL, COL["tail"], R=rot_y(math.radians(theta)), off=np.array([px, 0, pz]))

    # global dive attitude: pitch the whole body nose-down + drop it
    Rg = rot_x(math.radians(BODY_PITCH_MAX * dive))
    C = np.array([0, 0, P.BODY_LENGTH / 2.0])
    drop = np.array([0, -DESCENT * (0.5 - 0.5 * math.cos(2 * math.pi * t)), 0])
    return [((tp - C) @ Rg.T + C + drop, rgb) for tp, rgb in out]


def main():
    # fixed display box over the whole clip so the robot doesn't jump/scale
    allpts = np.concatenate([np.concatenate([tp.reshape(-1, 3)
              for tp, _ in world_tris(k / N_FRAMES)]) for k in range(N_FRAMES)])
    allpts = allpts[:, [2, 0, 1]]
    mn, mx = allpts.min(0) - 12, allpts.max(0) + 12
    rng = mx - mn

    frames = []
    fig = plt.figure(figsize=(9, 3.6), facecolor=BG)
    for k in range(N_FRAMES):
        fig.clf()
        ax = fig.add_subplot(111, projection="3d", facecolor=BG)
        tris = world_tris(k / N_FRAMES)
        pts = np.concatenate([tp for tp, _ in tris])[:, :, [2, 0, 1]]
        cols = np.concatenate([shade(tp[:, :, [2, 0, 1]], rgb) for tp, rgb in tris])
        ax.add_collection3d(Poly3DCollection(pts, facecolors=cols,
                                             edgecolors="none"))
        ax.set_xlim(mn[0], mx[0]); ax.set_ylim(mn[1], mx[1]); ax.set_zlim(mn[2], mx[2])
        ax.set_box_aspect(rng); ax.view_init(elev=16, azim=-70)
        ax.set_axis_off()
        fig.subplots_adjust(0, 0, 1, 1)
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
        frames.append(buf)
        print(f"  frame {k+1}/{N_FRAMES}")
    plt.close(fig)

    gif = os.path.normpath(os.path.join(OUT, "eel_demo.gif"))
    imageio.mimsave(gif, frames, duration=0.08, loop=0)
    print(f"[ok] {gif}  ({len(frames)} frames, {os.path.getsize(gif)//1024} KB)")


if __name__ == "__main__":
    main()
