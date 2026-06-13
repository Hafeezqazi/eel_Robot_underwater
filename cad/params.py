"""
params.py  --  SINGLE SOURCE OF TRUTH for the bio-inspired eel robot.

Every CAD script (body / joints / assembly / head_bay) and the analysis
scripts import their numbers from here. Change a value here -> the whole
model and all calculations update. No magic numbers anywhere else.

UNITS: millimetres + degrees for geometry (CadQuery native unit = mm).
       SI (m, kg, s, N) is used only inside analysis/, converted there.

Run directly to print a human-readable summary:
    python params.py
"""

import math

# ----------------------------------------------------------------------
# 1. TOP-LEVEL MISSION / SCALE  (desk-pool prototype tier)
# ----------------------------------------------------------------------
BODY_LENGTH      = 500.0    # mm, nose tip to tail-fin tip
DEPTH_RATING     = 2.0      # m, shallow pool
DESIGN_SPEED     = 0.30     # m/s, target cruise
WATER            = "fresh"  # fresh | salt  (density chosen in analysis)

# ----------------------------------------------------------------------
# 2. BODY-OF-REVOLUTION RADIUS PROFILE  r(z)
#    Eel/lamprey silhouette: small nose -> fat front -> long taper to tail.
#    s = z / BODY_LENGTH in [0,1].  Returns radius in mm.
# ----------------------------------------------------------------------
R_NOSE_TIP = 3.0    # mm, small ROUNDED tip (was a blunt 10 mm flat face)
R_MAX      = 35.0   # mm, max body radius  (dia 70 mm) over the front bay
R_TAIL     = 9.0    # mm, radius where the tapering body meets the tail fin

_S_NOSE_END = 0.16  # elliptical ogive nose ends here (longer, finer entry)
_S_FAT_END  = 0.32  # constant-max region ends, taper begins


def radius_profile(z):
    """Body outer radius (mm) at axial station z (mm from nose).

    Nose is an ELLIPTICAL (ogive) entry: rounded small tip -> full radius,
    which is low-drag (no blunt flat face). Tail is a long cosine taper.
    """
    s = max(0.0, min(1.0, z / BODY_LENGTH))
    if s <= _S_NOSE_END:                                   # elliptical nose
        f = s / _S_NOSE_END                                # 0 at tip -> 1 full
        r = R_MAX * math.sqrt(max(0.0, 1.0 - (1.0 - f) ** 2))
        return max(r, R_NOSE_TIP)                          # rounded tip
    if s <= _S_FAT_END:                                    # fat front (bay)
        return R_MAX
    f = (s - _S_FAT_END) / (1.0 - _S_FAT_END)              # taper to tail
    ease = 0.5 * (1.0 - math.cos(math.pi * f))
    return R_MAX + (R_TAIL - R_MAX) * ease


# ----------------------------------------------------------------------
# 3. SEGMENTATION  ->  head + 3 DRIVEN + 2 PASSIVE segments + tail fin
#    Front 3 joints are servo-driven; the rear 2 are PASSIVE/COMPLIANT -- a
#    springy tail the body wave flexes on its own (biomimetic, and keeps the
#    servos out of the thin tail where they won't fit). 5 physical joints carry
#    the travelling wave; only the front 3 carry a servo.
# ----------------------------------------------------------------------
HEAD_LEN   = 140.0          # mm, rigid dry electronics bay (segment 0, base)
N_JOINTS   = 5              # total body joints (travelling wave + pins)
N_DRIVEN   = 3              # of those, how many carry a servo (front segments)
N_PASSIVE  = N_JOINTS - N_DRIVEN   # rear compliant joints (2)
SEG_LEN    = 60.0           # mm, each body segment
TAILFIN_LEN = BODY_LENGTH - HEAD_LEN - N_JOINTS * SEG_LEN   # = 60 mm

JOINT_TRAVEL_DEG = 28.0     # +/- mechanical limit per joint
WALL       = 2.5            # mm, printed shell wall thickness
SEGMENT_GAP = 5.0           # mm, axial clearance between adjacent shells so
                            # they don't collide when the joint bends (the
                            # clevis/tongue bridge it; the skin sleeve covers it).
                            # 5 mm clears the ~7 deg cruise wave; raise it only
                            # if you command bigger per-joint angles.

# Axial station of every cut plane (joint location), nose datum z=0.
# stations[i] = z where joint i lives. Head spans 0..stations[0].
JOINT_Z = [HEAD_LEN + i * SEG_LEN for i in range(N_JOINTS)]   # 140..380
TAILFIN_Z = HEAD_LEN + N_JOINTS * SEG_LEN                     # 440


