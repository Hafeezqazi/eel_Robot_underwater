"""
sizing.py  --  First-order physics & sizing for the eel robot.

Pulls every geometric input from cad/params.py so the math always
matches the CAD. Computes, prints, and saves a report covering:

  1. Geometry        : displaced volume, wetted area, frontal area
  2. Buoyancy/ballast: neutral-buoyancy mass budget
  3. Hydrodynamics   : cruise drag, thrust, propulsive power
  4. Gait (Strouhal) : tail-beat frequency, per-joint phase offsets
  5. Actuation       : per-joint servo torque demand vs rated
  6. Power/energy    : electrical budget, battery / tether current

All results are ORDER-OF-MAGNITUDE engineering estimates with the
assumptions printed alongside. Treat as design targets, refine with
CFD (analysis stage D) and bench tests.

Run:  python sizing.py
"""

import os
import sys
import math
import numpy as np

# import the shared parameter module from ../cad
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as P   # noqa: E402


# ----------------------------------------------------------------------
# assumptions you may want to tune
# ----------------------------------------------------------------------
ENDURANCE_TARGET_MIN = 30.0    # min of active swimming we size energy for
PROP_EFFICIENCY      = 0.40    # undulatory propulsive efficiency (0.2-0.5)
SHELL_PACKING        = 0.50    # printed-shell effective fill (infill+walls)
CD_PLATE             = 1.2     # flat-plate normal drag coeff (segment sweep)
HOTEL_W              = 2.0     # W, electronics always-on (MCU+sensors+leak)
SERVO_AVG_W_EACH     = 0.8     # W, average per DRIVEN servo while beating
DIVE_SERVO_W         = 0.3     # W, dive-plane servo (mostly holding position)

# mass line-items (kg) -- swap for measured values as you buy parts
M_SERVO_EACH = 0.014           # 9-14 g metal-gear micro (MG90S class, potted)
M_BATTERY    = 0.030           # small 2S buffer pack (tether supplies bulk)
M_ELECTRONICS = 0.055          # MCU + driver + IMU + depth + leak + FPV
                               # camera + LED headlight + MOSFET + window
M_HARDWARE   = 0.020           # pins, screws, inserts
M_SKIN_FIN   = 0.085           # TPU sleeve (~72 g) + tail fin foil
M_DIVE       = 0.026           # 2 dive planes + transverse shaft


def rho_water():
    return P.RHO_FRESH if P.WATER == "fresh" else P.RHO_SALT


# ----------------------------------------------------------------------
# 1. GEOMETRY  (integrate the body of revolution)
# ----------------------------------------------------------------------
def geometry():
    samples = P.body_wetted_radius_list(400)
    # the nose is truncated at the camera window -> body starts at WINDOW_Z
    z0 = P.WINDOW_Z / 1000.0
    samples = [s for s in samples if s[0] >= z0]
    z = np.array([s[0] for s in samples])          # m
    r = np.array([s[1] for s in samples])          # m
    # displaced volume  V = integral pi r^2 dz
    vol = float(np.trapezoid(math.pi * r ** 2, z))
    # wetted area  A = integral 2 pi r sqrt(1 + (dr/dz)^2) dz
    drdz = np.gradient(r, z)
    area = float(np.trapezoid(2 * math.pi * r * np.sqrt(1 + drdz ** 2), z))
    return dict(volume=vol, wetted=area, frontal=P.frontal_area())


# ----------------------------------------------------------------------
# 2. MASS / BUOYANCY BUDGET
# ----------------------------------------------------------------------
def head_bay_volume():
    """Displaced volume (m^3) of the sealed head bay (WINDOW_Z..HEAD_LEN)."""
    n = 120
    zs = np.linspace(P.WINDOW_Z / 1000.0, P.HEAD_LEN / 1000.0, n)
    rs = np.array([P.radius_profile(z * 1000.0) / 1000.0 for z in zs])
    return float(np.trapezoid(math.pi * rs ** 2, zs))


