"""Round 3: compare A_real and B_real (masses and CoM from the CAD outputs) with the older A and B models.

    uv run python real_parts.py     # needs models/*.xml (models.py), writes results/real_parts.md
"""
import os

import numpy as np

import analyze
import models

ROWS = [("A v0 (first estimate)", "A_v0"), ("A v1 (round 2)", "A"), ("A_real (CAD top module + gun + guard)", "A_real"),
        ("B (first estimate), full", "B"), ("B (first estimate), empty", "B_empty"),
        ("B_real (CAD backpack + guard + old head), full", "B_real"), ("B_real, empty", "B_real_empty")]
PD = [(50, 2, 6), (50, 2, 20), (200, 5, 6)]
PITCH = ("hip_pitch", "knee_pitch", "ankle_pitch")


def row(label, v):
    m = models.load(v)
    r = analyze.static_report(m, 0)
    base = models.URDF_MASS["biped"]
    t = r["single"]["tau"]
    pitch = max(max(abs(r[f"single_{s}"]["tau"][j]) for j in analyze.LEG if any(p in j for p in PITCH))
                for s in ("left", "right"))
    pd = []
    for kp, kd, lim in PD:
        stood, _, x = analyze.simulate(m, kp, kd, lim)
        pd.append(f"stands, {x:.1f} Nm" if stood else f"falls at {x:.1f} s")
    return (f"| {label} | {r['mass'] - base:.2f} | {1000 * r['com_dx']:+.0f} / {1000 * r['com_dy']:+.0f} "
            f"| {r['stand']['peak']:.1f} | {r['crouch']['peak']:.1f} | {pitch:.1f} | {r['single']['peak']:.1f} "
            f"| {' | '.join(pd)} |"), pitch


def self_check():
    m = models.load("A_real")  # module with gun: same total mass and CoM as cad/parts/out/assembly.json
    a = [p for p in models.PARTS["A_real"] if p[0] != "splash_guard"]
    mass = sum(p[1] for p in a)
    com = sum(p[1] * np.array(p[2]) for p in a) / mass
    assert abs(mass - 1.452) < 1e-6 and np.allclose(com, [-0.046, -0.001, 0.904], atol=1e-6), (mass, com)
    assert abs(m.body_subtreemass[1] - models.URDF_MASS["biped"] - 1.543) < 1e-3
    assert abs(models.payload_mass("B_real") - 0.35 - 0.091 - 2.318) < 1e-6  # head + guard + backpack full
    assert abs(models.payload_mass("B_real", True) - 0.35 - 0.091 - 1.372) < 1e-6  # backpack empty
    print("self-check real_parts: A_real CoM and masses match the CAD files")


if __name__ == "__main__":
    self_check()
    L = ["| Model | Add-on mass (kg) | CoM offset fore-aft / sideways (mm) | Stand peak (Nm) | Crouch peak (Nm) "
         "| Single-leg pitch peak (Nm) | Single-leg peak, all joints (Nm) | "
         + " | ".join(f"PD kp {kp} / kd {kd} / {lim} Nm" for kp, kd, lim in PD) + " |",
         "|---" * (7 + len(PD)) + "|"]
    for label, v in ROWS:
        line, _ = row(label, v)
        L.append(line)
        print(line, flush=True)
    open(os.path.join(analyze.OUT, "real_parts.md"), "w").write("\n".join(L) + "\n")
