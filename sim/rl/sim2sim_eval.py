"""Compare our ONNX policy with the official BHL policy in the sim/sim2sim harness (CPU MuJoCo, 2000 Hz, PD clipped at 6 Nm).

Usage: python sim2sim_eval.py <run_dir>    -> <run_dir>/sim2sim.md, turn_on_spot_A_real.mp4, walk_0.25_A_real.mp4
The command tests call sim/sim2sim/run.py simulate() unchanged (BHL start drop, training noise, 20 s).
The push test is a copy of that loop that adds the training pushes: every 5-10 s, a sudden 0.1-1.0 m/s
change of the torso horizontal velocity in a random direction. 10 seeds for each case.
"""

import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")  # before mujoco is imported, for the video

import mujoco  # pylint: disable=g-import-not-at-top
import numpy as np
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim2sim"))
import run  # sim/sim2sim/run.py, read-only  # pylint: disable=g-import-not-at-top

run_dir = Path(sys.argv[1]).resolve()
POLICIES = {"official": str(run.POLICY), "ours": str(run_dir / "policy.onnx")}
MODELS = ["bhl_A_real", "bhl_B_real"]
CMDS = {"stand": (0.0, 0.0, 0.0), "vx 0.1": (0.1, 0.0, 0.0), "vx 0.25": (0.25, 0.0, 0.0),
        "turn on the spot 0.5": (0.0, 0.0, 0.5), "vx 0.25 + yaw 0.5": (0.25, 0.0, 0.5)}
PUSH_CMDS = ["stand", "vx 0.25", "turn on the spot 0.5"]
LIMIT, SEEDS = 6.0, 10


def harness(policy, model, cmd):
  run.POLICY = Path(POLICIES[policy])
  return run.simulate(model, CMDS[cmd], LIMIT, 20.0, None, "bhl", True)


def push_run(policy, model, cmd, seed, seconds=20.0):
  """run.simulate() with noise and pushes. Returns the fall time or None."""
  rng = np.random.default_rng(seed)
  m = mujoco.MjModel.from_xml_path(str(run.MODELS / f"{model}.xml"))
  m.opt.timestep = run.PHYSICS_DT
  d = mujoco.MjData(m)
  d.qpos[7:19] = run.DEFAULT
  mujoco.mj_forward(m, d)
  sess = ort.InferenceSession(POLICIES[policy], providers=["CPUExecutionProvider"])
  c = np.array(CMDS[cmd], dtype=np.float32)
  action = np.zeros(12, dtype=np.float32)
  substeps = round(run.POLICY_DT / run.PHYSICS_DT)
  z0 = d.site("imu").xpos[2]
  next_push = rng.uniform(5, 10)
  for _ in range(round(seconds / run.POLICY_DT)):
    if d.time >= next_push:
      th, mag = rng.uniform(0, 2 * np.pi), rng.uniform(0.1, 1.0)
      d.qvel[0:2] += mag * np.array([np.cos(th), np.sin(th)])
      next_push += rng.uniform(5, 10)
    obs = run.observation(c, d.sensor("imu_quat").data.copy(), d.sensor("imu_gyro").data.copy(),
                          d.qpos[7:19], d.qvel[6:18], action)
    obs += (rng.uniform(-1, 1, 45) * run.NOISE).astype(np.float32)
    action = sess.run(None, {"obs": obs})[0][0]
    target = run.DEFAULT + run.ACTION_SCALE * action
    for _ in range(substeps):
      d.ctrl[:] = np.clip(run.KP * (target - d.qpos[7:19]) - run.KD * d.qvel[6:18], -LIMIT, LIMIT)
      mujoco.mj_step(m, d)
    g = run.quat_rotate_inverse(d.sensor("imu_quat").data, np.array([0, 0, -1.0]))
    if np.arccos(np.clip(-g[2], -1, 1)) > run.TILT_LIMIT or d.site("imu").xpos[2] < 0.6 * z0:
      return d.time
  return None


def fmt(r):
  if r["fall"] is not None:
    return f"falls at {r['fall']:.1f} s", "-"
  return "no fall", f"{r['vx']:+.2f} / {r['wz']:+.2f}"


if __name__ == "__main__":
  jobs = [(p, mo, c) for mo in MODELS for c in CMDS for p in POLICIES]
  pjobs = [(p, mo, c, s) for mo in MODELS for c in PUSH_CMDS for p in POLICIES for s in range(SEEDS)]
  with Pool(4) as pool:  # CPU only; leave cores for the other agents
    res = dict(zip(jobs, pool.starmap(harness, jobs)))
    pres = dict(zip(pjobs, pool.starmap(push_run, pjobs)))
  lines = ["| Model | Test | Official: result | Official: vx / yaw rate | Ours: result | Ours: vx / yaw rate |",
           "|---|---|---|---|---|---|"]
  for mo in MODELS:
    for c in CMDS:
      lines.append(f"| {mo} | {c} | " + " | ".join(" | ".join(fmt(res[(p, mo, c)])) for p in POLICIES) + " |")
    for c in PUSH_CMDS:
      cells = []
      for p in POLICIES:
        n = sum(pres[(p, mo, c, s)] is not None for s in range(SEEDS))
        cells.append(f"falls in {n} of {SEEDS} runs | -")
      lines.append(f"| {mo} | push test, {c} | " + " | ".join(cells) + " |")
  text = "\n".join(lines) + "\n"
  (run_dir / "sim2sim.md").write_text(text)
  print(text)
  if "--no-video" not in sys.argv:
    run.POLICY = Path(POLICIES["ours"])
    run.video("bhl_A_real", "yaw 0.5", LIMIT, str(run_dir / "turn_on_spot_A_real.mp4"), noise=True)
    run.COMMANDS["vx 0.25"] = CMDS["vx 0.25"]
    run.video("bhl_A_real", "vx 0.25", LIMIT, str(run_dir / "walk_0.25_A_real.mp4"), noise=True)
