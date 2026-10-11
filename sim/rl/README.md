# Walking policy for the BHL biped with a torso payload (simulation)

This folder trains a walking policy for the Berkeley Humanoid Lite (BHL) biped legs.
The robot carries an extra mass on the torso, like the water tank, pump and cameras.
Training uses reinforcement learning (RL) on the GPU with MuJoCo MJX and Brax PPO.
PPO (Proximal Policy Optimization) is the standard RL algorithm for legged robots.

Status: **built** and **tested in simulation** only. Nothing here is measured on a laptop or on the robot.

## Results

All numbers come from simulation. I trained four policies with PPO on the RTX 3090:

| Run folder | Action scale | Torque limit | Steps | Training time | Result |
|---|---|---|---|---|---|
| `runs/a025_nm6` | 0.25 | 6 Nm | 91 M | 14 min | Stands. Does not walk or turn. |
| `runs/a025_nm20_stopped` | 0.25 | 20 Nm | 20 M | 4 min | I stopped it. Up to 20 M steps, its reward curve was the same as the 6 Nm run. |
| `runs/a05_nm6` | 0.5 | 6 Nm | 121 M | 37 min | Walks and turns, but falls often when pushed. |
| `runs/a05_nm20` | 0.5 | 20 Nm | 121 M | 37 min | Walks and turns, best tracking, falls less when pushed. |

The two 121 M runs ran at the same time on the GPU, so each took 37 min.
The 6 Nm limit is the official BHL value. The 20 Nm limit is the `forcerange` in the BHL MJCF.
Nobody has checked 20 Nm on the real motors.

The reward curves of all runs are in `runs/reward_curves.png`.

### Evaluation without pushes (`evaluate.py`)

Each cell gives the mean measured value and, in brackets, the mean error.
Fall rate is 0 % for all 24 cases: no robot (of 64) fell in 10 s.

| Payload | Run | Forward 0.3 m/s: speed (error) | Turn 0.5 rad/s: turn rate (error) | Stand: speed error |
|---|---|---|---|---|
| 0 kg | 6 Nm | 0.30 m/s (0.08) | 0.38 rad/s (0.25) | 0.08 m/s |
| 0 kg | 20 Nm | 0.29 m/s (0.07) | 0.48 rad/s (0.14) | 0.06 m/s |
| 1.5 kg | 6 Nm | 0.30 m/s (0.06) | 0.39 rad/s (0.24) | 0.05 m/s |
| 1.5 kg | 20 Nm | 0.29 m/s (0.05) | 0.48 rad/s (0.13) | 0.05 m/s |
| 2.5 kg | 6 Nm | 0.30 m/s (0.05) | 0.39 rad/s (0.23) | 0.05 m/s |
| 2.5 kg | 20 Nm | 0.29 m/s (0.04) | 0.49 rad/s (0.13) | 0.05 m/s |
| Concept A, 1.44 kg, 9.6 cm higher | 6 Nm | 0.31 m/s (0.05) | 0.40 rad/s (0.24) | 0.05 m/s |
| Concept A, 1.44 kg, 9.6 cm higher | 20 Nm | 0.30 m/s (0.04) | 0.47 rad/s (0.14) | 0.05 m/s |

The speed error is the norm of the forward and side velocity error.
When it walks forward, the 6 Nm policy also turns slowly: 0.05 to 0.07 rad/s.
The 20 Nm policy turns less than 0.02 rad/s when it walks forward.
The full numbers are in `runs/<run>/eval_2.5kg.json`.

### Evaluation with pushes and randomisation (Brax evaluation during training)

Brax evaluates 128 robots for 20 s with pushes and all domain randomisation on.
At the end of training, 79 % of these episodes ended in a fall with 6 Nm.
With 20 Nm, 17 % ended in a fall.
So the 6 Nm limit mostly costs robustness to pushes, not walking on flat ground.

### Videos

