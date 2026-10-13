"""Round 5: the TCS M400K-V pump inside the torso, with tank R1 (inside the torso) or R2 (two side tanks).

    uv run python sim/payload/torso_tank.py          # all runs, about 10 min on 6 cores -> results/torso_tank.md,
                                                     # results/torso_tank.json, results/torso_*.png
    uv run python sim/payload/torso_tank.py check    # self-check (slosh formulas, jet, model layout), 10 s
    MUJOCO_GL=egl uv run python sim/payload/torso_tank.py video   # results/torso_*.mp4 (needs ffmpeg)

Needs models/bhl_R1*.xml and models/bhl_R2*.xml: run cad/torso_tank/body.py, then models.py.
The walking loop copies sim/sim2sim/run.py (shipped BHL policy, 25 Hz policy, 2000 Hz physics, kp 20 / kd 2,
torque clipped, training observation noise) and adds a push on the torso and a water slosh model.
"""
import json
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "sim2sim"), str(HERE.parent.parent / "aim")]
import analyze  # noqa: E402
import ballistics  # noqa: E402  aim/ballistics.py
import models  # noqa: E402
import report  # noqa: E402  palette and plot style of rounds 1-4
import run as s2s  # noqa: E402  sim/sim2sim/run.py, not modified
from poses import stand_qpos  # noqa: E402

plt = report.plt
OUT = HERE / "results"
G = 9.81
ROWS = [("bare biped", "biped"), ("A_real: water gun on the pan-tilt", "A_real"),
        ("B_real: backpack + Seaflo pump, full", "B_real"), ("B_real, empty", "B_real_empty"),
        ("R1: tank inside the torso, full", "R1"), ("R1, half", "R1_half"), ("R1, empty", "R1_empty"),
        ("R2: side tanks, full", "R2"), ("R2, half", "R2_half"), ("R2, empty", "R2_empty")]
COMMANDS = {"stand": (0.0, 0.0, 0.0), "vx 0.3": (0.3, 0.0, 0.0), "vx 0.2 + yaw 0.5": (0.2, 0.0, 0.5)}
LIMITS = (6.0, 4.0)
PUSH_DIRS = {"forward": 0.0, "back": math.pi, "left": math.pi / 2, "right": -math.pi / 2}
PUSH_CMDS = {"standing": (0.0, 0.0, 0.0), "walking 0.3 m/s": (0.3, 0.0, 0.0)}
PUSH_T = (3.0, 3.2, 3.4)  # s, three push times = three gait phases; the table keeps the worst one
PUSH_HI, PUSH_ITERS = 24.0, 6  # N s upper bound, bisection steps (resolution 0.375 N s)

# Slosh (equivalent mechanical model, first mode of a rectangular tank, NASA SP-106 / Ibrahim 2005):
# w^2 = (pi g / L) tanh(pi h / L), slosh mass m1 = m 8 tanh(pi h / L) / (pi^3 h / L), at the water centroid.
# One mass per tank on an x and a y spring; mass = the larger of the x and y values (conservative).
# "baffle" uses the baffle cells of the CAD (cad/torso_tank/body.py). Damping ratios are ASSUMED.
SLOSH = {"nobaffle": {"baffles": False, "zeta": 0.01}, "baffle": {"baffles": True, "zeta": 0.05}}
SLOSH_RUNS = ["R1_half", "R1_half_slosh_nobaffle", "R1_half_slosh_baffle",
              "R2_half", "R2_half_slosh_nobaffle", "R2_half_slosh_baffle"]

# Pump curve, TCS M400K at 12 V: 1150 mL/min free flow, 380 mbar max (TCS M400 range page, read 2026-10-13).
# Straight line between the two points (GUESS, typical shape). Nozzle velocity coefficient 0.95 (GUESS).
PUMP_Q0, PUMP_PMAX, NOZZLE_CV = 1.15 / 60000, 38e3, 0.95
LIFT, TUBE_L, TUBE_D = 0.20, 0.6, 0.0032  # m: pump to nozzle height, tube length (GUESS), bore
NOZZLE_Z = 0.90  # m, nozzle height over the floor on the pan-tilt (CAD, tilt 0)


