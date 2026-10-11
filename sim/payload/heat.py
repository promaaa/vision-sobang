"""Round 4: joint torques of the shipped BHL walking policy over 60 s of walking, for the motor heat question.

    sim/sim2sim/.venv/bin/python sim/payload/heat.py    # writes results/heat.md, results/heat.json, results/heat_<run>.npz

The control loop copies sim/sim2sim/run.py (read-only import of its constants and observation function):
25 Hz policy, 2000 Hz physics, PD kp 20 / kd 2, torque clipped at the limit. 2 s of standing, then 60 s of walking
at 0.25 m/s with left and right turns. Statistics use the 60 s of walking only.
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sim2sim"))
import run as s2s  # noqa: E402  (sim/sim2sim/run.py, not modified)

OUT = HERE / "results"
STAND_S, WALK_S = 2.0, 60.0
# (start time s, vx m/s, yaw rate rad/s) during the walk; aim/ uses 0.25 m/s and up to 0.6 rad/s.
# "plain": 0.25 m/s from the start. The policy often keeps standing in place with this command.
# "kick": 0.3 m/s for the first 3 s, which starts the gait (sim/sim2sim found that 0.3 m/s walks), then as "plain".
PLAIN = [(0, 0.25, 0.0), (10, 0.25, 0.5), (20, 0.25, 0.0), (30, 0.25, -0.5), (40, 0.25, 0.0), (50, 0.25, 0.5)]
SCHEDULES = {"plain": PLAIN, "kick": [(0, 0.3, 0.0), (3, 0.25, 0.0)] + PLAIN[1:]}
RUNS = [("bhl_A_real", 6.0, "kick"), ("bhl_B_real", 6.0, "kick"), ("bhl_A_real", 6.0, "plain"),
        ("bhl_B_real", 6.0, "plain"), ("bhl_A_real", 4.0, "kick"), ("bhl_B_real", 4.0, "kick")]
DECIMATE = 10  # saved log at 200 Hz; statistics use every 2000 Hz physics step


def command(t, schedule):
    if t < STAND_S:
        return np.zeros(3, dtype=np.float32)
    vx, wz = next((v, w) for t0, v, w in reversed(SCHEDULES[schedule]) if t - STAND_S >= t0)
    return np.array([vx, 0.0, wz], dtype=np.float32)


def walk(job):
    model, limit, schedule = job
    m = mujoco.MjModel.from_xml_path(str(s2s.MODELS / f"{model}.xml"))
    m.opt.timestep = s2s.PHYSICS_DT
    d = mujoco.MjData(m)
    d.qpos[7:19] = s2s.DEFAULT  # BHL reset, as run.py start="bhl"
    mujoco.mj_forward(m, d)
    assert [m.actuator(i).name for i in range(m.nu)] == s2s.JOINTS
    policy = ort.InferenceSession(str(s2s.POLICY), providers=["CPUExecutionProvider"])
    action = np.zeros(12, dtype=np.float32)
    sub = round(s2s.POLICY_DT / s2s.PHYSICS_DT)
    z0, base = d.site("imu").xpos[2], m.body("base").id
    taus, fall, x_prev, path = [], None, None, 0.0
    for _ in range(round((STAND_S + WALK_S) / s2s.POLICY_DT)):
        cmd = command(d.time, schedule)
        obs = s2s.observation(cmd, d.sensor("imu_quat").data.copy(), d.sensor("imu_gyro").data.copy(),
                              d.qpos[7:19], d.qvel[6:18], action)
        action = policy.run(None, {"obs": obs})[0][0]
        target = s2s.DEFAULT + s2s.ACTION_SCALE * action
        for _ in range(sub):
            tau = np.clip(s2s.KP * (target - d.qpos[7:19]) - s2s.KD * d.qvel[6:18], -limit, limit)
            d.ctrl[:] = tau
            mujoco.mj_step(m, d)
            if d.time > STAND_S:
                taus.append(tau.astype(np.float32))
        if d.time >= STAND_S:  # path length of the base in the floor plane during the walk
            if x_prev is not None:
                path += float(np.linalg.norm((d.xpos[base] - x_prev)[:2]))
            x_prev = d.xpos[base].copy()
        tilt = np.arccos(np.clip(-s2s.quat_rotate_inverse(d.sensor("imu_quat").data, np.array([0, 0, -1.0]))[2], -1, 1))
        if tilt > s2s.TILT_LIMIT or d.site("imu").xpos[2] < 0.6 * z0:
            fall = float(d.time)
            break
    tau = np.array(taus).reshape(-1, 12)
    name = f"{model}_{limit:g}Nm_{schedule}"
    if len(tau) == 0:  # fell while standing, before the walk
        return {"run": name, "model": model, "limit": limit, "schedule": schedule, "fall": fall, "walked_m": 0.0,
                "seconds": 0.0}
    np.savez_compressed(OUT / f"heat_{name}.npz", tau=tau[::DECIMATE], dt=s2s.PHYSICS_DT * DECIMATE, joints=s2s.JOINTS)
    return {"run": name, "model": model, "limit": limit, "schedule": schedule, "fall": fall,
            "walked_m": path,
            "seconds": len(tau) * s2s.PHYSICS_DT,
            "rms": np.sqrt((tau.astype(np.float64) ** 2).mean(0)).tolist(),
            "peak": np.abs(tau).max(0).tolist(),
            "above4": (100.0 * (np.abs(tau) > 4.0).mean(0)).tolist(),
            "at_limit": (100.0 * (np.abs(tau) >= limit - 1e-6).mean(0)).tolist()}


def self_check():
    assert command(0.0, "kick")[0] == 0 and command(STAND_S + 1, "kick")[0] == np.float32(0.3)
    assert command(STAND_S + 15, "plain")[2] == 0.5 and command(STAND_S + 35, "kick")[2] == -0.5
    t = np.array([[3.0, -4.0], [-3.0, 4.0]])
    assert np.allclose(np.sqrt((t ** 2).mean(0)), [3, 4])  # RMS of a +-a signal is a
    print("self-check heat: command schedule, RMS")


# ---------- report ----------
GEAR = 15.0  # BHL robot_configuration.backup.json "gear_ratio": -15.0
# motor torque constant (Nm/A, motor side) per joint, BHL Lowlevel robot_configuration.backup.json "torque_constant"
KT = {"hip_roll": 0.0919, "hip_yaw": 0.0919, "hip_pitch": 0.0919, "knee_pitch": 0.0919,
      "ankle_pitch": 0.1176, "ankle_roll": 0.1176}
# line-to-line winding resistance (ohm), measured by BHL: M6C12 0.1257, 5010 0.4129
# (https://berkeley-humanoid-lite.gitbook.io/docs/in-depth-contents/motor-characterization.md)
R_LL = {k: 0.1257 if KT[k] < 0.1 else 0.4129 for k in KT}
ETA = 0.9  # gearbox efficiency, "approximately 90%" (BHL paper, https://arxiv.org/html/2504.17249)
# copper loss = c * R_LL * Iq^2 with c = 0.5 (power-invariant dq) to 0.75 (amplitude-invariant dq); the firmware
# convention is not known, so the report gives both ends


def report():
    res = [r for r in json.load(open(OUT / "heat.json")) if r["seconds"]]
    L = []
    for r in res:
        L += [f"#### {r['run']}: {r['seconds']:.0f} s, path {r['walked_m']:.1f} m, "
              + ("no fall" if r["fall"] is None else f"falls at {r['fall']:.1f} s"), "",
              "| Joint | RMS torque (Nm) | Peak (Nm) | Time above 4 Nm (%) | Time at the limit (%) "
              "| RMS motor current (A, estimate) | Copper loss (W, estimate) |", "|---|---|---|---|---|---|---|"]
        for j, name in enumerate(s2s.JOINTS):
            k = name.split("_", 2)[2].replace("_joint", "")
            i_rms = r["rms"][j] / (GEAR * KT[k] * ETA)
            loss = f"{0.5 * R_LL[k] * i_rms ** 2:.1f} to {0.75 * R_LL[k] * i_rms ** 2:.1f}"
            L.append(f"| {name.replace('leg_', '').replace('_joint', '')} | {r['rms'][j]:.2f} | {r['peak'][j]:.2f} "
                     f"| {r['above4'][j]:.1f} | {r['at_limit'][j]:.1f} | {i_rms:.1f} | {loss} |")
        L.append("")
    six = [r for r in res if r["limit"] == 6.0]
    L += ["#### Summary at 6 Nm: worse of the left and right joint", "",
          "| Joint (actuator) | " + " | ".join(f"RMS {r['run'].replace('bhl_', '').replace('_6Nm', '')} (Nm)" for r in six)
          + " | " + " | ".join(f"Above 4 Nm {r['run'].replace('bhl_', '').replace('_6Nm', '')} (%)" for r in six)
          + " | Highest RMS motor current (A, estimate) | Copper loss at that current, upper end (W, estimate) |",
          "|---" * (2 * len(six) + 3) + "|"]
    for k in KT:
        js = [i for i, n in enumerate(s2s.JOINTS) if k in n]
        rms = [max(r["rms"][i] for i in js) for r in six]
        L.append(f"| {k} ({'6512' if KT[k] < 0.1 else '5010'}) | " + " | ".join(f"{v:.2f}" for v in rms) + " | "
                 + " | ".join(f"{max(r['above4'][i] for i in js):.0f}" for r in six)
                 + f" | {max(rms) / (GEAR * KT[k] * ETA):.1f} | {0.75 * R_LL[k] * (max(rms) / (GEAR * KT[k] * ETA)) ** 2:.1f} |")
    L.append("")
    fell = [r for r in json.load(open(OUT / "heat.json")) if r["fall"] is not None]
    L += ["Runs that fall: " + ", ".join(f"{r['run']} at {r['fall']:.1f} s" for r in fell), ""]
    (OUT / "heat.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    if sys.argv[1:] == ["report"]:
        report()
        sys.exit()
    self_check()
    OUT.mkdir(exist_ok=True)
    with Pool(len(RUNS)) as p:
        res = p.map(walk, RUNS)
    json.dump(res, open(OUT / "heat.json", "w"), indent=1)
    for r in res:
        print(r["run"], "fall", r["fall"], "walked", round(r["walked_m"], 1), "m")
        for j, name in enumerate(s2s.JOINTS if r["seconds"] else []):
            print(f"   {name:28s} rms {r['rms'][j]:5.2f}  peak {r['peak'][j]:5.2f}  >4Nm {r['above4'][j]:5.1f} %"
                  f"  at limit {r['at_limit'][j]:5.1f} %")

    report()
