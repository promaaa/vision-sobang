"""Where should payload mass go? Move a 2 kg point mass over a grid of (x, z) positions on the biped,
then compute static peak torques and the push the stiff PD stance survives. Also: how much mass fits
before the static torques reach 6 Nm and 20 Nm, for two mass positions (BUDGET_AT).

    uv run python placement.py      # writes results/placement.json
"""
import json
import os

import mujoco
import numpy as np

import analyze
import models

PROBE = 2.0  # kg
XS = np.round(np.arange(-0.20, 0.151, 0.05), 3)  # robot frame, m
ZS = np.round(np.arange(0.45, 1.051, 0.10), 3)
PITCH = ("hip_pitch", "knee_pitch", "ankle_pitch")
BUDGET_AT = [("torso top centre (x 0, z 0.791)", 0.0, models.T), ("backpack (x -0.145, z 0.64)", -0.145, 0.64)]


def set_probe(m, mass, x, z):
    m.body_mass[m.body("probe").id] = mass
    m.body_pos[m.body("probe").id] = [x, 0.0, z + models.Z0]
    mujoco.mj_setConst(m, mujoco.MjData(m))  # recompute body_subtreemass, or the whole-body CoM is wrong


def peaks(r):
    """Peak |torque| of the pitch joints and of all leg joints, for stand, crouch and single-leg stance."""
    out = {}
    for k in ("stand", "crouch", "single"):
        t = r[k]["tau"]
        out[k] = max(abs(t[j]) for j in analyze.LEG)
        out[k + "_pitch"] = max(abs(t[j]) for j in analyze.LEG if any(p in j for p in PITCH))
    return out


if __name__ == "__main__":
    from poses import stand_qpos
    s = models.build(None)
    b = s.body("base").add_body(name="probe", pos=[0, 0, 0.6])
    b.mass, b.ipos, b.inertia, b.explicitinertial = 1.0, [0, 0, 0], [1e-4] * 3, True
    m = s.compile()
    s.add_key(name="stand", qpos=stand_qpos(m, models.STAND), ctrl=np.zeros(m.nu))
    m = s.compile()
    grid = []
    for x in XS:
        for z in ZS:
            set_probe(m, PROBE, x, z)
            r = analyze.static_report(m, 0)
            push = {sgn: analyze.max_push(m, 200, 5, 20, sgn) for sgn in (1, -1)}
            grid.append({"x": float(x), "z": float(z), "com_dx": r["com_dx"], **peaks(r), "push_fwd": push[1],
                         "push_back": push[-1]})
            print(grid[-1], flush=True)
    # mass budget at two places: torso top centre (x = 0, z = T), and backpack tank position (B, C)
    budget = {}
    for name, x, z in BUDGET_AT:
        budget[name] = []
        for mass in np.arange(0.0, 10.01, 0.5):
            set_probe(m, mass, x, z)
            budget[name].append({"mass": float(mass), **peaks(analyze.static_report(m, 0))})
    os.makedirs(analyze.OUT, exist_ok=True)
    json.dump({"probe": PROBE, "grid": grid, "budget": budget}, open(os.path.join(analyze.OUT, "placement.json"), "w"),
              indent=1)
