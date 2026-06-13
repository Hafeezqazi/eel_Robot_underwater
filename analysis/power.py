"""
power.py  --  Electrical reality check for the build: servo peak/stall current,
brownout protection, tether voltage drop, fusing.

The average draw (~6 W, see sizing.py) is the easy part. What bites real builds:
  * servos STALL at many times their running current, all at once -> big spikes
  * those spikes brown out the ESP32 unless it's on its own rail + a bulk cap
  * the long thin TETHER drops voltage at peak current -> servos starve

Run:  python power.py   ->  output/power_report.txt
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as P   # noqa: E402

N_SERVO = P.N_DRIVEN + 1          # 3 joint + 1 dive
I_RUN = 0.25                      # A, per servo while moving (light load)
I_STALL = 1.0                     # A, per servo stall (9 g metal-gear class)
V_BUS = 5.5                       # V, servo bus
V_LOGIC = 3.3
HOTEL_A = 0.3                     # A, electronics @ their rail (~1 W)
LED_A = 0.4                       # A, headlight at full
TETHER_LEN = 5.0                  # m
RHO_CU = 1.72e-8                  # ohm*m
# common conductor areas (mm^2): AWG24, AWG22, AWG20, AWG18
AWG = {"24": 0.205, "22": 0.326, "20": 0.518, "18": 0.823}


def main():
    L = []
    pr = L.append
    I_peak = N_SERVO * I_STALL                       # worst case, all stall
    I_typ = N_SERVO * I_RUN + HOTEL_A + LED_A        # typical active draw
    pr("=" * 62)
    pr("ELECTRICAL  --  peak current, brownout, tether drop")
    pr("=" * 62)
    pr(f"servos                 : {N_SERVO}  (3 joint + 1 dive)")
    pr(f"per-servo run / stall  : {I_RUN:.2f} A / {I_STALL:.2f} A")
    pr(f"typical active draw    : {I_typ:.2f} A  (servos moving + hotel + LED)")
    pr(f"WORST-CASE peak        : {I_peak:.1f} A  (all servos stall at once)")
    pr("")
    pr("[BROWNOUT PROTECTION]")
    pr("  * ESP32 + logic on their OWN 3.3 V buck off the bus -- NOT sharing")
    pr("    the servo rail (servo droop must not reset the MCU).")
    pr(f"  * bulk capacitor across the servo bus: 1000-2200 uF, {int(V_BUS*2)} V+")
    pr("    (holds the rail through stall spikes).")
    pr(f"  * fuse the servo bus at ~{int(I_peak)} A; fuse the LED separately.")
    pr("")
    pr("[TETHER VOLTAGE DROP]  round-trip drop at the typical + peak current")
    pr(f"  {TETHER_LEN:.0f} m tether, drop = I x (2 x rho x L / A):")
    pr(f"  {'AWG':>5} {'R(ohm)':>8} {'drop@typ':>10} {'drop@peak':>11}")
    for g, a in AWG.items():
        R = 2 * RHO_CU * TETHER_LEN / (a * 1e-6)
        pr(f"  {g:>5} {R:8.3f} {I_typ*R:9.2f}V {I_peak*R:10.2f}V")
    pr("")
    pr("  => At 5-6 V on the tether the drop is unacceptable on thin wire.")
    pr("     FIX (recommended): run the tether at ~12 V, regulate to 5-6 V")
    pr("     AT THE ROBOT with a buck. Half the current -> a quarter the loss,")
    pr("     and AWG20-22 power pairs are then fine. Otherwise use AWG18 power")
    pr("     conductors and keep the run short.")
    pr("=" * 62)
    pr("verdict: size the supply for the ~%.0f A PEAK, not the 6 W average;" % I_peak)
    pr("  isolate the MCU rail + bulk cap to stop brownout; send 12 V down the")
    pr("  tether and buck at the robot to beat voltage drop.")
    pr("=" * 62)
    text = "\n".join(L)
    print(text)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "output", "power_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print("\n[saved]", os.path.normpath(out))


if __name__ == "__main__":
    main()