def segment_table():
    """List of body parts with axial extents and end radii.

    Each dict: name, z0, z1, r0 (radius at z0), r1 (radius at z1),
               driven (bool: has a driven joint at its FRONT face).
    """
    parts = []
    parts.append(dict(name="head", z0=0.0, z1=HEAD_LEN,
                      r0=radius_profile(0.0), r1=radius_profile(HEAD_LEN),
                      driven=False))
    for i in range(N_JOINTS):
        z0 = JOINT_Z[i]
        z1 = z0 + SEG_LEN
        parts.append(dict(name=f"seg{i+1}", z0=z0, z1=z1,
                          r0=radius_profile(z0), r1=radius_profile(z1),
                          driven=(i < N_DRIVEN)))   # front 3 driven, rear 2 passive
    parts.append(dict(name="tailfin", z0=TAILFIN_Z, z1=BODY_LENGTH,
                      r0=radius_profile(TAILFIN_Z), r1=R_TAIL * 0.6,
                      driven=False))
    return parts


# ----------------------------------------------------------------------
# 4. REVOLUTE JOINT HARDWARE  (clevis + tongue + pin)
# ----------------------------------------------------------------------
PIN_D        = 3.0     # mm, joint pin (M3 bolt or 3 mm dowel)
PIN_CLEAR    = 0.3     # mm, bore clearance over pin (printed fit)
TONGUE_T     = 6.0     # mm, central blade thickness (the moving prong)
CLEVIS_GAP   = TONGUE_T + 1.0   # mm, fork inner gap (0.5 mm/side clearance)
CLEVIS_PRONG = 4.0     # mm, each fork prong thickness
JOINT_OVERLAP = 14.0   # mm, axial length of the clevis/tongue overlap zone
KNUCKLE_R    = 6.0     # mm, rounded pivot-end radius of every lug (load arm
                       #     used by analysis/structures.py pin check)

# ----------------------------------------------------------------------
# 5. SERVO (one per joint).  9g-class METAL-GEAR sub-micro.
#    Rear segments get small; this size fits even the rearmost segment.
#    Confirm against the exact servo you buy and tweak here.
# ----------------------------------------------------------------------
# CHOSEN PART (Path A -- the build-ready fit for THIS body): a metal-gear MICRO
# (Tower Pro MG90S class, ~9-14 g, ~2.2 kg*cm) POTTED for submersion. Keeps the
# body small AND the ballast balanced (stability.py: foam+keel -> neutral, level).
# WHY NOT a ready-IP67 servo: the genuinely-submersible micros (e.g. Savox
# SW-0250MG, 25 g, 29.5x14x32.5 mm, IP67) FIT the bore but their +44 g over the
# micro needs ~+44 cm^3 more buoyancy than the servo-crowded bays can hold (the
# narrow tail caps foam ~79 cm^3) -> they'd require a LONGER body or external
# foam. That's a real upsize decision, documented in docs/BOM.md, not a drop-in.
SERVO_BODY_L = 23.0    # mm, along robot axis        (MG90S-class micro)
SERVO_BODY_W = 12.2    # mm, across (drives min inner width)
SERVO_BODY_H = 22.7    # mm, tall (gearbox to base)
SERVO_TAB_L  = 32.0    # mm, mounting-tab tip to tip
SERVO_TAB_T  = 2.5     # mm, tab thickness
SERVO_SHAFT_OFF = 6.0  # mm, output-shaft offset from body end
SERVO_POCKET_CLEAR = 0.6   # mm, pocket clearance around body
SERVO_TORQUE_RATED = 0.20  # N*m, rated stall (~2.0 kg*cm) -- verify per part

# ----------------------------------------------------------------------
# 5b. DIVE PLANES  (bow fins for active depth control -> 3-D diving)
#     A pair of horizontal fins on a common transverse (X) shaft just aft of
#     the head, driven by ONE extra waterproof servo (the 4th and last).
#     Pitching the shaft sets angle-of-attack -> vertical lift while
#     swimming forward.
# ----------------------------------------------------------------------
DIVE_PLANE_Z     = HEAD_LEN + 25.0   # mm, axial station of the dive shaft
DIVE_PLANE_SPAN  = 70.0   # mm, EXPOSED span of EACH fin, outboard of the hull
                          #     + skin (root at DIVE_ROOT_X, so the full span
                          #     makes lift -- matches analysis/dive.py area)
DIVE_ROOT_X      = R_MAX + 3.5   # mm, fin-root offset from the centreline:
                          #     clears hull (R_MAX) + TPU skin (~2.2 mm) + play
DIVE_PLANE_CHORD = 45.0   # mm, fore-aft chord
DIVE_PLANE_T     = 3.5    # mm, fin thickness
DIVE_SHAFT_D     = 4.0    # mm, transverse pitch shaft (steel rod)
DIVE_PLANE_MAX_DEG = 25.0 # +/- mechanical pitch limit (stall ~ +/-15 deg)
DIVE_CL_PER_DEG  = 0.09   # /deg, lift-curve slope (flat-plate, pre-stall)
DIVE_STALL_DEG   = 15.0   # deg, stall angle of attack