`runs/a05_nm6/walk_payload1.5kg.mp4` and `runs/a05_nm20/walk_payload1.5kg.mp4` show a 1.5 kg payload.
Each video has 5 s of standing, 5 s of walking at 0.3 m/s and 5 s of turning at 0.5 rad/s.

## Round 2: backpack range (6 Nm, 0 to 3.5 kg, knee limit 1.4 rad)

The B backpack is 2.3 kg plus the head. Its legs clear the backpack only with knee ≤ 1.4 rad (`cad/backpack/README.md`).
So I trained `runs/a05_nm6_p35_knee14`: 6 Nm, action scale 0.5, payload 0 to 3.5 kg, centre of mass shift ±5 cm, knee ≤ 1.4 rad.
It ran alone on the GPU: 132 M steps in 16 min.

I evaluated all three action-scale-0.5 policies with and without pushes (64 robots for each case).
"Falls, no push" is the worst of stand, forward and turn (10 s).
"Falls, push" is the mean of stand, forward and turn (15 s, one or two pushes).
Speeds are without pushes, except the last column.

| Policy | Payload | Falls, no push | Falls, push | Forward 0.3: speed | Turn 0.5: rate | Forward 0.3 with push: speed |
|---|---|---|---|---|---|---|
| 6 Nm, 0–2.5 kg | 0 kg | 0 % | 29 % | 0.30 m/s | 0.38 rad/s | 0.30 m/s |
| 6 Nm, 0–2.5 kg | 1.5 kg | 0 % | 42 % | 0.30 m/s | 0.39 rad/s | 0.30 m/s |
| 6 Nm, 0–2.5 kg | 3.5 kg | 2 % | 59 % | 0.29 m/s | 0.38 rad/s | 0.29 m/s |
| 20 Nm, 0–2.5 kg | 0 kg | 0 % | 1 % | 0.29 m/s | 0.48 rad/s | 0.29 m/s |
| 20 Nm, 0–2.5 kg | 1.5 kg | 0 % | 3 % | 0.29 m/s | 0.48 rad/s | 0.28 m/s |
| 20 Nm, 0–2.5 kg | 3.5 kg | 0 % | 10 % | 0.29 m/s | 0.49 rad/s | 0.27 m/s |
| 6 Nm, 0–3.5 kg, knee ≤ 1.4 | 0 kg | 0 % | 43 % | 0.30 m/s | 0.27 rad/s | 0.30 m/s |
| 6 Nm, 0–3.5 kg, knee ≤ 1.4 | 1.5 kg | 0 % | 48 % | 0.30 m/s | 0.26 rad/s | 0.30 m/s |
| 6 Nm, 0–3.5 kg, knee ≤ 1.4 | 3.5 kg | 0 % | 61 % | 0.28 m/s | 0.24 rad/s | 0.28 m/s |

For the first two policies, 3.5 kg is outside their training range (0 to 2.5 kg).

What this shows:

- All three policies walk at 0.3 m/s on flat ground without pushes, with 0 to 2 % falls.
- With pushes, the 6 Nm policies fall in 29 % to 61 % of cases. The 20 Nm policy falls in 1 % to 10 %.
- The round 2 policy does not fall less than the first 6 Nm policy, and it turns more slowly.
- The torque limit has the largest effect on falls under pushes. The wider payload range and the knee limit did not reduce falls.
- The next step is to find the real peak torque of the BHL motors and train with that limit.

## Round 3: official BHL policy interface

Goal: a policy that the BHL runtime can run without changes, and that steps for slow walking and turning on the spot.

### Interface

`bhl_official.py` and `export_onnx.py` match the official biped policy (`docs/locomotion/README.md`, section 2.2):

| Item | Official BHL | Round 3 |
|---|---|---|
| Policy input | 45 values: command, gyro, projected gravity, joint position − default, joint velocity, last action | the same, in the same order, without scaling |
| Policy output | 12 actions, joint target = default + 0.25 × action | the same |
| Joint order and default pose | left leg then right leg; hip pitch −0.2, knee 0.4, ankle pitch −0.3 rad | the same |
| Rate and PD | 25 Hz; torque = 20 × error − 2 × velocity, clipped at 6 Nm | the same. The damping is inside the clipped torque, as on the robot |
| ONNX file | input `obs` float32 [1, 45], output `actions` float32 [1, 12], opset 11 | the same (`runs/<run>/policy.onnx`) |
| Observation noise in training | gyro ±0.3, gravity ±0.05, joint position ±0.05, joint velocity ±2.0 | the same |

