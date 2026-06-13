"""
swim_sim.py  --  Self-propulsion estimate + swim animation.

Closes the design loop: takes the actual gait (firmware/gait.py), reconstructs
the body's backbone motion, and uses LIGHTHILL ELONGATED-BODY THEORY to
predict the steady self-propelled cruise speed, then checks it against the
DESIGN_SPEED assumed in sizing.py.

Lighthill reactive (mean) thrust at the trailing edge:
    T_mean = 0.5 * m_L * ( <(dh/dt)^2> - U^2 <(dh/dx)^2> )
Self-propulsion: T_mean = drag = 0.5 * rho * Cd * A_front * U^2  ->
    U = sqrt( m_L*<(dh/dt)^2> / ( rho*Cd*A_front + m_L*<(dh/dx)^2> ) )

  h    = lateral displacement of the backbone (m)
  m_L  = virtual (added) mass per length at the trailing edge (kg/m)
  <>   = time-average over one tail-beat period

Also renders output/swim_cycle.gif. Run:  python swim_sim.py
"""

import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))
import params as P            # noqa: E402
import gait                   # noqa: E402

OUT = os.path.join(HERE, "..", "output")


# Lighthill EBT models only reactive (added-mass) thrust and ignores viscous
# body drag, joint discreteness, and wake slip, so it OVER-predicts. Measured
# robotic-fish speeds are typically 40-60% of the EBT value -> derate factor.
EBT_DERATE = 0.5


def rho_water():
    return P.RHO_FRESH if P.WATER == "fresh" else P.RHO_SALT


def backbone(t, speed=None, heading=0.0, step=5.0):
    """Reconstruct the body centreline at time t.

    Returns (xs, zs, ss) arrays: lateral x, axial z, arc-length s (mm).
    Uses the full body wave (driven front joints + the passive compliant tail,
    which tracks the same wave).
    """
    ang = gait.body_wave_angles(t, speed=speed)   # all N_JOINTS angles (deg)
    xs, zs, ss = [0.0], [0.0], [0.0]
    x = z = s = 0.0
    theta = 0.0                                  # heading (rad) from +Z

    def walk(length):
        nonlocal x, z, s
        n = max(1, int(length / step))
        dl = length / n
        for _ in range(n):
            x += math.sin(theta) * dl
            z += math.cos(theta) * dl
            s += dl
            xs.append(x); zs.append(z); ss.append(s)

    walk(P.HEAD_LEN)                             # rigid head
    for i in range(P.N_JOINTS):
        theta += math.radians(ang[i])           # joint bend
        walk(P.SEG_LEN)
    walk(P.TAILFIN_LEN)                          # passive tail
    return np.array(xs), np.array(zs), np.array(ss)


def predict_speed():
    f = gait.tail_beat_freq()
    T = 1.0 / f
    M = 200
    ts = np.linspace(0, T, M, endpoint=False)
    x_tail = np.empty(M)
    slope = np.empty(M)
    for k, t in enumerate(ts):
        xs, zs, _ = backbone(t)
        x_tail[k] = xs[-1] / 1000.0                       # m
        dz = (zs[-1] - zs[-3]) / 1000.0
        dx = (xs[-1] - xs[-3]) / 1000.0
        slope[k] = dx / dz if abs(dz) > 1e-9 else 0.0
    dt = T / M
    dh_dt = np.gradient(x_tail, dt)                        # m/s, periodic-ish
    A_t = float(np.mean(dh_dt ** 2))                       # <(dh/dt)^2>
    B_t = float(np.mean(slope ** 2))                       # <(dh/dx)^2>

    rho = rho_water()
    d = 1.4 * P.R_MAX / 1000.0                             # tail-edge height (m)
    m_L = rho * math.pi * (d / 2.0) ** 2                   # added mass / length
    A_front = P.frontal_area()

    U = math.sqrt(m_L * A_t / (rho * P.CD_AXIAL * A_front + m_L * B_t))
    # thrust & drag at that U for reporting
    T_mean = 0.5 * m_L * (A_t - U ** 2 * B_t)
    drag = 0.5 * rho * P.CD_AXIAL * A_front * U ** 2
    # Strouhal St = f * (peak-to-peak tail sweep) / U. Quote it at BOTH the
    # EBT upper-bound speed and the derated realistic speed -- the realistic
    # one is what the physical robot will see, so tune the gait against it.
    amp_pp = 2 * abs(x_tail).max()
    St_ub = f * amp_pp / U if U > 0 else float("inf")
    St_real = f * amp_pp / (U * EBT_DERATE) if U > 0 else float("inf")
    return dict(f=f, A_t=A_t, B_t=B_t, m_L=m_L, U=U, T_mean=T_mean,
                drag=drag, St=St_ub, St_real=St_real,
                tail_amp=abs(x_tail).max())