# ----------------------------------------------------------------------
# 6. CABLE / WIRE ROUTING / FLOODING
# ----------------------------------------------------------------------
CABLE_BORE_D = 8.0     # mm, axial through-bore in each bulkhead for wiring
DRAIN_HOLE_D = 3.0     # mm, drain/vent hole at the low point of each
                       #     free-flooding segment (fill on launch, drain out)

# ----------------------------------------------------------------------
# 7. HEAD ELECTRONICS BAY  (sealed, O-ring lid)
# ----------------------------------------------------------------------
BAY_WALL       = 3.0   # mm, pressure wall of the dry bay
ORING_CS       = 2.0   # mm, O-ring cross-section (e.g. 2 mm cord)
ORING_GROOVE_W = 2.4   # mm, groove width  (~1.2 x cord)
ORING_GROOVE_D = 1.5   # mm, groove depth   (~0.75 x cord -> squeeze)
LID_LEN        = 30.0  # mm, removable rear lid of the head bay
PENETRATOR_D   = 10.0  # mm, tether cable penetrator bore
PENETRATOR_OFF_Y = 12.0  # mm, penetrator offset above the axis so the tether
                         #     clears the joint-1 tongue on the lid centreline
WIRE_GLAND_D   = 10.0  # mm, second lid bore: servo + leak-probe wires from the
                       #     wet body, potted solid with epoxy (offset -Y)
SENSOR_PORT_D  = 8.0   # mm, third lid bore: MS5837 sensing face epoxied in,
                       #     gel side open to the water (offset +X)
SENSOR_PORT_X  = 14.0  # mm, lateral offset of the depth-sensor port

# ----------------------------------------------------------------------
# 7b. CAMERA WINDOW + LIGHT  (front of the dry bay -> useful ROV payload)
#     The elliptical nose is truncated at WINDOW_Z into a flat face with a
#     recessed seat; a clear acrylic disc is epoxy-bonded in. An analog FPV
#     camera + LED sit BEHIND the window inside the dry bay (no extra
#     waterproofing). Video goes topside over a spare tether pair.
# ----------------------------------------------------------------------
WINDOW_Z       = 18.0  # mm, axial station of the flat window face
WINDOW_SEAT_D  = 31.0  # mm, recess diameter for the acrylic disc (+0.5 fit)
WINDOW_SEAT_T  = 3.0   # mm, recess depth = disc thickness (flush mount)
WINDOW_BORE_D  = 24.0  # mm, clear aperture through to the bay cavity
LIGHT_W        = 2.0   # W, average white-LED headlight draw (analysis)

# lid clamp: 3 M3 bolt ears (head-rim insert boss <- lid rear tab). The lid's
# O-ring is a RADIAL (piston) seal -> seals with NO axial clamp force, and the
# joint-1 pin is the PRIMARY axial retention. These ears are a positive
# secondary lock against handling/rock + the drivetrain pull on the flange
# (so retention is NOT O-ring friction). Ears tuck into the head<->seg1 gap.
LID_BOLTS        = 3      # M3 cap screws around the rim
LID_BOLT_PCR     = 37.0   # mm, bolt pitch-circle radius (on small ears)
LID_EAR_R        = 4.5    # mm, ear / tab boss radius
LID_EAR_LEN      = 7.0    # mm, head-side insert-boss length (forward of rim)
LID_EAR_TAB      = 4.0    # mm, lid-side tab length (rearward, into the gap)
LID_INSERT_D     = 4.0    # mm, brass heat-set insert pilot bore (head ear)
LID_INSERT_DEPTH = 6.0    # mm, insert depth into the head ear
LID_BOLT_CLR_D   = 3.4    # mm, M3 clearance hole through the lid tab

# ----------------------------------------------------------------------
# 7c. STABILITY FIX  (from analysis/stability.py)
#     Baseline floats NOSE-UP (buoyancy all forward in the head bay) and is
#     barely roll-stable. Fix = aft buoyancy foam (moves CB back) + a low
#     forward lead keel (drops CG -> roll stable, and sets level trim).
# ----------------------------------------------------------------------
#   The foam is closed-cell DISCS shaped to the bore (tapered plugs that slide
#   into the rear-mid free-flooding bays), NOT a loose block. Two discs straddle
#   the seg2/seg3 joint so each stays inside its own segment (clear of the
#   joints) while their combined centroid sits aft enough to trim the boat level.
#   The disc frustum volumes below ARE the buoyancy number -> CAD drives the
#   analysis (stability.py / sizing.py read FOAM_VOL + FOAM_Z), not a guess.
FOAM_CLEAR = 2.5                       # mm, radial gap to the bore (slides in)
FOAM_Y     = 0.0                       # mm, centred on the axis (fills the bore)
FOAM_BAYS  = [(290.0, 26.0),           # (z_centre, length) disc in the seg2 bay
              (350.0, 30.0)]           # (z_centre, length) disc in the seg3 bay