def mass_budget(geo):
    shell = geo["wetted"] * (P.WALL / 1000.0) * P.RHO_PLA * SHELL_PACKING
    n_servo = P.N_DRIVEN + 1                           # 3 driven joints + 1 dive
    servos = n_servo * M_SERVO_EACH
    parts = {
        "shell (PLA)":   shell,
        "servos x%d" % n_servo: servos,
        "battery":       M_BATTERY,
        "electronics":   M_ELECTRONICS,
        "hardware":      M_HARDWARE,
        "skin+tailfin":  M_SKIN_FIN,
        "dive planes":   M_DIVE,
    }
    dry = sum(parts.values())
    displaced = geo["volume"] * rho_water()          # kg, FULLY-SEALED body
    ballast = displaced - dry                         # +ve => add ballast
    # free-flooding option: only the head bay traps air; flooded tail
    # segments displace ~ their solid (PLA) volume only ~= shell mass / rho.
    # free-flood displacement = head-bay air + shell material + buoyancy FOAM
    foam_disp = (P.FOAM_VOL / 1e6) * rho_water()          # kg, stability foam
    disp_flood = head_bay_volume() * rho_water() + shell + foam_disp
    ballast_flood = disp_flood - dry                      # = the lead KEEL
    return (parts, dry, displaced, ballast, disp_flood, ballast_flood)


# ----------------------------------------------------------------------
# 3. HYDRODYNAMICS  (cruise)
# ----------------------------------------------------------------------
def hydro(geo):
    v = P.DESIGN_SPEED
    Fd = 0.5 * rho_water() * P.CD_AXIAL * geo["frontal"] * v ** 2
    P_thrust = Fd * v                                 # ideal thrust power
    P_prop = P_thrust / PROP_EFFICIENCY               # mech power into water
    return dict(drag=Fd, thrust=Fd, p_thrust=P_thrust, p_prop=P_prop)


# ----------------------------------------------------------------------
# 4. GAIT  (Strouhal -> frequency + traveling-wave phases)
# ----------------------------------------------------------------------
def gait():
    v = P.DESIGN_SPEED
    A = P.TAIL_AMPLITUDE                               # m, target lateral sweep
    f = P.CRUISE_FREQ_HZ                               # Hz, chosen tail-beat
    # traveling wave: one wavelength ~ body length -> phase per axial mm
    wavelength = P.BODY_LENGTH / 1000.0                # m
    k = 2 * math.pi / wavelength                       # rad/m
    phases = []
    for i, z in enumerate(P.JOINT_Z):
        phi = k * (z / 1000.0)                          # rad lag at this joint
        phases.append((i + 1, z, math.degrees(phi) % 360.0))
    return dict(freq=f, amplitude=A, phases=phases,
                omega_pk=2 * math.pi * f * math.radians(P.JOINT_TRAVEL_DEG))


# ----------------------------------------------------------------------
# 5. SERVO TORQUE DEMAND  (first-order plate-sweep model)
#    Each joint sweeps the body AFT of it through the water. Model the
#    swept appendage as a flat plate; peak hydrodynamic torque about the
#    pivot = integral of plate drag * moment-arm at peak angular velocity.
# ----------------------------------------------------------------------
def servo_torque(g):
    rho = rho_water()
    omega = g["omega_pk"]                              # rad/s peak
    demand = []
    parts = P.segment_table()
    # index of first driven segment in parts list (head is [0])
    for j in range(P.N_DRIVEN):
        # everything aft of joint j contributes; approximate as the single
        # segment just behind the joint (dominant near-field load)
        seg = parts[1 + j]
        L = (seg["z1"] - seg["z0"]) / 1000.0           # m segment length
        r_mean = 0.5 * (seg["r0"] + seg["r1"]) / 1000.0
        span = 2 * r_mean                              # m plate height ~ dia
        # plate strip from pivot (x=0) to x=L; v_lat(x)=omega*x
        # dT = 0.5 rho Cd (span dx) (omega x)^2 * x  -> integral 0..L
        T = 0.5 * rho * CD_PLATE * span * omega ** 2 * (L ** 4) / 4.0
        demand.append((j + 1, T))
    return demand


# ----------------------------------------------------------------------
# 6. POWER / ENERGY
# ----------------------------------------------------------------------
def power(hyd):
    p_servos = P.N_DRIVEN * SERVO_AVG_W_EACH + DIVE_SERVO_W   # driven + dive
    p_total = HOTEL_W + p_servos + P.LIGHT_W           # + LED headlight
    wh = p_total * (ENDURANCE_TARGET_MIN / 60.0)
    # tether/battery current at 2S nominal 7.4 V
    v_bus = 7.4
    amps = p_total / v_bus
    return dict(p_servos=p_servos, p_total=p_total, wh=wh,
                v_bus=v_bus, amps=amps, p_hydro=hyd["p_prop"])