- Brax PPO normally limits actions to ±1 with a tanh function. Round 3 uses unbounded Gaussian actions, as RSL-RL does. So action scale 0.25 does not limit the joint targets to ±0.25 rad.
- The policy does not see the gait phase or the base velocity any more. Only the critic sees them, and the payload mass.
- `export_onnx.py` folds the observation normaliser into the first layer. The ONNX takes the raw BHL observation.
  It checks the ONNX against the JAX policy: the largest difference is about 2 × 10⁻⁶.

### Training changes

- Payload 0 to 3.5 kg, centre of mass shift ±5 cm, knee ≤ 1.4 rad, 6 Nm, pushes as before (0.1 to 1.0 m/s, every 5 to 10 s).
- Command mix, resampled every 5 s: 10 % stand, 25 % turn on the spot (0.2 to 0.8 rad/s), 30 % slow walk (0.1 to 0.3 m/s, turn up to 0.6 rad/s), 35 % the earlier ranges.
- The tracking rewards add a second, narrow kernel. Standing still on a 0.1 m/s command then earns about 35 % less than walking.
- The feet air time reward counts for every non-zero command, also for turning on the spot. BHL counts it only above 0.1 m/s.
- Discount 0.98 instead of 0.97, because at 25 Hz 0.97 looks only about 1.3 s ahead.
- Run `off_ss` adds a dense stepping reward like the Isaac Lab term that BHL uses: while one foot is in the air, it pays the air time up to 0.4 s.

### Round 3 results (tested in simulation)

**Not done:** the round 3 policy does not walk. Do not use it on the robot. The official BHL policy is still better.

All runs use the official interface, 6 Nm and knee ≤ 1.4 rad. I stopped all runs at 09:43 because of the deadline.

| Run | Difference | Steps | Result in the training environment |
|---|---|---|---|
| `off_std1` | as described above | 127 M | Stands. Does not step. Reward stays near 5 after 60 M steps. |
| `off_std2_stopped` | initial action noise 2 instead of 1 | 63 M | Same reward curve as `off_std1`. |
| `off_ss` | adds the dense stepping reward | 169 M | Stands, with very small steps. Reward near 5 to 6. |
| `off_ss_stage1` | `off_ss` without pushes and with payload ≤ 1.5 kg (curriculum stage 1) | 31 M | Learns faster: reward 10.3 at 20 M steps (`off_ss`: 3.3), falls in 37 % of evaluation episodes without pushes (`off_ss`: 91 % with pushes). |

`sim2sim_eval.py` compares `off_ss` with the official policy (`policy_biped_25hz_a.onnx`).
It uses the `sim/sim2sim` harness unchanged: models `bhl_A_real` and `bhl_B_real`, 6 Nm, training noise, 20 s, BHL start drop.
The vx and yaw rate values are means from 5 s to 20 s. The push test uses 10 seeds for each case.