def _foam_plug_geo(zc, length):
    """Bore-fitting tapered plug at station zc -> (front r, rear r, volume cm^3)."""
    half = length / 2.0
    r0 = radius_profile(zc - half) - WALL - FOAM_CLEAR     # front (wider)
    r1 = radius_profile(zc + half) - WALL - FOAM_CLEAR     # rear  (narrower)
    vol = math.pi / 3.0 * length * (r0 ** 2 + r0 * r1 + r1 ** 2) / 1000.0
    return r0, r1, vol


# (z_centre, length, r0, r1, volume_cm3) per disc
FOAM_PLUGS = [(zc, length) + _foam_plug_geo(zc, length) for zc, length in FOAM_BAYS]
FOAM_VOL   = sum(p[4] for p in FOAM_PLUGS)                       # cm^3, total
FOAM_Z     = sum(p[0] * p[4] for p in FOAM_PLUGS) / FOAM_VOL     # mm, vol-weighted
KEEL_MASS  = 197.0   # g, lead keel (also serves as the neutral-trim ballast)
KEEL_Z     = 40.0    # mm, keel centroid (forward belly, under the head bay)
KEEL_Y     = -22.0   # mm, keel low (on the floor) -> lowers CG for roll

# ----------------------------------------------------------------------
# 8. MATERIAL / PHYSICS CONSTANTS  (used by analysis/)
# ----------------------------------------------------------------------
RHO_FRESH = 1000.0     # kg/m^3
RHO_SALT  = 1025.0     # kg/m^3
RHO_PLA   = 1240.0     # kg/m^3, solid PLA (de-rate for infill in analysis)
G         = 9.81       # m/s^2

# Hydrodynamics
CD_AXIAL  = 0.10       # drag coeff on frontal area (streamlined body)
ST_TARGET = 0.30       # Strouhal number sweet-spot (efficient 0.2-0.4)
TAIL_AMPLITUDE = 0.10 * BODY_LENGTH / 1000.0   # m, target peak tail sweep

# Gait control inputs (cruise). JOINT_TRAVEL_DEG above is the MECHANICAL max,
# held in reserve for turns/bursts; cruise uses a gentler amplitude so the
# realised Strouhal -- evaluated at the REALISTIC (derated) speed, not the
# EBT upper bound -- lands in the efficient band (verified in swim_sim.py).
CRUISE_FREQ_HZ = 2.0   # Hz, chosen tail-beat frequency (open-loop control)
CRUISE_AMP_DEG = 7.0   # deg, peak per-joint amplitude at cruise (< travel)


def frontal_area():
    """Max frontal cross-section area (m^2)."""
    return math.pi * (R_MAX / 1000.0) ** 2


def body_wetted_radius_list(n=200):
    """Sampled (z_m, r_m) along the body for volume/area integration."""
    out = []
    for i in range(n + 1):
        z = BODY_LENGTH * i / n
        out.append((z / 1000.0, radius_profile(z) / 1000.0))
    return out


# ----------------------------------------------------------------------
# Self-test / summary
# ----------------------------------------------------------------------
def _summary():
    print("=" * 60)
    print("EEL ROBOT  --  PARAMETER SUMMARY")
    print("=" * 60)
    print(f"Total length        : {BODY_LENGTH:.0f} mm")
    print(f"Max diameter        : {2*R_MAX:.0f} mm")
    print(f"Body joints / driven: {N_JOINTS} total, {N_DRIVEN} servo-driven, "
          f"{N_PASSIVE} passive-compliant")
    print(f"Joint travel        : +/- {JOINT_TRAVEL_DEG:.0f} deg")
    print(f"Depth rating        : {DEPTH_RATING:.0f} m")
    print(f"Design speed        : {DESIGN_SPEED:.2f} m/s")
    print("-" * 60)
    print(f"{'part':8} {'z0':>6} {'z1':>6} {'r0':>6} {'r1':>6} {'driven':>7}")
    for p in segment_table():
        print(f"{p['name']:8} {p['z0']:6.0f} {p['z1']:6.0f} "
              f"{p['r0']:6.1f} {p['r1']:6.1f} {str(p['driven']):>7}")
    print("-" * 60)
    print(f"Joint Z stations    : {[round(z) for z in JOINT_Z]} mm")
    print(f"Tail-fin starts at  : {TAILFIN_Z:.0f} mm  (len {TAILFIN_LEN:.0f} mm)")
    print("=" * 60)


if __name__ == "__main__":
    _summary()
