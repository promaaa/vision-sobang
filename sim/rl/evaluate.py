"""Evaluate a trained policy: velocity tracking and falls for several payloads, plus a video.

Usage: python evaluate.py <run_dir> [push]
Without "push": writes <run_dir>/eval.json, reward_curve.png and walk_payload1.5kg.mp4.
With "push": 15 s runs with the training pushes (a sudden 0.1-1.0 m/s change of the torso
horizontal velocity, every 5-10 s, random direction); writes <run_dir>/eval_push.json only.
"""

import json
import os
import pickle
import sys

os.environ.setdefault("MUJOCO_GL", "egl")

import jax
import jax.numpy as jp
import matplotlib
import mediapy
import mujoco
from mujoco import mjx
import numpy as np
from brax.training.acme import running_statistics
from brax.training.agents.ppo import networks as ppo_networks

import bhl_env

run_dir = sys.argv[1]
PUSH = sys.argv[2:] == ["push"]
N_ENVS, SECONDS, SKIP_S = 64, 15.0 if PUSH else 10.0, 2.0  # measure tracking after a 2 s settle period
TESTS = {"stand": [0.0, 0.0, 0.0], "forward_0.3": [0.3, 0.0, 0.0], "turn_0.5": [0.0, 0.0, 0.5]}

cfg = bhl_env.default_config()
cfg.push_config.enable = PUSH  # noise stays on (as on the real robot)
cfg_path = os.path.join(run_dir, "config.json")
cfg.update(json.load(open(cfg_path)))
env = bhl_env.BHLJoystick(cfg)
pay = env.mj_model.body("payload").id
pay_m0, pay_I0 = env.mj_model.body_mass[pay], env.mj_model.body_inertia[pay].copy()
pay_p0 = env.mj_model.body_ipos[pay].copy()
# name: (mass kg, CoM shift from the default payload point 0.84 m above the base origin).
# "A" = concept A from sim/payload/models/bhl_A.xml: 1.44 kg, CoM 9.6 cm higher (outside the training range).
PAYLOADS = {"0kg": (0.0, (0, 0, 0)), "3.5kg": (3.5, (0, 0, 0)), "A_1.44kg_high": (1.44, (0.015, 0.003, 0.096)),
            "1.5kg": (1.5, (0, 0, 0))}  # 1.5 kg last: the video reuses its compiled step
if PUSH:
  del PAYLOADS["A_1.44kg_high"]

with open(os.path.join(run_dir, "params_latest.pkl"), "rb") as f:
  params = pickle.load(f)
net = ppo_networks.make_ppo_networks(
    env.observation_size, env.action_size, preprocess_observations_fn=running_statistics.normalize,
    policy_hidden_layer_sizes=(512, 256, 128), value_hidden_layer_sizes=(512, 256, 128),
    policy_obs_key="state", value_obs_key="privileged_state")
policy = jax.jit(ppo_networks.make_inference_fn(net)(params, deterministic=True))


def set_payload(mass, shift=(0, 0, 0)):
  env.mj_model.body_mass[pay] = mass
  env.mj_model.body_ipos[pay] = pay_p0 + np.array(shift)
  env.mj_model.body_inertia[pay] = pay_I0 * max(mass, 1e-3) / pay_m0
  env.update_mjx_model()
  global reset_fn, step_fn, forward_fn  # the model is a jit constant: compile once per payload
  reset_fn, step_fn = jax.jit(jax.vmap(env.reset)), jax.jit(jax.vmap(env.step))
  forward_fn = jax.jit(jax.vmap(lambda d: mjx.forward(env.mjx_model, d)))


