"""Train a BHL biped walking policy with payload, using Brax PPO (Playground setup).

Usage: python train.py <num_timesteps> <num_evals> <run_dir> [effort_limit_Nm=6] [action_scale=0.5] [payload_max_kg=2.5] [com_shift_m=0.03] [knee_limit_rad=0 (MJCF)]
Saves <run_dir>/params_<step>.pkl at every eval, params_latest.pkl, and progress.jsonl.
"""

import functools
import json
import os
import pickle
import sys
import time

from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo
from mujoco_playground import wrapper

import bhl_env
import bhl_official

OFFICIAL = "--official" in sys.argv  # official BHL policy interface (bhl_official.py)
if OFFICIAL:
  sys.argv.remove("--official")
INIT_STD = 1.0  # initial action noise std; "--init_std=2" explores +-0.5 rad with action scale 0.25
for arg in [a for a in sys.argv if a.startswith("--init_std=")]:
  INIT_STD = float(arg.split("=")[1])
  sys.argv.remove(arg)
NO_PUSH = "--no_push" in sys.argv  # curriculum stage 1: no pushes
if NO_PUSH:
  sys.argv.remove("--no_push")
RESTORE = None  # "--restore=<run>/params_latest.pkl": start from saved weights (curriculum next stage)
for arg in [a for a in sys.argv if a.startswith("--restore=")]:
  with open(arg.split("=", 1)[1], "rb") as f:
    RESTORE = pickle.load(f)
  sys.argv.remove(arg)
SCALES = {}  # "--scale=feet_air_time:0" overrides one reward weight
for arg in [a for a in sys.argv if a.startswith("--scale=")]:
  name, value = arg.split("=", 1)[1].split(":")
  SCALES[name] = float(value)
  sys.argv.remove(arg)
SINGLE_STANCE = 0.0  # weight of the dense stepping reward of bhl_official.py ("--single_stance=1")
for arg in [a for a in sys.argv if a.startswith("--single_stance=")]:
  SINGLE_STANCE = float(arg.split("=")[1])
  sys.argv.remove(arg)
num_timesteps, num_evals, run_dir = int(float(sys.argv[1])), int(sys.argv[2]), sys.argv[3]
os.makedirs(run_dir, exist_ok=True)
cfg = bhl_official.default_config() if OFFICIAL else bhl_env.default_config()
overrides = {"official": OFFICIAL, "init_std": INIT_STD, "single_stance": SINGLE_STANCE} if OFFICIAL else {}
overrides.update({"effort_limit": float(sys.argv[4]) if len(sys.argv) > 4 else 6.0,
             "action_scale": float(sys.argv[5]) if len(sys.argv) > 5 else 0.5,
             "payload_max": float(sys.argv[6]) if len(sys.argv) > 6 else 2.5,
             "payload_com_shift": float(sys.argv[7]) if len(sys.argv) > 7 else 0.03,
             "knee_limit": float(sys.argv[8]) if len(sys.argv) > 8 else 0.0})
if OFFICIAL:
  overrides["action_scale"] = bhl_official.ACTION_SCALE  # fixed by the BHL interface
cfg.update({k: v for k, v in overrides.items() if k not in ("official", "init_std", "single_stance")})
if OFFICIAL:
  cfg.reward_config.scales.single_stance = SINGLE_STANCE
cfg.reward_config.scales.update(SCALES)
overrides["scales"] = SCALES
cfg.push_config.enable = not NO_PUSH
overrides["push"] = not NO_PUSH
json.dump(overrides, open(os.path.join(run_dir, "config.json"), "w"))

env = bhl_official.BHLOfficial(cfg) if OFFICIAL else bhl_env.BHLJoystick(cfg)
# PPO settings from Playground's BerkeleyHumanoidJoystickFlatTerrain config.
ppo_params = dict(
    num_timesteps=num_timesteps, num_evals=num_evals, reward_scaling=1.0,
    episode_length=env._config.episode_length, normalize_observations=True,
    action_repeat=1, unroll_length=20, num_minibatches=32, num_updates_per_batch=4,
    discounting=0.98 if OFFICIAL else 0.97,  # at 25 Hz, 0.97 looks only about 1.3 s ahead
    learning_rate=3e-4, entropy_cost=0.005, num_envs=8192,
    batch_size=256, max_grad_norm=1.0, clipping_epsilon=0.2, num_resets_per_eval=1,
)
network_factory = functools.partial(
    ppo_networks.make_ppo_networks,
    policy_hidden_layer_sizes=(512, 256, 128), value_hidden_layer_sizes=(512, 256, 128),
    policy_obs_key="state", value_obs_key="privileged_state",
    # Official interface: unbounded Gaussian actions (as RSL-RL). Brax's default tanh limits actions to +-1.
    distribution_type="normal" if OFFICIAL else "tanh_normal",
    init_noise_std=INIT_STD,
)
t0 = time.time()
log = open(os.path.join(run_dir, "progress.jsonl"), "a")


def progress(step, metrics):
  row = {"step": int(step), "time_s": round(time.time() - t0, 1)}
  row.update({k: float(v) for k, v in metrics.items() if k.startswith("eval/episode_") and not k.endswith("_std")})
  log.write(json.dumps(row) + "\n")
  log.flush()
  print(f"step {step:>11,}  t {row['time_s']:7.1f}s  reward {row.get('eval/episode_reward', 0):8.3f}", flush=True)


def save_params(step, make_policy, params):
  del make_policy
  for name in (f"params_{int(step)}.pkl", "params_latest.pkl"):
    with open(os.path.join(run_dir, name), "wb") as f:
      pickle.dump(params, f)


ppo.train(
    environment=env,
    wrap_env_fn=wrapper.wrap_for_brax_training,
    randomization_fn=functools.partial(bhl_env.domain_randomize, mj_model=env.mj_model,
                                       payload_max=cfg.payload_max, com_shift=cfg.payload_com_shift),
    network_factory=network_factory,
    progress_fn=progress,
    policy_params_fn=save_params,
    restore_params=RESTORE,
    **ppo_params,
)
print(f"done in {time.time() - t0:.0f} s")