# ---------------- slosh models ----------------
def slosh_params(L, h, m):
    k = math.pi * h / L
    return math.sqrt(math.pi * G / L * math.tanh(k)), m * 8 * math.tanh(k) / (math.pi ** 2 * k)


def write_slosh_models():
    asm = json.load(open(HERE.parent.parent / "cad/torso_tank/out/assembly.json"))["options"]
    info = {}
    for key in ("R1", "R2"):
        dims = asm[key]["slosh"]
        for tag, cfg in SLOSH.items():
            name = f"{key}_half_slosh_{tag}"
            s = models.build(f"{key}_half")
            s.modelname = f"bhl_{name}"
            lx = dims["lx_m"] / (dims["cells_x"] if cfg["baffles"] else 1)
            ly = dims["ly_m"] / (dims["cells_y"] if cfg["baffles"] else 1)
            for w in asm[key]["water"]["half"]:
                h = w["size_m"][2]  # fill depth
                wx, mx = slosh_params(lx, h, w["mass_kg"])
                wy, my = slosh_params(ly, h, w["mass_kg"])
                ms = max(mx, my)
                b = s.body(f"payload_{w['name']}")
                b.mass -= ms
                sb = b.add_body(name=f"slosh_{w['name']}", pos=[0, 0, 0])
                sb.mass, sb.ipos, sb.inertia, sb.explicitinertial = ms, [0, 0, 0], [1e-5] * 3, True
                for axis, wn, L in (([1, 0, 0], wx, lx), ([0, 1, 0], wy, ly)):
                    j = sb.add_joint(name=f"slosh_{w['name']}_{'xy'[axis.index(1)]}", type=mujoco.mjtJoint.mjJNT_SLIDE,
                                     axis=axis, stiffness=[ms * wn * wn, 0, 0], damping=[2 * cfg["zeta"] * ms * wn, 0, 0],
                                     range=[-0.25 * L, 0.25 * L], limited=mujoco.mjtLimited.mjLIMITED_TRUE)
                sb.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.018, 0, 0], contype=0, conaffinity=0, group=1,
                            mass=0, rgba=[0.2, 0.95, 1.0, 1])  # visual only
                info[f"{name}/{w['name']}"] = {"f_x_hz": wx / 2 / math.pi, "f_y_hz": wy / 2 / math.pi, "m_water": w["mass_kg"],
                                               "m_slosh": ms, "share": ms / w["mass_kg"], "depth_m": h}
            m = s.compile()
            s.add_key(name="stand", qpos=stand_qpos(m, models.STAND), ctrl=np.zeros(m.nu))
            with open(models.path(name), "w") as f:
                f.write(s.to_xml().replace(f'meshdir="{s.meshdir}', f'meshdir="{models.MESHDIR}'))
    return info


