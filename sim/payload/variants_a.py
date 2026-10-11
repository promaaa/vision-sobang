"""Concept A variants: pan axis fore-aft position, gun offset, pan and tilt angle, counterweight.

    uv run python variants_a.py     # writes results/a_variants.json, results/a_variants.md, results/a_variants.png

Same total add-on mass as A v0 (1.44 kg, estimates). Parts (robot frame, T = torso top):
- deck plate 0.12 kg, fixed at x = 0
- pan unit (pan servo + U bracket) 0.15 kg on the pan axis
- tilt servo 0.07 kg, 0.067 m to the side of the pan axis, turns with the pan
- gun with water and camera 1.10 kg, D m in front of the tilt axis and 0.03 m above it, turns with pan and tilt
- optional counterweight behind the torso at x = -0.12, z = 0.65
Pan angle: + = gun turns to the left. Tilt angle: + = nozzle up.
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import analyze  # noqa: E402
import models  # noqa: E402
from poses import stand_qpos  # noqa: E402

T, Z0 = models.T, models.Z0
TILT_Z = T + 0.095  # tilt axis height (cad/concepts.py pan_tilt)
GUN_M, GUN_UP = 1.10, 0.03
XP = [0.02, -0.02, -0.06]  # pan axis x
D = [0.05, 0.10]  # gun centre in front of the tilt axis
PAN = [0, 45, -45, 90, -90]  # deg
TILT = [-30, 0, 20]  # deg
# counterweight options: (label, mass kg, x, mass removed from x = 0 at the same height)
CW = [("none", 0.0, -0.12, 0.0), ("0.3 kg at x -0.12", 0.3, -0.12, 0.0), ("0.5 kg at x -0.12", 0.5, -0.12, 0.0),
      ("battery 0.6 kg moved x 0 -> -0.12", 0.6, -0.12, 0.6)]
CW_Z = 0.65
PITCH = ("hip_pitch", "knee_pitch", "ankle_pitch")


def parts(xp, d, pan, tilt):
    """(name, mass, (x, y, z) robot frame, box size) for one configuration, angles in degrees."""
    p, t = np.radians(pan), np.radians(tilt)
    r = d * np.cos(t) - GUN_UP * np.sin(t)  # horizontal reach of the gun centre from the pan axis
    gun = (xp + r * np.cos(p), r * np.sin(p), TILT_Z + d * np.sin(t) + GUN_UP * np.cos(t))
    return [("deck_plate", 0.12, (0.0, 0.0, T + 0.003), (0.15, 0.17, 0.006)),
            ("pan_unit", 0.15, (xp, 0.0, T + 0.04), (0.07, 0.11, 0.06)),
            ("tilt_servo", 0.07, (xp - 0.067 * np.sin(p), 0.067 * np.cos(p), T + 0.09), (0.04, 0.02, 0.04)),
            ("gun_with_water_and_camera", GUN_M, tuple(gun), (0.30, 0.07, 0.12))]


def probe_model():
    """Biped with one body per part, so a configuration only changes body_pos and body_mass."""
    s = models.build(None)
    for name in ("deck_plate", "pan_unit", "tilt_servo", "gun_with_water_and_camera", "cw", "cw_removed"):
        b = s.body("base").add_body(name=name, pos=[0, 0, 0.8])
        b.mass, b.ipos, b.inertia, b.explicitinertial = 0.1, [0, 0, 0], [1e-4] * 3, True
    m = s.compile()
    s.add_key(name="stand", qpos=stand_qpos(m, models.STAND), ctrl=np.zeros(m.nu))
    return s.compile()


def configure(m, xp, d, pan, tilt, cw):
    _, cw_m, cw_x, cw_removed = cw
    rows = parts(xp, d, pan, tilt) + [("cw", cw_m, (cw_x, 0, CW_Z), None), ("cw_removed", -cw_removed, (0, 0, CW_Z), None)]
    for name, mass, (x, y, z), size in rows:
        i = m.body(name).id
        m.body_mass[i], m.body_pos[i] = mass, [x, y, z + Z0]
        if size:
            m.body_inertia[i] = models.box_inertia(mass, size)
    mujoco.mj_setConst(m, mujoco.MjData(m))  # recompute subtree masses, or the CoM is wrong


def evaluate(m):
    r = analyze.static_report(m, 0)
    out = {"com_dx": 1000 * r["com_dx"], "com_dy": 1000 * r["com_dy"], "stand": r["stand"]["peak"],
           "crouch": r["crouch"]["peak"]}
    for side in ("left", "right"):
        t = r[f"single_{side}"]["tau"]
        out[f"{side}_all"] = max(abs(t[j]) for j in analyze.LEG)
        out[f"{side}_pitch"] = max(abs(t[j]) for j in analyze.LEG if any(p in j for p in PITCH))
    out["pitch"] = max(out["left_pitch"], out["right_pitch"])
    out["all"] = max(out["left_all"], out["right_all"])
    return out


def sweep():
    m = probe_model()
    res = []
    for cw in CW:
        for xp in XP:
            for d in D:
                for pan in PAN:
                    for tilt in TILT:
                        configure(m, xp, d, pan, tilt, cw)
                        res.append({"cw": cw[0], "xp": xp, "d": d, "pan": pan, "tilt": tilt, **evaluate(m)})
    return res


def worst(res, **sel):
    rows = [r for r in res if all(r[k] == v for k, v in sel.items())]
    return max(rows, key=lambda r: r["pitch"]), max(rows, key=lambda r: r["all"]), rows


def report(res):
    L = ["### A variants: worst case over pan (0, ±45, ±90°) and tilt (-30, 0, +20°), no counterweight", "",
         "| Pan axis x (m) | Gun offset D (m) | CoM fore-aft range (mm) | CoM sideways range (mm) "
         "| Worst single-leg pitch torque (Nm, at pan / tilt) | Worst single-leg torque, all joints (Nm, at pan / tilt) "
         "| Stand peak at pan 0, tilt 0 (Nm) | Crouch peak at pan 0, tilt 0 (Nm) |", "|---|---|---|---|---|---|---|---|"]
    for xp in XP:
        for d in D:
            wp, wa, rows = worst(res, cw="none", xp=xp, d=d)
            p0 = next(r for r in rows if r["pan"] == 0 and r["tilt"] == 0)
            dx = [r["com_dx"] for r in rows]
            dy = [r["com_dy"] for r in rows]
            L.append(f"| {xp:+.2f} | {d:.2f} | {min(dx):+.0f} to {max(dx):+.0f} | {min(dy):+.0f} to {max(dy):+.0f} "
                     f"| {wp['pitch']:.1f} ({wp['pan']:+d}° / {wp['tilt']:+d}°) | {wa['all']:.1f} ({wa['pan']:+d}° / {wa['tilt']:+d}°) "
                     f"| {p0['stand']:.1f} | {p0['crouch']:.1f} |")
    L += ["", "### A variants: counterweight, worst single-leg pitch torque over all pan and tilt angles (Nm)", "",
          "| Pan axis x (m) | Gun offset D (m) | " + " | ".join(c[0] for c in CW) + " |", "|---" * (len(CW) + 2) + "|"]
    for xp in XP:
        for d in D:
            L.append(f"| {xp:+.2f} | {d:.2f} | " + " | ".join(f"{worst(res, cw=c[0], xp=xp, d=d)[0]['pitch']:.1f}" for c in CW) + " |")
    return L


def pan_table(res, xp, d):
    L = [f"### Pan and tilt effect at pan axis x = {xp:+.2f} m, gun offset D = {d:.2f} m, no counterweight", "",
         "| Pan (°) | Tilt (°) | CoM fore-aft (mm) | CoM sideways (mm) | Left stance: pitch / all joints (Nm) "
         "| Right stance: pitch / all joints (Nm) |", "|---|---|---|---|---|---|"]
    for r in res:
        if r["cw"] == "none" and r["xp"] == xp and r["d"] == d:
            L.append(f"| {r['pan']:+d} | {r['tilt']:+d} | {r['com_dx']:+.0f} | {r['com_dy']:+.0f} "
                     f"| {r['left_pitch']:.1f} / {r['left_all']:.1f} | {r['right_pitch']:.1f} / {r['right_all']:.1f} |")
    return L


def plot(res):
    ink2, grid = "#52514e", "#e4e3df"
    colors = {"none": ("#2a78d6", "o"), "0.5 kg at x -0.12": ("#eb6834", "s"),
              "battery 0.6 kg moved x 0 -> -0.12": ("#1baf7a", "^")}
    fig, ax = plt.subplots(figsize=(7.5, 4.6), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for cw, (c, mk) in colors.items():
        for d, ls, z in ((0.05, ":", 3), (0.10, "-", 2)):
            y = [worst(res, cw=cw, xp=xp, d=d)[0]["pitch"] for xp in XP]
            ax.plot(XP, y, ls, color=c, lw=2, marker=mk, ms=7, zorder=z, label=f"{cw}, D = {d:.2f} m")
    for v, txt in ((6, "6 Nm policy limit"), (5, "5 Nm target")):
        ax.axhline(v, color="#0b0b0b" if v == 6 else ink2, lw=1.2, ls="--")
        ax.text(XP[-1], v + 0.04, txt, color=ink2, fontsize=9, ha="right", va="bottom")
    ax.set_xlabel("Pan axis x, robot frame (m). Right = further back")
    ax.set_ylabel("Worst single-leg pitch torque (Nm)")
    ax.set_title("Concept A: worst case over pan and tilt angles", loc="left", fontsize=11)
    ax.invert_xaxis()
    ax.set_xticks(XP)
    ax.grid(color=grid)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.savefig(os.path.join(analyze.OUT, "a_variants.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def self_check():
    """The probe model in the v0-like pose must match the hand computation of the gun position."""
    x, y, z = parts(-0.06, 0.10, 90, 0)[3][2]
    assert abs(x + 0.06) < 1e-9 and abs(y - 0.10) < 1e-9 and abs(z - (TILT_Z + GUN_UP)) < 1e-9
    m = probe_model()
    configure(m, 0.02, 0.05, 0, 0, CW[0])
    assert abs(m.body_subtreemass[1] - (models.URDF_MASS["biped"] + 1.44)) < 1e-3
    configure(m, 0.02, 0.05, 0, 0, CW[3])  # battery move keeps the total mass
    assert abs(m.body_subtreemass[1] - (models.URDF_MASS["biped"] + 1.44)) < 1e-3
    assert np.allclose(m.body_ipos[m.body("cw").id], 0)  # mass sits at the body position
    gun = dict((n, p) for n, _, p, _ in models.PARTS["A"])["gun_body_camera"]  # models.py A = this sweep at
    assert np.allclose(gun, parts(-0.06, 0.10, 0, 0)[3][2])  # pan axis -0.06, D 0.10, pan 0, tilt 0
    print("self-check variants_a: gun position, total mass, models.py A matches")


def model_files():
    """Static and dynamic results of the saved model files bhl_A_v0.xml and bhl_A.xml."""
    L = ["### Model files: A v0 (first version) and A v1 (new bhl_A.xml)", "",
         "| Model | CoM fore-aft (mm) | Stand peak (Nm) | Crouch peak (Nm) | Single-leg pitch peak (Nm) "
         "| Single-leg peak, all joints (Nm) | kp 50 / kd 2 / 6 Nm | kp 200 / kd 5 / 6 Nm | Push fwd / back (N s), kp 200 / kd 5 / 20 Nm |",
         "|---|---|---|---|---|---|---|---|---|"]
    for v in ("A_v0", "A"):
        m = models.load(v)
        r = evaluate(m)
        st = [analyze.simulate(m, kp, kd, lim) for kp, kd, lim in ((50, 2, 6), (200, 5, 6))]
        push = [analyze.max_push(m, 200, 5, 20, s) for s in (1, -1)]
        cells = [f"stands, {s[2]:.1f} Nm" if s[0] else f"falls at {s[2]:.1f} s" for s in st]
        L.append(f"| {v} | {r['com_dx']:+.0f} | {r['stand']:.1f} | {r['crouch']:.1f} | {r['pitch']:.1f} | {r['all']:.1f} "
                 f"| {cells[0]} | {cells[1]} | {push[0]:.1f} / {push[1]:.1f} |")
    return L


if __name__ == "__main__":
    self_check()
    res = sweep()
    json.dump(res, open(os.path.join(analyze.OUT, "a_variants.json"), "w"), indent=0)
    L = report(res)
    for xp in XP:
        L += [""] + pan_table(res, xp, 0.10)
    L += [""] + model_files()
    open(os.path.join(analyze.OUT, "a_variants.md"), "w").write("\n".join(L) + "\n")
    plot(res)
    print("\n".join(L))