# ----------------------------------------------------------------------
# report
# ----------------------------------------------------------------------
def main():
    geo = geometry()
    parts, dry, displaced, ballast, disp_flood, ballast_flood = mass_budget(geo)
    hyd = hydro(geo)
    g = gait()
    torq = servo_torque(g)
    pw = power(hyd)

    L = []
    def pr(s=""):
        L.append(s)

    pr("=" * 64)
    pr("EEL ROBOT  --  FIRST-ORDER SIZING REPORT")
    pr("=" * 64)
    pr(f"water = {P.WATER} (rho {rho_water():.0f} kg/m^3),  "
       f"speed = {P.DESIGN_SPEED:.2f} m/s")
    pr("")
    pr("[1] GEOMETRY")
    pr(f"  displaced volume : {geo['volume']*1e6:8.1f} cm^3")
    pr(f"  wetted area      : {geo['wetted']*1e4:8.1f} cm^2")
    pr(f"  frontal area     : {geo['frontal']*1e4:8.2f} cm^2")
    pr("")
    pr("[2] MASS / BUOYANCY BUDGET  (neutral target)")
    for k, v in parts.items():
        pr(f"    {k:16}: {v*1000:7.1f} g")
    pr(f"    {'-'*30}")
    pr(f"    {'DRY MASS':16}: {dry*1000:7.1f} g")
    pr("  option A -- FULLY SEALED body:")
    pr(f"    displaces        : {displaced*1000:7.1f} g water")
    pr(f"  => ADD BALLAST     : {ballast*1000:7.1f} g  (heavy ballast needed)")
    pr("  option B -- FREE-FLOODING tail (only head bay dry) [RECOMMENDED]:")
    pr(f"    displaces        : {disp_flood*1000:7.1f} g water")
    if ballast_flood >= 0:
        pr(f"  => LEAD KEEL       : {ballast_flood*1000:7.1f} g  (low+fwd; also "
           f"sets roll/trim -- see stability.py)")
    else:
        pr(f"  => ADD FLOTATION   : {-ballast_flood*1000:7.1f} g  (add buoyancy foam)")
    pr(f"     reserve buoyancy: aim ~2-5% ({0.03*disp_flood*1000:.0f} g) trim margin")
    pr("")
    pr("[3] HYDRODYNAMICS (cruise)")
    pr(f"  drag force       : {hyd['drag']*1000:8.2f} mN")
    pr(f"  ideal thrust pwr : {hyd['p_thrust']*1000:8.2f} mW")
    pr(f"  prop. power (eta={PROP_EFFICIENCY:.2f}): {hyd['p_prop']*1000:8.2f} mW")
    pr("")
    pr("[4] GAIT (Strouhal St=%.2f)" % P.ST_TARGET)
    pr(f"  tail-beat freq   : {g['freq']:8.2f} Hz")
    pr(f"  peak ang. vel    : {math.degrees(g['omega_pk']):8.0f} deg/s")
    pr(f"  amplitude (tail) : {g['amplitude']*1000:8.0f} mm")
    pr("  traveling-wave joint phase offsets:")
    for jn, z, phi in g["phases"]:
        pr(f"    joint {jn} @ z={z:3.0f}mm : {phi:6.1f} deg")
    pr("")
    pr("[5] SERVO TORQUE DEMAND vs RATED (%.2f N*m)" % P.SERVO_TORQUE_RATED)
    worst = 0.0
    for jn, T in torq:
        worst = max(worst, T)
        flag = "OK" if T < P.SERVO_TORQUE_RATED else "** OVER **"
        pr(f"    joint {jn} : {T*1000:7.2f} mN*m   {flag}")
    margin = P.SERVO_TORQUE_RATED / worst if worst > 0 else float("inf")
    pr(f"  worst-case margin : {margin:5.1f}x")
    pr("")
    pr("[6] POWER / ENERGY")
    pr(f"  hotel load       : {HOTEL_W:8.1f} W")
    pr(f"  servos ({P.N_DRIVEN}x{SERVO_AVG_W_EACH:.1f}W + dive "
       f"{DIVE_SERVO_W:.1f}W): {pw['p_servos']:.1f} W")
    pr(f"  LED headlight    : {P.LIGHT_W:8.1f} W (avg; W command dims)")
    pr(f"  TOTAL electrical : {pw['p_total']:8.1f} W")
    pr(f"  energy / {ENDURANCE_TARGET_MIN:.0f} min : {pw['wh']:8.1f} Wh")
    pr(f"  bus current @{pw['v_bus']:.1f}V: {pw['amps']:8.2f} A "
       f"(size tether/battery for this)")
    pr("=" * 64)

    text = "\n".join(L)
    print(text)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "output", "sizing_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[saved] {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