# ---------------- policy loop with a push ----------------
def policy_run(model, cmd, limit=6.0, seconds=10.0, push=None, seed=0, frames=None, log=None):
    """One run of the shipped BHL policy. push = (t0 s, impulse N s, direction rad in the heading frame, 0 = forward):
    a horizontal force on the torso for 0.1 s. Returns the fall time (s) or None. log gets one row per policy step:
    time, base x, base y, then the slosh joint positions."""
    m = mujoco.MjModel.from_xml_path(str(models.path(model)))
    m.opt.timestep = s2s.PHYSICS_DT
    d = mujoco.MjData(m)
    d.qpos[7:19] = s2s.DEFAULT  # BHL reset, as run.py start="bhl"
    mujoco.mj_forward(m, d)
    policy = ort.InferenceSession(str(s2s.POLICY), providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(seed)
    base, z0 = m.body("base").id, d.site("imu").xpos[2]
    action, c = np.zeros(12, dtype=np.float32), np.array(cmd, dtype=np.float32)
    sub = round(s2s.POLICY_DT / s2s.PHYSICS_DT)
    for _ in range(round(seconds / s2s.POLICY_DT)):
        obs = s2s.observation(c, d.sensor("imu_quat").data.copy(), d.sensor("imu_gyro").data.copy(),
                              d.qpos[7:19], d.qvel[6:18], action)
        obs += (rng.uniform(-1, 1, 45) * s2s.NOISE).astype(np.float32)
        action = policy.run(None, {"obs": obs})[0][0]
        target = s2s.DEFAULT + s2s.ACTION_SCALE * action
        for _ in range(sub):
            d.ctrl[:] = np.clip(s2s.KP * (target - d.qpos[7:19]) - s2s.KD * d.qvel[6:18], -limit, limit)
            d.xfrc_applied[base, :3] = 0
            if push and push[0] <= d.time < push[0] + 0.1:
                R = d.xmat[base].reshape(3, 3)
                a = math.atan2(R[1, 0], R[0, 0]) + push[2]
                d.xfrc_applied[base, :2] = push[1] / 0.1 * np.array([math.cos(a), math.sin(a)])
            mujoco.mj_step(m, d)
            if frames and d.time * 30 >= frames.n:
                frames(m, d)
        if log is not None:
            log.append([d.time, *d.xpos[base][:2], *d.qpos[19:]])
        tilt = np.arccos(np.clip(-s2s.quat_rotate_inverse(d.sensor("imu_quat").data, np.array([0, 0, -1.0]))[2], -1, 1))
        if tilt > s2s.TILT_LIMIT or d.site("imu").xpos[2] < 0.6 * z0:
            return float(d.time)
    return None


def max_push(model, cmd, angle, t0):
    """Largest push (N s) with no fall in the 3 s after it, by bisection. 0 when the model falls without a push."""
    if policy_run(model, cmd, seconds=t0 + 3.0) is not None:
        return 0.0
    lo, hi = 0.0, PUSH_HI
    for _ in range(PUSH_ITERS):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if policy_run(model, cmd, seconds=t0 + 3.0, push=(t0, mid, angle)) is None else (lo, mid)
    return lo


def walk_job(model, cmd_name, limit):
    r = s2s.simulate(model, COMMANDS[cmd_name], limit, 20.0, noise=True)
    return {"model": model, "cmd": cmd_name, "limit": limit, "fall": r["fall"], "vx": r["vx"], "wz": r["wz"]}


def push_job(model, cmd_name, dir_name, t0):
    return {"model": model, "cmd": cmd_name, "dir": dir_name, "t0": t0,
            "impulse": max_push(model, PUSH_CMDS[cmd_name], PUSH_DIRS[dir_name], t0)}


def slosh_log(model, cmd_name):
    log = []
    fall = policy_run(model, COMMANDS[cmd_name], seconds=20.0, log=log)
    return {"model": model, "cmd": cmd_name, "fall": fall, "log": np.array(log).tolist()}


# ---------------- jet ----------------
def jet(d_mm):
    """Operating point with a round nozzle of d_mm: straight-line pump curve, minus the lift to the nozzle and the
    friction in the 3.2 mm tube (laminar 64/Re or Blasius). Returns (flow L/min, exit speed m/s)."""
    a, at = math.pi * (d_mm / 1000) ** 2 / 4, math.pi * TUBE_D ** 2 / 4

    def p_nozzle(q):
        vt = q / at
        re = 1000 * vt * TUBE_D / 1.0e-3
        f = 64 / re if re < 2300 else 0.316 * re ** -0.25
        return PUMP_PMAX * (1 - q / PUMP_Q0) - 1000 * G * LIFT - f * TUBE_L / TUBE_D * 500 * vt * vt

    lo, hi = 1e-9, PUMP_Q0
    for _ in range(60):  # nozzle flow at the pump pressure, minus the flow asked: falls with q
        q = (lo + hi) / 2
        lo, hi = (q, hi) if a * NOZZLE_CV * math.sqrt(2 * max(p_nozzle(q), 0) / 1000) > q else (lo, q)
    return q * 60000, q / a


# ---------------- report ----------------
def static_rows():
    res = {}
    for label, v in ROWS:
        r = analyze.static_report(v, 0)
        pitch = max(max(abs(r[f"single_{s}"]["tau"][j]) for j in analyze.LEG if any(p in j for p in report.PITCH))
                    for s in ("left", "right"))
        res[v] = {"label": label, "mass": r["mass"], "add": r["mass"] - models.URDF_MASS["biped"],
                  "com_dx": r["com_dx"], "com_dy": r["com_dy"], "com_h": r["com_h"], "stand": r["stand"]["peak"],
                  "crouch": r["crouch"]["peak"], "single_pitch": pitch, "single_all": r["single"]["peak"]}
    return res


def tables(res):
    st, walk, push, slosh = res["static"], res["walk"], res["push"], res["slosh"]
    L = ["#### Statics: torques in slow poses (same method as rounds 1 to 3)", "",
         "| Model | Add-on mass (kg) | CoM height (m) | CoM fore-aft / sideways (mm) | Stand peak (Nm) | Crouch peak (Nm) "
         "| Single-leg pitch peak (Nm) | Single-leg peak, all joints (Nm) |", "|---|---|---|---|---|---|---|---|"]
    for v, r in st.items():
        L.append(f"| {r['label']} | {r['add']:.2f} | {r['com_h']:.3f} | {1000 * r['com_dx']:+.0f} / {1000 * r['com_dy']:+.0f} "
                 f"| {r['stand']:.1f} | {r['crouch']:.1f} | {r['single_pitch']:.1f} | {r['single_all']:.1f} |")
    L += ["", "#### Walking with the shipped BHL policy, 20 s, training noise", "",
          "| Model | " + " | ".join(f"{c}, {lim:g} Nm" for lim in LIMITS for c in COMMANDS) + " |",
          "|---" * (1 + len(LIMITS) * len(COMMANDS)) + "|"]
    for label, v in ROWS + [(n, n) for n in SLOSH_RUNS if "slosh" in n]:
        cells = []
        for lim in LIMITS:
            for c in COMMANDS:
                w = next(w for w in walk if w["model"] == f"bhl_{v}" and w["cmd"] == c and w["limit"] == lim)
                cells.append(f"falls at {w['fall']:.1f} s" if w["fall"] is not None else
                             (f"{w['vx']:+.2f} m/s" if c == "vx 0.3" else f"{w['vx']:+.2f} m/s, {w['wz']:+.2f} rad/s"
                              if "yaw" in c else "stands"))
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L += ["", "Speeds are the mean forward speed and yaw rate from 5 to 20 s.", "",
          "#### Largest push the policy survives (N s, 0.1 s on the torso, worst of 3 gait phases, 6 Nm)", "",
          "| Model | " + " | ".join(f"{c}: {d}" for c in PUSH_CMDS for d in PUSH_DIRS) + " |",
          "|---" * (1 + len(PUSH_CMDS) * len(PUSH_DIRS)) + "|"]
    for label, v in ROWS + [(n, n) for n in SLOSH_RUNS if "slosh" in n]:
        cells = [f"{push_worst(push, v, c, d):.1f}" for c in PUSH_CMDS for d in PUSH_DIRS]
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L += ["", "#### Slosh model (half-full tanks)", "",
          "| Model / tank | Water (kg) | Fill depth (mm) | Slosh mass (kg, share) | Slosh frequency x / y (Hz) |",
          "|---|---|---|---|---|"]
    for k, s in slosh["params"].items():
        L.append(f"| {k} | {s['m_water']:.3f} | {1000 * s['depth_m']:.0f} | {s['m_slosh']:.3f} ({100 * s['share']:.0f} %) "
                 f"| {s['f_x_hz']:.1f} / {s['f_y_hz']:.1f} |")
    L += ["", "| Model | Command | Slosh travel x, RMS / peak (mm) | Slosh travel y, RMS / peak (mm) |", "|---|---|---|---|"]
    for r in slosh["logs"]:
        a = np.array(r["log"])
        if a.shape[1] < 5:
            continue
        a = a[a[:, 0] > 5.0]
        x, y = 1000 * a[:, 3], 1000 * a[:, 4]
        L.append(f"| {r['model']} | {r['cmd']} | {np.sqrt((x ** 2).mean()):.1f} / {np.abs(x).max():.1f} "
                 f"| {np.sqrt((y ** 2).mean()):.1f} / {np.abs(y).max():.1f} |")
    L += ["", "#### Jet of the TCS M400K-V at 12 V (estimate, no air drag)", "",
          "| Nozzle (mm) | Flow (L/min) | Exit speed (m/s) | Range to the floor from 0.9 m, no drag (m) |", "|---|---|---|---|"]
    for j in res["jet"]:
        L.append(f"| {j['d_mm']:.1f} | {j['q_lpm']:.2f} | {j['v']:.1f} | {j['range_m']:.1f} |")
    return "\n".join(L) + "\n"


def short(v):
    """Plot label: model and fill."""
    if v in ("biped", "A_real"):
        return {"biped": "bare biped", "A_real": "A_real (gun)"}[v]
    return v.replace("_empty", " empty").replace("_half", " half") + ("" if "_" in v and v != "B_real" else " full")


def push_worst(push, v, c, d):
    return min(p["impulse"] for p in push if p["model"] == v and p["cmd"] == c and p["dir"] == d)


def plots(res):
    st = res["static"]
    keys = [v for _, v in ROWS]
    y = np.arange(len(keys))[::-1]
    # 1. torques
    fig, ax = plt.subplots(figsize=(8, 5.2))
    series = [("stand", "stand", report.S1), ("crouch", "crouch", report.S3),
              ("single_pitch", "one-leg stance, pitch joints", report.S2), ("single_all", "one-leg stance, all joints", report.INK2)]
    for i, (k, name, col) in enumerate(series):
        ax.barh(y + (1.5 - i) * 0.2, [st[v][k] for v in keys], 0.2, color=col, label=name)
    ax.axvline(6, color=report.INK, lw=1.2, ls="--")
    ax.text(6.1, y[0] + 0.45, "6 Nm policy limit", fontsize=9)
    ax.set_yticks(y, [short(v) for v in keys])
    ax.set_xlabel("peak static leg torque (Nm)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False, fontsize=9)
    ax.grid(axis="x", color=report.GRID)
    report.save(fig, "torso_torque.png")
    # 2. centre of mass
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    groups = {"bare biped": (["biped"], report.INK2), "A_real (gun on top)": (["A_real"], report.INK),
              "B_real (backpack)": (["B_real", "B_real_empty"], report.S2),
              "R1 (tank inside the torso)": (["R1", "R1_half", "R1_empty"], report.S1),
              "R2 (side tanks)": (["R2", "R2_half", "R2_empty"], report.S3)}
    for name, (vs, col) in groups.items():
        xs, zs = [1000 * st[v]["com_dx"] for v in vs], [st[v]["com_h"] for v in vs]
        ax.plot(xs, zs, "-o", color=col, label=name, ms=6)
        ax.annotate("full" if len(vs) > 1 else "", (xs[0], zs[0]), textcoords="offset points", xytext=(6, 4), fontsize=8, color=col)
    ax.set_xlabel("CoM fore-aft offset from the centre of the feet (mm, + forward)")
    ax.set_ylabel("CoM height (m)")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(color=report.GRID)
    report.save(fig, "torso_com.png")
    # 3. push
    fig, axs = plt.subplots(1, 2, figsize=(10, 5.2), sharey=True)
    cols = [report.S1, report.S2, report.S3, report.INK2]
    for ax, c in zip(axs, PUSH_CMDS):
        for i, (dname, col) in enumerate(zip(PUSH_DIRS, cols)):
            ax.barh(y + (1.5 - i) * 0.2, [push_worst(res["push"], v, c, dname) for v in keys], 0.2, color=col, label=dname)
        ax.set_title(c, fontsize=10)
        ax.set_xlabel("largest push survived (N s)")
        ax.grid(axis="x", color=report.GRID)
    axs[0].set_yticks(y, [short(v) for v in keys])
    axs[1].legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(-0.1, -0.12), ncol=4)
    report.save(fig, "torso_push.png")
    # 4. slosh
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, key in zip(axs, ("R1", "R2")):
        for r in res["slosh"]["logs"]:
            if r["model"].startswith(f"{key}_half_slosh") and r["cmd"] == "vx 0.2 + yaw 0.5":
                a = np.array(r["log"])
                tag = r["model"].split("_")[-1]
                ax.plot(a[:, 0], 1000 * a[:, 3], color=report.S1 if tag == "nobaffle" else report.S2, lw=1,
                        label=f"fore-aft, {'no baffles' if tag == 'nobaffle' else 'baffles'}")
                ax.plot(a[:, 0], 1000 * a[:, 4], color=report.S1 if tag == "nobaffle" else report.S2, lw=1, ls=":",
                        label=f"sideways, {'no baffles' if tag == 'nobaffle' else 'baffles'}")
        ax.set_title(f"{key} half full, walking 0.2 m/s and turning 0.5 rad/s", fontsize=10)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("slosh mass travel (mm)")
        ax.grid(color=report.GRID)
    axs[0].legend(frameon=False, fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(1.1, -0.16))
    report.save(fig, "torso_slosh.png")
    # 5. jet
    fig, ax = plt.subplots(figsize=(6.5, 4))
    d = [j["d_mm"] for j in res["jet"]]
    ax.plot(d, [j["range_m"] for j in res["jet"]], "-o", color=report.S1, label="range to the floor, no drag (m)")
    ax.plot(d, [j["v"] for j in res["jet"]], "-o", color=report.S2, label="exit speed (m/s)")
    ax.plot(d, [j["q_lpm"] for j in res["jet"]], "-o", color=report.S3, label="flow (L/min)")
    ax.set_xlabel("nozzle diameter (mm)")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(color=report.GRID)
    report.save(fig, "torso_jet.png")


def main():
    slosh_params_info = write_slosh_models()
    res = {"static": static_rows()}
    print("statics done", flush=True)
    models_all = [v for _, v in ROWS] + [n for n in SLOSH_RUNS if "slosh" in n]
    with Pool(6) as pool:  # CPU only
        res["walk"] = pool.starmap(walk_job, [(f"bhl_{v}", c, lim) for v in models_all for c in COMMANDS for lim in LIMITS])
        print("walking done", flush=True)
        res["push"] = pool.starmap(push_job, [(v, c, d, t0) for v in models_all for c in PUSH_CMDS for d in PUSH_DIRS
                                              for t0 in PUSH_T])
        print("push done", flush=True)
        logs = pool.starmap(slosh_log, [(v, c) for v in SLOSH_RUNS if "slosh" in v for c in ("vx 0.3", "vx 0.2 + yaw 0.5")])
    res["slosh"] = {"params": slosh_params_info, "logs": logs}
    res["jet"] = []
    for d in (1.0, 1.5, 2.0, 2.5, 3.0):
        q, v = jet(d)
        res["jet"].append({"d_mm": d, "q_lpm": q, "v": v, "range_m": ballistics.max_range(v, -NOZZLE_Z)})
    (OUT / "torso_tank.json").write_text(json.dumps(res))
    (OUT / "torso_tank.md").write_text(tables(res))
    plots(res)
    print(tables(res))


def redo_report():
    res = json.load(open(OUT / "torso_tank.json"))
    (OUT / "torso_tank.md").write_text(tables(res))
    plots(res)


def video(model, cmd, out, seconds=10.0, push=None, dist=2.2, azim=135.0, elev=-15.0, xray=False, look_dz=0.0):
    """30 fps, 640 x 480, the camera follows the torso (as sim2sim/run.py video()). xray: the torso and the dry
    payload parts are see-through, so the water boxes and the slosh mass (blue sphere) show."""
    w, h = 640, 480
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                           "-r", "30", "-i", "-", "-pix_fmt", "yuv420p", str(OUT / out)], stdin=subprocess.PIPE)
    st = {}

    def grab(m, d):
        if not st:
            st["r"] = mujoco.Renderer(m, h, w)
            cam = mujoco.MjvCamera()
            cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            cam.distance, cam.elevation, cam.azimuth = dist, elev, azim
            st["cam"], st["base"] = cam, m.body("base").id
            for g in range(m.ngeom) if xray else []:
                b = m.body(m.geom_bodyid[g]).name
                if b == "base" or b.startswith("payload_"):
                    m.geom_matid[g] = -1
                    m.geom_rgba[g] = ([0.45, 0.45, 0.47, 0.18] if b == "base" else [0.25, 0.55, 0.9, 0.3]
                                      if b.startswith("payload_water") else [0.85, 0.2, 0.1, 0.06])
        st["cam"].lookat[:] = d.subtree_com[st["base"]] + [0, 0, look_dz]  # whole-robot CoM, as the tracking camera
        st["r"].update_scene(d, st["cam"])
        ff.stdin.write(st["r"].render().tobytes())
        grab.n += 1
    grab.n = 0
    fall = policy_run(model, cmd, seconds=seconds, push=push, frames=grab)
    ff.stdin.close()
    ff.wait()
    st["r"].close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(OUT / out), "-frames:v", "1",
                    str(OUT / out.replace(".mp4", "_poster.jpg"))], check=True)
    print(out, "fall" if fall else "no fall", fall)