| Model | Test | Official: result | Official: vx / yaw rate | Ours: result | Ours: vx / yaw rate |
|---|---|---|---|---|---|
| bhl_A_real | stand | no fall | +0.00 / -0.00 | no fall | -0.00 / +0.00 |
| bhl_A_real | vx 0.1 | no fall | +0.00 / -0.00 | no fall | +0.00 / -0.00 |
| bhl_A_real | vx 0.25 | no fall | +0.23 / -0.05 | no fall | +0.02 / -0.00 |
| bhl_A_real | turn on the spot 0.5 | no fall | +0.00 / +0.04 | no fall | +0.00 / +0.03 |
| bhl_A_real | vx 0.25 + yaw 0.5 | no fall | +0.23 / +0.48 | no fall | +0.07 / +0.34 |
| bhl_A_real | push test, stand | falls in 7 of 10 runs | - | falls in 8 of 10 runs | - |
| bhl_A_real | push test, vx 0.25 | falls in 5 of 10 runs | - | falls in 7 of 10 runs | - |
| bhl_A_real | push test, turn on the spot 0.5 | falls in 6 of 10 runs | - | falls in 8 of 10 runs | - |
| bhl_B_real | stand | no fall | +0.00 / -0.00 | no fall | -0.00 / +0.00 |
| bhl_B_real | vx 0.1 | no fall | +0.00 / -0.00 | no fall | -0.00 / -0.00 |
| bhl_B_real | vx 0.25 | no fall | +0.11 / -0.04 | no fall | +0.00 / +0.00 |
| bhl_B_real | turn on the spot 0.5 | no fall | +0.00 / +0.01 | no fall | -0.00 / +0.06 |
| bhl_B_real | vx 0.25 + yaw 0.5 | no fall | +0.14 / +0.46 | no fall | +0.03 / +0.16 |
| bhl_B_real | push test, stand | falls in 10 of 10 runs | - | falls in 9 of 10 runs | - |
| bhl_B_real | push test, vx 0.25 | falls in 7 of 10 runs | - | falls in 9 of 10 runs | - |
| bhl_B_real | push test, turn on the spot 0.5 | falls in 9 of 10 runs | - | falls in 10 of 10 runs | - |

- On flat ground, `off_ss` does not walk: 0.02 m/s on bhl_A_real and 0.00 m/s on bhl_B_real for a 0.25 m/s command. The official policy gives 0.23 and 0.11 m/s.
- Turn on the spot: `off_ss` gives 0.03 and 0.06 rad/s for 0.5 rad/s. The official policy gives 0.04 and 0.01 rad/s. Neither policy turns on the spot.
- With pushes, `off_ss` falls a little more often than the official policy (7 to 10 of 10 runs, against 5 to 10 of 10).
- `off_ss_stage1` does not walk in the harness either. It falls on bhl_B_real, which is heavier than its training range.
- `runs/off_ss/turn_on_spot_A_real.mp4` shows `off_ss` on bhl_A_real with the 0.5 rad/s turn-on-the-spot command. The robot stands and turns very little.

Why training stalled:

- **Assumed:** the action scale 0.25 is not the main cause. `off_std2` explores ±0.5 rad, like the round 1 and 2 runs, and it stalled in the same way.
- **Assumed:** the main causes are the missing gait clock and the pushes from the start. The round 1 and 2 policies had a gait clock in their input and reward. The official interface has no clock.
- `off_ss_stage1` supports the push part: without pushes and with a lighter payload, it learned much faster.

Next steps (planned):

1. Train `off_ss_stage1` (no pushes, payload ≤ 1.5 kg) to about 150 M steps, and check that it walks in the harness.
2. Continue from its weights with pushes and payload 0 to 3.5 kg. Brax PPO can start from saved weights (`restore_params`).
3. If the policy still does not step: train a teacher policy with a gait clock, then copy its behaviour into a 45-input student policy.

### Round 4: curriculum without pushes (tested in simulation)

**Not done:** no policy walks at 0.25 m/s yet, and no policy is robust to pushes. Do not use these policies on the robot.
**Assumed:** a gait clock cannot fit in the official 45-value input. Every value already has a meaning in the BHL runtime. A clock needs a 47-value input and a runtime change, so I kept the official layout.

Curriculum stage 1 has no pushes, payload ≤ 1.5 kg and CoM shift ±3 cm. Each run starts from the weights of the run before it (`--restore`).