def rollout(cmd, n_steps, n_envs, seed=0):
  """Returns per-step qpos [T, n, nq], local vel [T, n, 3], gyro [T, n, 3], done [T, n]."""
  state = reset_fn(jax.random.split(jax.random.PRNGKey(seed), n_envs))
  # Start from the clean default stand (reset() also randomises joint angles and base velocity).
  data = state.data.replace(qpos=jp.tile(env._init_q, (n_envs, 1)), qvel=jp.zeros_like(state.data.qvel),
                            ctrl=jp.tile(env._default_pose, (n_envs, 1)))
  state = state.replace(data=forward_fn(data))
  state.info["command"] = jp.tile(jp.array(cmd), (n_envs, 1))
  keys = jax.random.split(jax.random.PRNGKey(seed + 1), n_steps)
  out = []
  for t in range(n_steps):
    act, _ = jax.vmap(policy)(state.obs, jax.random.split(keys[t], n_envs))
    state = step_fn(state, act)
    state.info["command"] = jp.tile(jp.array(cmd), (n_envs, 1))
    out.append((state.data.qpos, jax.vmap(env.get_local_linvel)(state.data),
                jax.vmap(env.get_gyro)(state.data), state.done))
  return [np.array(x) for x in zip(*out)]


results = {}
n_steps, skip = int(SECONDS / env.dt), int(SKIP_S / env.dt)
for pname, (mass, shift) in PAYLOADS.items():
  set_payload(mass, shift)
  for name, cmd in TESTS.items():
    qpos, vel, gyro, done = rollout(cmd, n_steps, N_ENVS)
    fell = np.maximum.accumulate(done > 0, axis=0)  # once fallen, stays fallen
    ok = ~fell[skip:]
    err_v = np.linalg.norm(vel[skip:, :, :2] - np.array(cmd[:2]), axis=-1)
    err_w = np.abs(gyro[skip:, :, 2] - cmd[2])
    results[f"{pname}/{name}"] = {
        "fall_rate": float(fell[-1].mean()),
        "lin_vel_err_mps": float(err_v[ok].mean()) if ok.any() else None,
        "yaw_rate_err_radps": float(err_w[ok].mean()) if ok.any() else None,
        "mean_vx_mps": float(vel[skip:, :, 0][ok].mean()) if ok.any() else None,
        "mean_yaw_rate_radps": float(gyro[skip:, :, 2][ok].mean()) if ok.any() else None,
    }
    print(f"{pname:14s} {name:12s}", results[f"{pname}/{name}"], flush=True)
json.dump(results, open(os.path.join(run_dir, "eval_push.json" if PUSH else "eval.json"), "w"), indent=1)
if PUSH:
  sys.exit()

# Reward curve.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # pylint: disable=g-import-not-at-top
rows = [json.loads(l) for l in open(os.path.join(run_dir, "progress.jsonl"))]
plt.figure(figsize=(6, 3.5))
plt.plot([r["step"] / 1e6 for r in rows], [r["eval/episode_reward"] for r in rows], "o-")
plt.xlabel("environment steps (millions)")
plt.ylabel("eval episode reward")
plt.title("BHL biped + payload, PPO")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(run_dir, "reward_curve.png"), dpi=120)

# Video: 1.5 kg payload, 5 s stand, 5 s forward 0.3 m/s, 5 s turn 0.5 rad/s.
frames_q = []
for cmd in TESTS.values():
  qpos = rollout(cmd, int(5.0 / env.dt), N_ENVS, seed=7)[0][:, 0]
  frames_q.append(qpos)
mj_model = env.mj_model
d = mujoco.MjData(mj_model)
renderer = mujoco.Renderer(mj_model, 480, 640)
cam = mujoco.MjvCamera()
cam.type, cam.trackbodyid, cam.distance, cam.elevation, cam.azimuth = mujoco.mjtCamera.mjCAMERA_TRACKING, 1, 2.0, -15, 120
frames = []
offset = np.zeros(3)
for seg in frames_q:  # segments restart at reset: chain them visually by shifting xy
  for q in seg:
    d.qpos[:] = q
    d.qpos[:2] += offset[:2]
    mujoco.mj_forward(mj_model, d)
    renderer.update_scene(d, cam)
    frames.append(renderer.render())
  offset[:2] += seg[-1][:2] - seg[0][:2]
mediapy.write_video(os.path.join(run_dir, "walk_payload1.5kg.mp4"), frames, fps=int(1 / env.dt))
print("wrote", os.path.join(run_dir, "walk_payload1.5kg.mp4"))