def videos():
    res = json.load(open(OUT / "torso_tank.json"))
    video("R1", COMMANDS["vx 0.2 + yaw 0.5"], "torso_R1_walk.mp4")
    video("R2", COMMANDS["vx 0.2 + yaw 0.5"], "torso_R2_walk.mp4")
    # the same backward push while walking on B_real, R1 and R2: 1 N s above the worst-phase limit of B_real,
    # at the push time where B_real is weakest. R1 and R2 survive this push at all three push times (table).
    w = "walking 0.3 m/s"
    j = push_worst(res["push"], "B_real", w, "back") + 1.0
    t0 = min(PUSH_T, key=lambda t: next(p["impulse"] for p in res["push"] if p["model"] == "B_real" and p["t0"] == t
                                        and p["cmd"] == w and p["dir"] == "back"))
    for v in ("B_real", "R1", "R2"):
        video(v, PUSH_CMDS[w], f"torso_push_{v}.mp4", seconds=t0 + 3.0, push=(t0, j, PUSH_DIRS["back"]), azim=90.0)
    video("R1_half_slosh_nobaffle", COMMANDS["vx 0.2 + yaw 0.5"], "torso_slosh_R1.mp4", dist=0.9, azim=150.0, elev=-30.0,
          xray=True, look_dz=0.30)
    print("push impulse in the videos:", j, "N s at", t0, "s")