| Run | Starts from | Difference | Steps | Result |
|---|---|---|---|---|
| `off_ss_stage1b` | `off_ss_stage1` | none | 63 M | Stands. In the MJX training env, 0.00 m/s on a 0.25 m/s command. |
| `off_ss3_stage1b` | `off_ss_stage1` | stepping reward ×3 | 31 M | I stopped it. At 20 M it did not walk in the harness, as `off_ss_stage1b`. |
| `off_v1` | `off_ss_stage1b` | stepping reward ×3, no air-time term | 115 M | I stopped it at 10:45. It steps in place and turns, but at 73 M it did not walk forward. |
| `off_v2` | `off_ss_stage1b` | as `off_v1`, also no feet slip penalty | 115 M | I stopped it at 10:45. It starts to walk and it turns on the spot (table below). |

I removed the Playground air-time term because it gives a penalty for short steps. That penalty also punished the first small steps of the policy.

`off_v2` against the official policy, in the `sim/sim2sim` harness (6 Nm, training noise, 20 s):

| Model | Test | Official: result | Official: vx / yaw rate | Ours: result | Ours: vx / yaw rate |
|---|---|---|---|---|---|
| bhl_A_real | stand | no fall | +0.00 / -0.00 | no fall | -0.00 / +0.00 |
| bhl_A_real | vx 0.1 | no fall | +0.00 / -0.00 | no fall | +0.03 / -0.00 |
| bhl_A_real | vx 0.25 | no fall | +0.23 / -0.05 | no fall | +0.15 / +0.04 |
| bhl_A_real | turn on the spot 0.5 | no fall | +0.00 / +0.04 | no fall | -0.01 / +0.39 |
| bhl_A_real | vx 0.25 + yaw 0.5 | no fall | +0.23 / +0.48 | no fall | +0.17 / +0.44 |
| bhl_A_real | push test, stand | falls in 7 of 10 runs | - | falls in 9 of 10 runs | - |
| bhl_A_real | push test, vx 0.25 | falls in 5 of 10 runs | - | falls in 8 of 10 runs | - |
| bhl_A_real | push test, turn on the spot 0.5 | falls in 6 of 10 runs | - | falls in 9 of 10 runs | - |
| bhl_B_real | stand | no fall | +0.00 / -0.00 | falls at 1.4 s | - |
| bhl_B_real | vx 0.1 | no fall | +0.00 / -0.00 | no fall | +0.00 / +0.00 |
| bhl_B_real | vx 0.25 | no fall | +0.11 / -0.04 | no fall | +0.02 / -0.01 |
| bhl_B_real | turn on the spot 0.5 | no fall | +0.00 / +0.01 | falls at 1.6 s | - |
| bhl_B_real | vx 0.25 + yaw 0.5 | no fall | +0.14 / +0.46 | no fall | +0.04 / +0.26 |
| bhl_B_real | push test, stand | falls in 10 of 10 runs | - | falls in 10 of 10 runs | - |
| bhl_B_real | push test, vx 0.25 | falls in 7 of 10 runs | - | falls in 10 of 10 runs | - |
| bhl_B_real | push test, turn on the spot 0.5 | falls in 9 of 10 runs | - | falls in 10 of 10 runs | - |

- On bhl_A_real, `off_v2` walks at 0.15 m/s for a 0.25 m/s command. The official policy walks at 0.23 m/s.
- On bhl_A_real, `off_v2` turns on the spot at 0.39 rad/s for 0.5 rad/s. The official policy turns at 0.04 rad/s.
- On bhl_B_real, `off_v2` falls when it stands and when it turns on the spot. B is heavier than its training range (≤ 1.5 kg).
- With pushes, `off_v2` falls more often than the official policy. Stage 1 had no pushes.
- Videos: `runs/off_v2/walk_0.25_A_real.mp4` (0.25 m/s command) and `runs/off_v2/turn_on_spot_A_real.mp4` (0.5 rad/s command).
- `runs/off_v2/policy.onnx` has the official form. Do not deploy it, because it is not robust.

Next steps (planned):

1. Continue `off_v2` without pushes until it tracks 0.25 m/s in the harness.
2. Then continue from its weights with payload 0 to 3.5 kg, then with pushes.

How to run round 3, from `sim/rl/`:

1. Train:

   ```
   XLA_PYTHON_CLIENT_MEM_FRACTION=0.5 uv run python train.py 300e6 30 runs/off_v2 6 0.25 1.5 0.03 1.4 --official --single_stance=3 --no_push --scale=feet_air_time:0 --scale=feet_slip:0 --restore=runs/off_ss_stage1b/params_latest.pkl
   ```

2. Export the ONNX file:

   ```
   JAX_PLATFORMS=cpu uv run python export_onnx.py runs/off_v2
   ```

3. Compare with the official policy in the harness:

   ```
   MUJOCO_GL=egl uv run python sim2sim_eval.py runs/off_v2
   ```

`--no_push` turns off the pushes. `--restore=<file>` starts from saved weights. `--scale=<reward>:<weight>` changes one reward weight.

## Files

| File | What it is |
|---|---|
| `bhl_biped_payload.xml` | Copy of the BHL biped MJCF with changes for MJX training (see below). |
| `bhl_env.py` | The joystick environment and the domain randomisation. Run it for the stand check. |
| `train.py` | PPO training. Saves a checkpoint (`params_<step>.pkl`) at every evaluation. |
| `evaluate.py` | Velocity tracking and falls for each payload, reward curve, and a video. |
| `bhl_official.py` | Round 3 environment with the official BHL policy interface. |
| `export_onnx.py` | Writes `policy.onnx` for a round 3 run, in the same form as the BHL file, and checks it. |
| `sim2sim_eval.py` | Compares a round 3 ONNX with the official BHL policy in the `sim/sim2sim` harness. |
| `runs/reward_curves.png` | Reward curves of all runs. |
| `runs/<name>/` | One folder per training run: `config.json`, `progress.jsonl`, `eval.json`, `eval_push.json`, `reward_curve.png`, `walk_payload1.5kg.mp4`, `params_latest.pkl`. |
| `_ref/` | Shallow clone of the official BHL Isaac Lab code, used as reference only (git-ignored). |

## How the environment is made

I reused the MuJoCo Playground "Berkeley Humanoid joystick" task.
A joystick task gives the robot a velocity command: forward speed, side speed and turn rate.
`bhl_env.py` keeps the Playground rewards, observations and pushes and only swaps the robot.

Changes in `bhl_biped_payload.xml`, compared with the third-party MJCF:

- The mesh path points to `../meshes`, and the `merged/` prefix is removed.
- Each joint has a position actuator with stiffness 20 and torque limit 6 Nm (official BHL Isaac Lab values). `train.py` can change the limit.
- Each joint has damping 2 (official value). I set it as joint damping, because MuJoCo then integrates it in a stable way at a 5 ms step.
- The armature is 0.007 for the legs and 0.002 for the ankles (official values).
- Only the two foot boxes touch the floor. This keeps the contact count low for MJX.
- A `payload` body sits 0.84 m above the base origin. This is about 0.80 m above the floor when the robot stands. The default mass is 1.5 kg.
- The `home` keyframe uses the official default pose: hip pitch -0.2, knee 0.4, ankle pitch -0.3 rad.

Settings in `bhl_env.py`:

- Simulation step 5 ms, policy step 40 ms (25 Hz), as in the official BHL config.
- Episode length 20 s. An episode ends when the torso tilts more than 0.78 rad (official value).
- Commands: forward -0.5 to 0.5 m/s, side -0.25 to 0.25 m/s, turn -1 to 1 rad/s (official ranges).
- Action scale 0.5 rad. See "Action scale" below for why this is not the official 0.25.
- Domain randomisation for each environment: payload 0 to 2.5 kg, payload centre of mass shift ±3 cm, link masses ±10 %, floor friction 0.4 to 1.0, joint friction ±10 %, PD stiffness ±20 %, default joint angles ±0.05 rad.
- Sensor noise and random pushes (0.1 to 1.0 m/s, every 5 to 10 s) as in Playground.

### Action scale

