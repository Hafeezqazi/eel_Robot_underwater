"""
gait.py  --  Anguilliform gait generator (reference implementation).

Produces the joint commands for a travelling body wave (the front N_DRIVEN
joints carry servos; the rear joints follow passively):

    theta_i(t) = A_i * sin(2*pi*f*t - phi_i) + heading_bias

  * f        : tail-beat frequency from the Strouhal target (sizing.py)
  * phi_i    : spatial phase lag at joint i (travelling wave head->tail)
  * A_i      : amplitude envelope, growing toward the tail (anguilliform)
  * heading  : constant bias added to all joints to steer (turn)

This pure-Python version is the source of truth; firmware/eel_gait.ino is
the microcontroller port of the same math. Run to print a command table:
    python gait.py
"""

import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as P   # noqa: E402


def tail_beat_freq(speed=None):
    """Cruise tail-beat frequency (Hz). `speed` scales it 0..1 (firmware)."""
    base = P.CRUISE_FREQ_HZ
    if speed is None:
        return base
    return base * speed


def phase_lags():
    """Per-joint spatial phase lag phi_i (rad), travelling wave head->tail."""
    k = 2 * math.pi / (P.BODY_LENGTH / 1000.0)        # one wave over body
    return [k * (z / 1000.0) for z in P.JOINT_Z]


def amplitude_envelope():
    """Per-joint amplitude A_i (deg): small at head, peak CRUISE_AMP_DEG aft."""
    n = P.N_JOINTS
    return [P.CRUISE_AMP_DEG * (0.45 + 0.55 * (i + 1) / n)
            for i in range(n)]


def _wave(i, t, speed, heading_deg):
    """Travelling-wave angle (deg) at body joint i."""
    f = tail_beat_freq(speed)
    ang = (amplitude_envelope()[i] *
           math.sin(2 * math.pi * f * t - phase_lags()[i]) + heading_deg)
    return max(-P.JOINT_TRAVEL_DEG, min(P.JOINT_TRAVEL_DEG, ang))


def command(t, speed=None, heading_deg=0.0):
    """Servo commands: the DRIVEN front joints only (N_DRIVEN of them).

    These are the angles sent to the physical servos. speed scales the beat
    frequency; heading_deg biases the driven joints to steer.
    """
    return [_wave(i, t, speed, heading_deg) for i in range(P.N_DRIVEN)]


def body_wave_angles(t, speed=None):
    """ALL body joint angles (driven + passive), for kinematics / animation.

    The passive rear joints are assumed to track the same body wave (a
    well-tuned compliant tail follows it). Used by the sim and the 3-D viewers
    so the whole body undulates, even though only the front joints are driven.
    """
    return [_wave(i, t, speed, 0.0) for i in range(P.N_JOINTS)]


def servo_us(angle_deg, center_us=1500, us_per_deg=10.0):
    """Map a joint angle (deg) to a servo pulse width (microseconds)."""
    return center_us + us_per_deg * angle_deg


class DepthHold:
    """PD depth controller -> bow dive-plane angle (deg, + = dive).

    err = target - depth ; +err means we need to go DEEPER -> positive (dive)
    plane angle. Output clamped to the mechanical plane limit. Dive planes have
    NO authority at zero forward speed (see analysis/dive.py).
    """

    def __init__(self, kp=12.0, kd=8.0):
        self.kp = kp
        self.kd = kd
        self.prev = 0.0

    def update(self, depth_m, target_m, dt):
        err = target_m - depth_m
        derr = (err - self.prev) / dt if dt > 0 else 0.0
        self.prev = err
        ang = self.kp * err + self.kd * derr
        return max(-P.DIVE_PLANE_MAX_DEG, min(P.DIVE_PLANE_MAX_DEG, ang))


def _wrap180(a):
    """Wrap an angle to [-180, 180] deg."""
    while a > 180.0:
        a -= 360.0
    while a < -180.0:
        a += 360.0
    return a


class HeadingHold:
    """PD heading controller -> joint steering BIAS (deg) for command().

    Reads the IMU yaw (heading) and the target; outputs the bias added to the
    driven joints so the body turns to hold the heading. Gyro-only yaw (MPU6050
    has no magnetometer) drifts slowly -> good for SHORT-term hold; add a
    compass (MPU9250 / HMC5883) for absolute heading.
    """

    def __init__(self, kp=0.6, kd=0.08, max_bias=18.0):
        self.kp = kp
        self.kd = kd
        self.max = max_bias
        self.prev = 0.0

    def update(self, heading_deg, target_deg, dt):
        err = _wrap180(target_deg - heading_deg)
        derr = (err - self.prev) / dt if dt > 0 else 0.0
        self.prev = err
        b = self.kp * err + self.kd * derr
        return max(-self.max, min(self.max, b))


def _demo():
    f = tail_beat_freq()
    print("=" * 60)
    print("ANGULILLIFORM GAIT  --  command table")
    print("=" * 60)
    print(f"tail-beat freq : {f:.2f} Hz   (period {1/f:.3f} s)")
    print(f"driven servos  : {P.N_DRIVEN} (front)   passive joints: {P.N_PASSIVE} (compliant tail)")
    print("phase lags     : " +
          ", ".join(f"{math.degrees(p):.0f}d" for p in phase_lags()))
    print("amplitudes     : " +
          ", ".join(f"{a:.0f}d" for a in amplitude_envelope()))
    print("-" * 60)
    hdr = "t(s)  " + "".join(f"  servo{i+1}" for i in range(P.N_DRIVEN))
    print(hdr)
    period = 1.0 / f
    for n in range(9):
        t = n * period / 8.0
        cmd = command(t)
        print(f"{t:5.3f} " + "".join(f"  {a:6.1f}" for a in cmd))
    print("-" * 60)
    print("steering demo (heading +15 deg, t=0):")
    print("  straight :", [round(a, 1) for a in command(0.0)])
    print("  turn     :", [round(a, 1) for a in command(0.0, heading_deg=15)])
    print("-" * 60)
    print("depth-hold demo (target 1.5 m, start 0 m, simple plant):")
    dh = DepthHold()
    depth, dt = 0.0, 0.2
    for step in range(6):
        ang = dh.update(depth, 1.5, dt)
        depth += 0.18 * (ang / P.DIVE_PLANE_MAX_DEG)   # toy descent response
        print(f"  t={step*dt:3.1f}s depth={depth:4.2f}m -> plane {ang:5.1f} deg")
    print("-" * 60)
    print("heading-hold demo (target 0 deg, start +40 deg, toy plant):")
    hh = HeadingHold()
    hdg, dt = 40.0, 0.2
    for step in range(7):
        bias = hh.update(hdg, 0.0, dt)
        hdg += 0.9 * bias * dt * 5       # toy: a -bias turns heading back to 0
        print(f"  t={step*dt:3.1f}s heading={hdg:5.1f}deg -> joint bias {bias:5.1f} deg")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