def self_check():
    w, m1 = slosh_params(1.0, 1e-4, 1.0)  # shallow limit: m1 -> 8/pi^2 of the water, w -> pi sqrt(g h) / L
    assert abs(m1 - 8 / math.pi ** 2) < 1e-3 and abs(w - math.pi * math.sqrt(G * 1e-4)) < 1e-4
    w, m1 = slosh_params(0.1, 1.0, 1.0)  # deep limit: w^2 -> pi g / L, small share
    assert abs(w * w - math.pi * G / 0.1) < 1e-6 and m1 < 0.1
    q, v = jet(2.0)
    a = math.pi * 0.002 ** 2 / 4
    assert 0 < q < 1.15 and abs(v - q / 60000 / a) < 1e-9
    p_left = PUMP_PMAX * (1 - q / 60000 / PUMP_Q0)
    assert 500 * (v / NOZZLE_CV) ** 2 < p_left  # nozzle pressure below the pump pressure (lift and tube losses)
    write_slosh_models()
    m = mujoco.MjModel.from_xml_path(str(models.path("R1_half_slosh_nobaffle")))
    assert [m.joint(f"leg_left_hip_roll_joint").qposadr[0], m.nq] == [7, 19 + 2]  # slosh joints after the legs
    assert abs(m.body_subtreemass[1] - models.load("R1_half").body_subtreemass[1]) < 1e-6  # same total mass
    assert policy_run("R1", (0.0, 0.0, 0.0), seconds=3.0) is None
    print("self-check torso_tank: slosh limits, jet operating point, slosh model layout, R1 stands 3 s")


if __name__ == "__main__":
    {"check": self_check, "video": videos, "report": redo_report}.get(sys.argv[1] if len(sys.argv) > 1 else "", main)()