The official BHL policy uses action scale 0.25 with unbounded actions.
Brax PPO limits each action to the range -1 to 1.
With scale 0.25, each joint target can move only ±0.25 rad from the default pose.
My first run used 0.25. That policy learned to stand but never stepped.
So I changed the scale to 0.5, the value that Playground uses.

## How to run

All commands run from `sim/rl/`. The GPU is shared, so each JAX process sets a memory limit.

1. Install the training environment once. It needs Linux and an NVIDIA GPU. `sim/rl/pyproject.toml` keeps JAX below 0.9, because JAX 0.9 and newer remove functions that Brax 0.14 needs:

   ```
   uv sync
   ```

2. `sim2sim_eval.py` also needs the Berkeley assets. Fetch them once:

   ```
   ../../scripts/fetch_bhl_assets.sh
   ```

3. Run the stand check. The robot must stand for 1 s with the default pose and zero action:

   ```
   XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 uv run python bhl_env.py
   ```

4. Train. The arguments are steps, number of evaluations, output folder, torque limit (Nm), action scale, maximum payload (kg), payload centre of mass shift (m) and knee limit (rad):

   ```
   XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 nohup uv run python train.py 150e6 16 runs/my_run 6 0.5 3.5 0.05 1.4 > runs/my_run.log 2>&1 &
   ```

5. Evaluate a run. This writes `eval.json`, `reward_curve.png` and the video into the run folder. Add `push` at the end for the push test, which writes `eval_push.json`:

   ```
   XLA_PYTHON_CLIENT_MEM_FRACTION=0.15 MUJOCO_GL=egl uv run python evaluate.py runs/my_run
   ```

The first call compiles the code for the GPU, which takes about 1 minute.
One training run alone on the RTX 3090 does about 120 000 steps per second.

## How the evaluation works

`evaluate.py` runs 64 robots in parallel for 10 s for each case.
Each robot starts from the default stand. Sensor noise is on. Pushes are off.

The push test (`evaluate.py <run> push`) uses the same pushes as training.
A push is a sudden change of 0.1 to 1.0 m/s in the horizontal torso velocity, in a random direction.
Each robot gets a push every 5 to 10 s. The push test runs for 15 s, so each robot gets one or two pushes.
The push test does not include concept A.
The script ignores the first 2 s, so the robot can settle.
It measures the mean velocity error and the fraction of robots that fall.

The payload cases are 0 kg, 1.5 kg and 3.5 kg at the default point. The first results above used 2.5 kg instead of 3.5 kg.
A fourth case is concept A from `sim/payload/models/bhl_A.xml`.
Concept A is 1.44 kg with its centre of mass 9.6 cm higher than the default point.
This height is outside the training range, so this case tests robustness.

The commands are: stand still, walk forward at 0.3 m/s, and turn at 0.5 rad/s.

## Not done

- **Not done: a deployable policy.** The round 3 and 4 policies have the official interface, but they do not walk well and fall when pushed (see rounds 3 and 4).
- **Not measured on the robot.** All results are from simulation. The policy has not run on a laptop or on the board.
- **Not tested: sim-to-real.** There is no motor model, no latency and no check of the real BHL motor limits.
- **Not tested: rough ground, stairs or slopes.** The training floor is flat.
- **Not tested: payload higher than the training range.** Concept A is 9.6 cm higher and works, but I did not test other concepts (B to E).
- **Not done: export.** The policy is a Brax/JAX checkpoint (`params_latest.pkl`). It is not exported to ONNX or to the BHL runtime.
- **Planned: torque limit.** Find the real continuous torque of the BHL actuators. Then train with that limit and add a torque penalty.
- **Planned: longer training.** The rewards of both 121 M runs were still increasing.
- **Planned: payload range.** Train with the payload centre of mass up to 10 cm higher to cover concept A.
- **Planned: payload as a sensor input.** The policy does not know the payload mass. It adapts only from what it senses.

## Licence

`bhl_biped_payload.xml` is derived from the BHL assets (CC BY-SA 4.0, HybridRobotics).
`bhl_env.py` reuses MuJoCo Playground code (Apache 2.0, DeepMind).