def animate():
    f = gait.tail_beat_freq()
    Tp = 1.0 / f
    frames = 30
    fig, ax = plt.subplots(figsize=(11, 3.2))

    def draw(fr):
        ax.clear()
        t = fr / frames * Tp
        xs, zs, ss = backbone(t)
        # body outline: offset centreline by +/- local radius
        rad = np.array([P.radius_profile(s) for s in ss])
        dz = np.gradient(zs); dx = np.gradient(xs)
        norm = np.hypot(dz, dx) + 1e-9
        nx, nz = -dz / norm, dx / norm            # unit normal (lateral)
        topx, topz = xs + nx * rad, zs + nz * rad
        botx, botz = xs - nx * rad, zs - nz * rad
        poly_z = np.concatenate([topz, botz[::-1]])
        poly_x = np.concatenate([topx, botx[::-1]])
        ax.fill(poly_z, poly_x, color="#2a7", alpha=0.85, zorder=1)
        ax.plot(zs, xs, "k-", lw=0.8, zorder=2)
        for zj in P.JOINT_Z:                       # joint markers
            idx = int(np.argmin(np.abs(ss - zj)))
            ax.plot(zs[idx], xs[idx], "ro", ms=3, zorder=3)
        ax.set_xlim(-20, 560); ax.set_ylim(-150, 150)
        ax.set_aspect("equal")
        ax.set_title(f"Anguilliform swim cycle  (t = {t*1000:4.0f} ms,  "
                     f"f = {f:.1f} Hz)", fontsize=10)
        ax.set_xlabel("axial Z (mm)"); ax.set_ylabel("lateral X (mm)")

    anim = FuncAnimation(fig, draw, frames=frames, interval=60)
    path = os.path.normpath(os.path.join(OUT, "swim_cycle.gif"))
    anim.save(path, writer=PillowWriter(fps=16))
    plt.close(fig)
    return path


def main():
    r = predict_speed()
    L = []

    def pr(s=""):
        print(s)
        L.append(s)

    pr("=" * 60)
    pr("EEL ROBOT  --  SELF-PROPULSION (Lighthill EBT)")
    pr("=" * 60)
    pr(f"  tail-beat freq        : {r['f']:.2f} Hz")
    pr(f"  tail amplitude        : {r['tail_amp']*1000:.0f} mm")
    pr(f"  <(dh/dt)^2>           : {r['A_t']:.4f} (m/s)^2")
    pr(f"  <(dh/dx)^2>           : {r['B_t']:.4f}")
    pr(f"  added mass / length   : {r['m_L']:.2f} kg/m")
    pr("-" * 60)
    u_exp = r['U'] * EBT_DERATE
    pr(f"  EBT cruise speed (UB) : {r['U']:.3f} m/s   "
       f"({r['U']/P.BODY_LENGTH*1000:.2f} BL/s)   <- optimistic upper bound")
    pr(f"  expected (x{EBT_DERATE:.1f} derate): {u_exp:.3f} m/s   "
       f"({u_exp/P.BODY_LENGTH*1000:.2f} BL/s)   <- realistic estimate")
    pr(f"  thrust = drag at UB   : {r['T_mean']*1000:.1f} mN")
    pr(f"  Strouhal @ UB speed   : {r['St']:.2f}")
    pr(f"  Strouhal @ realistic  : {r['St_real']:.2f}  "
       f"({'efficient 0.2-0.4' if 0.2 <= r['St_real'] <= 0.4 else 'tune amp/freq'})")
    pr("-" * 60)
    pr(f"  cruise control inputs : f={P.CRUISE_FREQ_HZ:.1f} Hz, "
       f"peak joint amp={P.CRUISE_AMP_DEG:.0f} deg "
       f"(mech max {P.JOINT_TRAVEL_DEG:.0f} deg in reserve)")
    pr("=" * 60)
    out = os.path.join(OUT, "swim_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    gif = animate()
    print(f"[ok] animation -> {gif}")
    print(f"[saved] {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
