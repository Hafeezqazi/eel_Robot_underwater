# CFD case — steady drag study (OpenFOAM)

A ready-to-run **simpleFoam** case that computes the **parasitic drag** of the
rigid eel hull and a drag coefficient, to validate the `CD_AXIAL = 0.10`
assumption used in `analysis/sizing.py`. Flow is along **+Z** (the body axis).

> This is the **rigid-body drag** study. The *swimming thrust* is a separate,
> much harder moving-boundary problem (overset / dynamic mesh) — see "Going
> further" below. For first-order design, drag here + Lighthill thrust in
> `analysis/swim_sim.py` is enough to size the robot.

## Prerequisites

- **OpenFOAM** (v2012+ / .org v9+). Not native on Windows — use **WSL2**,
  a Linux box, or the **openfoam Docker image**.
- The hull surface `output/cfd_hull.stl` — generate it first:
  ```bash
  cd ../cad && python hull_solid.py
  ```

## Run

```bash
cd cfd
python case_setup.py     # copies the STL in, prints Re and the analytic drag
./Allrun                 # blockMesh -> snappy -> simpleFoam (needs OpenFOAM)
```

Watch convergence (`log.simpleFoam`); residuals should drop below 1e-4.

## Get the answer

```bash
# drag force & coefficient history:
cat postProcessing/forces/0/coefficient.dat
```
- **Cd** column (once converged) is the drag coefficient on the reference area
  `Aref = 0.00385 m^2` (frontal). Compare to the `0.10` assumed in sizing.
- If CFD Cd differs, update `CD_AXIAL` in `cad/params.py` and re-run
  `analysis/sizing.py` + `analysis/swim_sim.py` to refresh the speed/power
  predictions. **This is the validation loop.**

## What's set

| Item | Value | File |
|---|---|---|
| Inlet speed | 0.5 m/s (+Z) | `0/U`, `controlDict` magUInf |
| Water ν | 1e-6 m²/s | `constant/transportProperties` |
| Reynolds | ~2.5e5 (turbulent) | — |
| Turbulence | k-ω SST RANS | `constant/turbulenceProperties` |
| Domain | 0.7×0.7×2.2 m box | `system/blockMeshDict` |
| Surface refinement | snappy level 2–3 | `system/snappyHexMeshDict` |
| Wall layers | **off** (enable for y⁺ study) | `snappyHexMeshDict` |

To sweep speed, change `0/U`, `controlDict` `magUInf`, and the value in
`case_setup.py`, then re-run — drag should scale ≈ U².

## Going further (swimming thrust)

The undulating-body thrust needs the joints to move the surface in time:
- **overset mesh** (one background + a body mesh per segment) driven by the
  gait, or **dynamicMotionSolverFvMesh** with prescribed boundary motion from
  `firmware/gait.py`, solved with `pimpleFoam` (transient).
- That's a multi-day setup; ask and I can scaffold it next. For now the
  rigid-drag Cd + Lighthill EBT give a validated first-order speed/power.
