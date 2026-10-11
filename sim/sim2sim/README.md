# Sim-to-sim: the shipped BHL walking policy with our payloads

This folder runs the walking policy that BHL ships on our payload models in MuJoCo.
It answers one question: can the BHL policy, without retraining, stand and walk with each payload concept?

**Status:** tested in simulation (MuJoCo 3.15.0, Python 3.12, CPU only). Nothing here is measured on board.

**Not verified:**
- I did not retrain the policy. All results use the shipped checkpoint `policy_biped_25hz_a.onnx`.
- The payload masses are estimates from `sim/payload/README.md`.
- The simulation has no motor model, no delay and no IMU error. Real results will be worse.

## Short answer

1. With the 6 Nm torque limit of the training, no model falls in any test. This includes concept B with a full tank (2.7 kg).
2. With the 4 Nm limit of the BHL Python runtime on the robot, concept B (full) falls within 1 s after the start drop. A, B empty, D and E fall in some walk tests.
   So we must use at least the training limit, 6 Nm, on the robot.
3. **The policy does not turn on the spot.** A command of 0.5 rad/s with vx = 0 gives at most 0.06 rad/s.
   With vx = 0.2 m/s, the same turn command gives 0.49 to 0.54 rad/s, except for B full (0.29 rad/s).
4. **Handled in `aim/`:** `aim/` now always walks at 0.25 m/s or more when it turns (`aim/controller.py`, `Controller._walk` and `turn_vx`).
   The policy limit itself is unchanged.
5. Without sensor noise, the policy sometimes stands still on a walk command. With the training noise, it walks in every 6 Nm test.
6. Even at 6 Nm, walking clips a joint torque in 34 to 86% of the physics steps. B full tracks only 0.16 of the 0.3 m/s command.
7. In the closed-loop demo with `aim/` (concept A), the robot reached SPRAY at 11.9 s and put out the fire, without a fall.
   It stood still for 6 s at vx = 0.2 m/s. The policy walks reliably only from about 0.25 m/s (section "Closed-loop demo").
   `aim/` now uses 0.25 m/s. The demo on the real-CAD model A had no stop (section "Models from the real CAD parts").

Cause of item 3: BHL gives the stepping reward only when the linear command is above 0.1 m/s.
See BHL `source/berkeley_humanoid_lite/berkeley_humanoid_lite/tasks/locomotion/velocity/mdp/rewards.py:55-56`.
`aim/` now adds forward speed while it turns. A retrained policy should still reward steps for a turn-only command.

## What `run.py` does

`run.py` is our own code. It copies the rules of the BHL runtime, with the line numbers below in the BHL repos at the commits named in `docs/locomotion/README.md`.

| Part | Value in `run.py` | BHL source |
| --- | --- | --- |
| Policy | `policy_biped_25hz_a.onnx`, input `obs` (1 × 45), output `actions` (1 × 12) | BHL `checkpoints/`, LL `policy/rl_controller.py:49-67` |
| Observation | command (3), IMU angular velocity (3), projected gravity (3), joint position − default (12), joint velocity (12), last action (12) | LL `policy/rl_controller.py:161-184` |
| Projected gravity | the same quaternion formula as BHL, from the `imu_quat` sensor | LL `policy/rl_controller.py:78-95` |
| Joint target | default + 0.25 × action. The default is hip pitch −0.2, knee 0.4, ankle pitch −0.3, others 0 rad | LL `policy/rl_controller.py:190-195`; BHL `configs/policy_biped_25hz_a.yaml` |
| PD control | torque = 20 × (target − position) − 2 × velocity, clipped to ±6 Nm or ±4 Nm, at every physics step | BHL `environments/mujoco.py:183-201` |
| Rates | policy 25 Hz, physics 2000 Hz | BHL `configs/policy_biped_25hz_a.yaml` (`policy_dt`, `physics_dt`) |
| Start state | base at (0, 0, 0), upright, default joints. The feet start 3.9 cm above the floor, so the robot drops | BHL `environments/mujoco.py:143-155` |
| Model E | a 5 N force, backward along world x, at the `hose_connector` site | `sim/payload/analyze.py:28-31` |

- The models are `sim/payload/models/bhl_*.xml`. `run.py` reads them and does not change them. It sets the timestep to 0.5 ms.
- A fall is a torso tilt above 0.78 rad (the BHL training limit) or an IMU height below 60% of its start height (`run.py:99`).
- Mean vx is the IMU speed along the robot heading. Mean yaw rate is the torso angular speed about the world z axis.
  Both are averages from 5 s to 20 s, so the start drop does not count (`run.py:103-108`).
- "Steps with a clipped torque" is the share of physics steps where at least one joint asked for more than the limit.
- `--noise` adds the uniform observation noise of the training, with a fixed seed (BHL `biped/env_cfg.py:55-72`).
  The noise is ±0.3 rad/s on the angular velocity, ±0.05 on gravity and joint positions, and ±2.0 rad/s on joint velocities.
- `--start key` starts from the flat-foot `stand` keyframe of the payload models instead of the BHL start.

## How to run

1. Install the environment once, from the repository root (see the root README).

```bash
uv sync
```

2. Fetch the Berkeley assets once, from the repository root.

```bash
scripts/fetch_bhl_assets.sh
```

3. Run the self-check. It checks that the bare biped stands for 5 s with a zero command.

```bash
uv run python sim/sim2sim/run.py --check
```

4. Run all tests without noise. This writes `results/results.md` in about 25 s on 4 CPU cores.

```bash
uv run python sim/sim2sim/run.py
```

5. Run all tests with the training noise. This writes `results/results_noise.md`.

```bash
uv run python sim/sim2sim/run.py --noise
```

6. Run all tests from the flat-foot keyframe. This writes `results/results_keyframe.md`.

```bash
uv run python sim/sim2sim/run.py --start key
```

7. Make a video of one test, for example the best case.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/run.py --video bhl_A "vx 0.2 + yaw 0.5" 6 best.mp4 --noise
```

## Results

Each cell gives the mean vx (m/s) and the mean yaw rate (rad/s) from 5 s to 20 s, or the time of the fall.
The commands are: stand still, vx = 0.3 m/s, yaw rate = 0.5 rad/s, and vx = 0.2 m/s with yaw rate = 0.5 rad/s.
The last command is like the `aim/` APPROACH state. The full tables, with the torque numbers, are in the `results*.md` files.

### With the training noise (`results/results_noise.md`)

| Model | Limit (Nm) | stand | vx 0.3 | yaw 0.5 | vx 0.2 + yaw 0.5 |
|---|---|---|---|---|---|
| bhl_biped | 6 | stands | vx +0.29 | yaw +0.04 | vx +0.19, yaw +0.50 |
| bhl_biped | 4 | stands | vx +0.17 | yaw +0.03 | vx +0.09, yaw +0.38 |
| bhl_A | 6 | stands | vx +0.30 | yaw +0.03 | vx +0.20, yaw +0.53 |
| bhl_A | 4 | stands | vx +0.22 | yaw +0.06 | **falls 4.9 s** |
| bhl_B | 6 | stands | vx +0.16 | yaw +0.01 | vx +0.07, yaw +0.29 |
| bhl_B | 4 | **falls 0.9 s** | **falls 0.8 s** | **falls 0.9 s** | **falls 0.8 s** |
| bhl_B_empty | 6 | stands | vx +0.28 | yaw +0.03 | vx +0.16, yaw +0.50 |
| bhl_B_empty | 4 | stands | **falls 17.1 s** | yaw +0.02 | **falls 14.0 s** |
| bhl_D | 6 | stands | vx +0.28 | yaw +0.01 | vx +0.18, yaw +0.54 |
| bhl_D | 4 | stands | **falls 5.2 s** | yaw +0.01 | **falls 4.7 s** |
| bhl_E | 6 | stands | vx +0.21 | yaw +0.01 | vx +0.21, yaw +0.49 |
| bhl_E | 4 | stands | vx +0.06 | **falls 1.5 s** | **falls 13.1 s** |

### Without noise, BHL start (`results/results.md`)

| Model | Limit (Nm) | stand | vx 0.3 | yaw 0.5 | vx 0.2 + yaw 0.5 |
|---|---|---|---|---|---|
| bhl_biped | 6 | stands | vx +0.28 | yaw -0.00 | vx +0.00, yaw -0.00 |
| bhl_biped | 4 | stands | vx +0.16 | yaw -0.00 | vx +0.00, yaw -0.00 |
| bhl_A | 6 | stands | vx +0.30 | yaw -0.00 | vx +0.21, yaw +0.54 |
| bhl_A | 4 | stands | vx +0.21 | yaw -0.00 | vx +0.15, yaw +0.43 |
| bhl_B | 6 | stands | vx +0.23 | yaw -0.00 | vx +0.00, yaw -0.00 |
| bhl_B | 4 | **falls 0.9 s** | **falls 0.7 s** | **falls 0.9 s** | **falls 0.8 s** |
| bhl_B_empty | 6 | stands | vx +0.29 | yaw -0.00 | vx +0.00, yaw -0.01 |
| bhl_B_empty | 4 | stands | vx +0.14 | yaw -0.00 | vx +0.07, yaw +0.32 |
| bhl_D | 6 | stands | vx +0.29 | yaw -0.00 | vx +0.17, yaw +0.58 |
| bhl_D | 4 | stands | **falls 17.2 s** | yaw -0.00 | vx +0.09, yaw +0.34 |
| bhl_E | 6 | stands | vx -0.00 | yaw -0.00 | vx -0.00, yaw -0.00 |
| bhl_E | 4 | stands | **falls 3.3 s** | yaw -0.00 | vx -0.00, yaw -0.00 |

- A value of exactly 0.00 on a walk command means that the robot stands still. The policy does not start to step.
- At 6 Nm, 5 of the 12 tests with a forward command stand still in this table.
- From the flat-foot keyframe (`results/results_keyframe.md`), this happens more often: 9 of the 12 tests at 6 Nm stand still.
- From the keyframe, B full at 4 Nm stands still without a fall. So the 4 cm drop at the BHL start causes its fall in the stand test.

## Videos

- `results/best_A_6Nm_vx0.2_yaw0.5_noise.mp4`: concept A, 6 Nm, vx 0.2 m/s with 0.5 rad/s, with noise. It walks on a circle (10 s).
- `results/worst_B_4Nm_stand.mp4`: concept B full, 4 Nm, stand command. It falls at 0.9 s, after the start drop (3 s).

## Closed-loop demo: policy + `aim/` + a fire (concept A)

**Status:** tested in simulation. `demo.py` connects the BHL policy (6 Nm) to the `aim/` controller in MuJoCo.

What `demo.py` does:

1. It loads `sim/payload/models/bhl_A.xml` and starts the robot as in `run.py`, with the training noise.
2. It puts a fire on the floor at x = 2.5 m, y = 1.5 m (2.9 m away, 31° to the left). The fire is visual only.
3. At 10 Hz, `aim/sim_demo.fake_detections` projects the fire into the concept A camera. It uses the MuJoCo base pose and the simulated pan and tilt angles. It adds pixel noise, misses and outliers.
4. The pan and tilt follow the commanded angles at 3 rad/s at most. They are not MuJoCo joints, so the gun in the video does not move.
5. `aim/controller.Controller` gets the detections. Its `vx` and `yaw_rate`, clipped to ±0.5 m/s and ±1 rad/s, go to the policy command at 25 Hz.
6. When the jet lands within 0.25 m of the fire centre, the fire loses health. It goes out after 3 s of water, as in `aim/sim_demo.py`.
7. The video shows the jet as blue spheres along the `aim/ballistics.jet_path` arc while the pump is on.

`demo.py` imports `aim/` and does not change it.

Run it:

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/demo.py
```

Result (one run, seed 1 for the detector, seed 0 for the noise):

| Item | Value |
| --- | --- |
| Reached SPRAY | yes, at 11.9 s |
| States | SEARCH 0 s, APPROACH 0.3 s, AIM 11.7 s, SPRAY 11.9 s, CHECK 15.8 s, DONE 18.9 s |
| Fire out | yes, after 3.3 s of pump time |
| Final distance from the base to the fire | 1.86 m (the `aim/` standoff is 2.0 m) |
| Fall | no |

- From 5 s to 11 s the robot stood still, although `aim/` sent vx = 0.2 m/s. Then it started to walk again by itself.
- The cause is the low speed. I ran `run.py` `simulate()` on `bhl_A` at 6 Nm, 20 s, straight walk, with these results (mean vx, 5–20 s):

| vx command (m/s) | Without noise | With noise |
| --- | --- | --- |
| 0.15 | 0.00 (stands still) | 0.00 (stands still) |
| 0.20 | 0.00 (stands still) | 0.18 |
| 0.25 | 0.26 | 0.25 |
| 0.30 | 0.30 | 0.30 |

- So the shipped policy walks reliably only from about 0.25 m/s. `aim/` used 0.2 m/s at the time of this demo.
  `aim/` now uses 0.25 m/s for `walk_speed`, `turn_vx` and `back_speed` (`aim/controller.py`, `ControllerConfig`).
  This is one model and one seed, so treat it as a first result.

Files: `demo.py`, `results/demo.mp4` (21 s, 0.15 MB), `results/demo.png` (base path coloured by state, and the states and commands over time), `results/demo_log.csv` (one row per 0.1 s).

## Models from the real CAD parts

**Status:** tested in simulation. The payload agent built `bhl_A_real.xml`, `bhl_B_real.xml` and `bhl_B_real_empty.xml` from the CAD parts.
I ran the shipped policy at 6 Nm with the training noise, 20 s for each test, with `run.py` `simulate()`:

```bash
uv run python -c "import sys; sys.path.insert(0, 'sim/sim2sim'); from run import simulate; print(simulate('bhl_B_real', (0.25, 0, 0), 6.0, noise=True))"
```

| Model | stand | vx 0.25 | vx 0.25 + yaw 0.5 |
|---|---|---|---|
| bhl_A_real | stands | vx +0.23 | vx +0.23, yaw +0.48 |
| bhl_B_real (tank full) | stands | vx +0.11 | vx +0.14, yaw +0.46 |
| bhl_B_real_empty | stands | vx +0.20 | vx +0.19, yaw +0.48 |

- No model falls. The values are means from 5 s to 20 s, in m/s and rad/s.
- B with a full tank walks at less than half of the 0.25 m/s command. Walking clips a joint torque in 61 to 72% of the physics steps.

Closed-loop demo on `bhl_A_real`, with the fire 2 m behind and 1.5 m to the right of the start (2.5 m away). `aim/` used `walk_speed` and `turn_vx` = 0.25 m/s at that time.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/demo.py bhl_A_real -2 -1.5 demo_real
```

| Item | Value |
| --- | --- |
| Reached SPRAY | yes, at 15.3 s |
| States | SEARCH 0 s (left arc), APPROACH 8.9 s, AIM 15.1 s, SPRAY 15.3 s, CHECK 19.4 s, DONE 22.4 s |
| Fire out | yes, after 3.5 s of pump time |
| Final distance from the base to the fire | 1.86 m |
| Fall | no |
| Stops on a walk command | none |

Files: `results/demo_real.mp4` (24 s, 0.2 MB), `results/demo_real.png`, `results/demo_real_log.csv`.

## Camera-in-the-loop test platform (for the fire detector)

**Status:** tested in simulation, with the **baseline** colour-threshold detector only. No real detector has run in it yet.

`camera_loop.py` closes the loop through a rendered camera image:

1. It builds the scene from `sim/payload/models/bhl_A_real.xml` (read-only). The copy has:
   - a pan joint (±90°) and a tilt joint (−45° to +30°) with position servos, at the `aim/geometry.py` pivot. The gun turns in the video.
   - the concept A camera `rgb` on the tilting part: pose from `aim/geometry.py`, 90° horizontal field of view, 640 × 480.
   - a nozzle site at the `aim/geometry.py` nozzle position.
   - a room: a checker floor and four walls, 14 m × 14 m.
   - the fires of the scenario: emissive orange and yellow flames. Their size and colour change in each camera image.
   - distractors: a red box (0.4 m) at (1.8, −0.9) m and a warm orange lamp bulb on a 1.6 m pole at (3.9, 0.6) m.
2. Every 100 ms it renders the robot camera image and calls `detect(rgb, t)` from the detector module.
3. It gives the detections, the base pose and the measured pan and tilt angles to `aim/controller.Controller`.
4. `vx` and `yaw_rate` go to the BHL policy (6 Nm, training noise). Pan and tilt go to the servos, at 3 rad/s at most.
5. When the pump is on, it computes where the jet lands from the true nozzle pose in MuJoCo, with `aim/ballistics.jet_path`.
   A fire goes out after 3 s of water within 0.25 m of its centre.
6. It labels each detection with the nearest projected object: a fire, the red box, the lamp, or none. A detection on a distractor or on none is false.
7. A run ends 1 s after `aim/` reaches DONE, 2 s after a fall, or at the time limit + 30 s.

### Scenario suite

Run the suite after every change in `aim/`. All runs use the model `bhl_A_real` and fixed random seeds, so the same code gives the same table.

| Scenario | Fires, world x, y (m) | Distractors | Time limit for "fires out" |
| --- | --- | --- | --- |
| `ahead` | (2.5, 0) | red box, lamp | 40 s |
| `behind_right` | (−2.0, −1.5) | red box, lamp | 50 s |
| `two_fires` | (2.5, 1.5) and (−1.0, −2.5) | red box, lamp | 90 s |
| `lamp_only` | none | lamp | - (it must never spray) |
| `too_close` | (0.5, 0): 0.5 m in front | red box, lamp | 50 s |
| `far` | (6.0, 0): 6 m away | red box, lamp | 70 s |

The robot starts at (0, 0) and faces +x. A scenario passes when all these checks pass:

- **Fires out in time:** every fire is out before the time limit.
- **No stray spray:** in no 100 ms sample with the pump on does the jet land more than 0.5 m from every fire. In `lamp_only`, any spray fails.
- **No fall:** the torso never tilts more than 0.78 rad.
- **Reached DONE:** `aim/` ends in DONE before the run ends.
- `too_close` only, **stepped back before spraying:** `aim/` sends vx < 0 before the first SPRAY.

Commands, from the repo root:

1. Run the quick check: all scenarios in 3 parallel processes, without video, in about 1 minute.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --quick
```

2. Run the full suite: the same table, plus `results/suite_two_fires.mp4` and `results/suite_two_fires_log.csv`, in about 2.5 minutes.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --suite
```

3. Run one scenario with its video, for example `far`. This writes `far.mp4`, `far_log.csv` and `results/scene_A_real.xml`.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --scenario far --out far
```

Both suite commands write `results/suite_results.md`. They exit with code 1 when a scenario fails.
In the video inset, a green box is a detection on a fire and a red box is a false detection.

### Suite result with the baseline detector

Run on 2026-10-10 at 10:34 with the `aim/` version of 10:25 (search again after CHECK, hold the commanded angles, hysteresis for too-close fires, spray interlock).
The `--quick` and `--suite` tables are the same for the same code.

| Scenario | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples | Detections on fires | False detections | Fall (s) | End (s) |
|---|---|---|---|---|---|---|---|---|---|
| ahead | **PASS** | 4.3 | 7.3 | 0.089 | 0 | 74 | 61 | - | 32.5 |
| behind_right | **PASS** | 15.9 | 18.9 | 0.084 | 0 | 106 | 56 | - | 44.2 |
| two_fires | **PASS** | 7.0 | 10.0, 37.9 | 0.094 | 0 | 258 | 80 | - | 63.0 |
| lamp_only | **PASS** | - | no fire | - | 0 | 0 | 53 | - | 21.2 |
| too_close | **PASS** | 4.0 | 7.0 | 0.062 | 0 | 68 | 70 | - | 32.2 |
| far | **PASS** | 35.6 | 38.7 | 0.089 | 0 | 267 | 152 | - | 63.8 |

- The mean landing error uses only the samples within 0.5 m of a fire.
- Almost all false detections are on the lamp. They do no harm: the pixel ray points above the horizon, so `aim/` cannot put them on the floor.
  A lamp lower than the camera (about 0.9 m) would fool the baseline. No scenario tests that yet.
- In `two_fires`, `aim/` searched again after CHECK. It found fire 1 and put it out at 37.9 s.
- In `too_close`, the robot stepped back first, then put the fire out at 7.0 s. It ended after the normal search, at 32.2 s.
  With the `aim/` version before the hysteresis, it went from SPRAY to APPROACH and back three times. It then used all 3 sprays (`max_sprays`).
- The baseline uses the bottom centre of each orange blob as the fire point, because `aim/` puts the point on the floor.

### Software in the loop (SIL): the real programs over UDP

**Status:** tested in simulation, on the laptop, with the real `aim/run.py` and the actuator node with mock servos.

`--sil` runs the robot programs as separate processes, connected over UDP as on the robot. The simulator replaces only the camera, the legs and the servos.

| Port | From | To | Content |
| --- | --- | --- | --- |
| 5600 | `camera_loop.py` (camera image + detector) | `aim/run.py A --feedback` | interface v2 frame messages: one per image, with an empty `detections` list when there is no fire |
| 5601 | `aim/run.py` | `actuators/actuator_node.py --mock` | pan, tilt, pump_on |
| 5602 | `aim/run.py` | `walk_bridge.AimGamepad`, inside `camera_loop.py` | vx, yaw_rate. The bridge clips them and sets zero after 0.5 s without a message |
| 5603 | actuator node | `aim/run.py` | measured pan, tilt (feedback) |
| 5604 | actuator node | `camera_loop.py` | the same feedback: the MuJoCo pan-tilt follows these angles, and `water` switches the jet |
| 5605 | `camera_loop.py` | `aim/run.py` | base pose `{"timestamp", "x", "y", "yaw"}` from MuJoCo, at 25 Hz. `--no-pose` switches it off: `run.py` then dead-reckons its walk command |

- `aim/run.py` and the actuator node run as separate processes, with the same Python as the simulator.
- The simulator runs in real time, because the other programs use `time.monotonic()`. All processes run on one computer, so they share the same clock.
- The simulator logs the stdout and stderr of `aim/run.py` and the stderr of the node.

Commands, from the repo root:

1. Run `ahead` and `two_fires` once in-process and 5 times over UDP (about 10 minutes). This writes `results/sil_results.md`.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --sil --repeat 5
```

2. Run `two_fires` over UDP without the pose stream (about 1.5 minutes). This writes `results/sil_results_no_pose.md`.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --sil --no-pose --sil-scenarios two_fires
```

Each SIL run also writes `sil_<scenario>_<run>_log.csv`, `sil_<scenario>_<run>_aim_stderr.log` and `sil_<scenario>_<run>_node.log`.

Results with the `aim/` version of 10:25. This version has:

- the pose input on 5605 with the torso `roll` and `pitch`. The simulator sends the MuJoCo torso angles: Z-Y-X, positive pitch tips the front down, as `aim/README.md` defines.
- confirmation = 3 detections within 0.6 s, and interface v2 frame messages.
- a spray interlock: no spray while the torso roll or pitch is above 15° or changes faster than 30°/s.
  Also no spray for 2 s after the start or after such an event (`aim/controller.py`, `MAX_BODY_TILT`, `MAX_TILT_RATE`, `SETTLE_TIME`).

| Scenario | Mode | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples |
|---|---|---|---|---|---|---|
| two_fires | in-process | PASS | 7.0 | 10.0, 37.9 | 0.094 | 0 |
| two_fires | SIL 1 to 5 | **5 of 5 PASS** | 5.4 to 7.5 | 8.4 to 10.5, 34.2 to 39.4 | 0.040 to 0.057 | 0 |
| ahead | in-process | PASS | 4.3 | 7.3 | 0.089 | 0 |
| ahead | SIL 1 to 3 | **3 of 3 PASS** | 4.4 | 7.4 | 0.051 to 0.062 | 0 |

- The in-process runs give `aim/` the pose without roll and pitch, so their landing error is larger.
- The pump ran in 79% to 86% of the SPRAY time. The torso tilt stayed at 7.3° or less while spraying.
- The 6-scenario suite (`--quick`, in-process) passed 6 of 6 with this `aim/` version (section "Suite result with the baseline detector").

History of the SIL results:

| `aim/` version | ahead | two_fires | Landing error (m) |
| --- | --- | --- | --- |
| interface v1, no pose input | 5 of 5 | 2 of 5 | 0.07 to 0.18 |
| pose input, interface v2 | 4 of 5 (one stray spray at the start) | 5 of 5. Also PASS without the pose stream (dead reckoning) | 0.08 to 0.12 |
| + roll and pitch, interlock at 6° | 5 of 5 | 4 of 5 (fire 1 not out in one run) | 0.04 to 0.08 |
| interlock at 15° or 30°/s | 3 of 3 | 5 of 5 | 0.04 to 0.06 |

With the 6° interlock, the torso stood at about −5° (front up) while spraying, and the policy steps added 2° to 3°.
So the pump stopped often and ran in only 22% to 80% of the SPRAY time. The 15° and 30°/s limits removed this problem.

Timing over UDP in the last 8 SIL runs (the full table is in `results/sil_results.md`; `results/sil_results_no_pose.md` has the earlier no-pose run):

| Item | Value |
| --- | --- |
| Frame messages rejected by `run.py` | 0 |
| `run.py` ticks with no new frame / with 2 frames | 1% to 29% / 1% to 29% of the ticks |
| Largest gap between two commands of `run.py` | 0.107 s |
| Walk command older than 0.5 s while `run.py` runs (bridge timeout) | 0 |
| Largest gap between two feedback messages of the node (50 Hz) | 0.15 to 0.19 s |
| Largest simulator lag behind real time | 0.06 to 0.09 s |
| `run.py` dead-reckoning messages | 1 per run, at the start, before the first pose arrives. No pose dropout later |

Findings:

1. **The three earlier problems are gone.** With the pose input and the frame messages, `two_fires` passed 5 of 5 SIL runs (before the interlock).
   It also passed with dead reckoning only, with a larger landing error (0.120 m against 0.087 to 0.106 m).
2. **Before the interlock: a too-early spray at the start (`ahead`, run 3). The interlock fixed it: no stray spray in the 18 later runs.**
   `aim/` went to AIM at 0.7 s. It sprayed at 1.0 s with the jet 0.59 to 0.70 m from the fire.
   The fire is 2.5 m away, so `aim/` should first walk to the 2.0 m standoff.
   At the start, the robot drops 4 cm onto its feet and the torso pitches. `aim/` assumes a level torso, so the fire looked nearer than 2.0 m.
   On the robot, walking also pitches the torso. A torso pitch and roll input (from the IMU), or no confirmation while the torso moves, would prevent this.
   The in-process run confirms the fire a little later and does not show it. So this is a timing-dependent result.
3. **No packet loss.** `run.py` rejected no message, its command gaps stayed at 0.11 s or less, and the walk bridge never timed out.
4. **The simulator sometimes fell behind real time, by up to 6.7 s in earlier runs (0.09 s at most in the last 8 runs).** Other jobs shared the CPU. It then runs faster to catch up, so some `run.py` ticks get two frames.
   Run the SIL test on an idle computer for timing results.
5. **Clocks:** all programs here run on one computer. A detector on another computer (open question Q1) has a different `time.monotonic()`.
   Then `run.py` rejects every message (its 1 s timestamp check). **Not tested.**
6. At the start, `run.py` writes "no fresh feedback" and "no fresh pose" once, before the first messages arrive. This is harmless.
7. When `run.py` reaches DONE, it stops. The walk bridge then sets zero velocity after 0.5 s, and the node switches the water off after 0.5 s. Both are safe.

### How Marc plugs in his detector

1. Write a Python file with a function `detect(rgb, t)` that returns a list of `FireDetection` (`aim/detection.py`).
2. Run the suite with `--detector` and the path of that file.

```bash
MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --quick --detector path/to/my_detector.py
```

Example module (I tested it with the baseline as `my_model`):

```python
from detection import FireDetection  # camera_loop.py puts aim/ on the import path


def detect(rgb, t):
    """rgb: 480 x 640 x 3 uint8 RGB image of camera "rgb". t: time of the image, s."""
    boxes = my_model(rgb)  # Marc's code: list of (u_min, v_min, u_max, v_max, score)
    return [FireDetection(t, "rgb", (u0 + u1) / 2, v1, (u0, v0, u1, v1), score)
            for u0, v0, u1, v1, score in boxes]
```

Rules for the detector:

- The image is RGB, not BGR. OpenCV code must convert it with `cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)`.
- The camera intrinsics are the `aim/geometry.py` values: fx = fy = 320 px, cx = 320 px, cy = 240 px.
- Give `u, v` at the point where the fire touches the floor, for example the bottom centre of the box. `aim/` intersects that pixel ray with the floor.
  If the detector knows the distance, it can set `depth_m` instead.
- A confidence below 0.5 is ignored (`aim/controller.py`, `min_conf`).
- Return an empty list when there is no fire.
- The simulation waits for `detect`, so this test does not check the detector speed. On the robot, it must run at 10 Hz or faster.
- To add the packages of your detector, run `uv add <package>` in the repository root.

### Limits of the camera test

- The image is a clean OpenGL render: no lens distortion, noise, blur, exposure change, smoke or real flame texture.
- The fires are simple emissive ellipsoids. A detector trained on real fire images may not detect them. Then use real images or textures.
- The jet has no drag and uses the `aim/` placeholder speed of 8 m/s.

## Files

| File | What |
| --- | --- |
| `run.py` | the simulation loop, the result tables, the videos and the self-check |
| `policy_biped_25hz_a.onnx` | copy of BHL `checkpoints/policy_biped_25hz_a.onnx`, commit `984741a`, SHA-256 `65769d21…2fd94e` |
| `BHL_LICENCE` | the MIT licence of the BHL code, which the policy copy requires |
| `results/results.md`, `results/results_noise.md`, `results/results_keyframe.md` | full result tables |
| `best_*.mp4`, `worst_*.mp4` | the two videos of the test matrix |
| `demo.py`, `results/demo.mp4`, `results/demo.png`, `results/demo_log.csv` | the closed-loop demo with `aim/` |
| `camera_loop.py`, `baseline_detector.py`, `results/scene_A_real.xml` | the camera-in-the-loop test platform and its scenario suite. A single run writes the scene file |
| `results/suite_results.md`, `results/suite_two_fires.mp4`, `results/suite_two_fires_log.csv` | the last suite result, and the video and log of `two_fires` |
| `results/sil_results.md`, `results/sil_results_no_pose.md`, `sil_*_log.csv`, `sil_*_aim_stderr.log`, `sil_*_node.log` | the last software-in-the-loop results and their logs |

## Limits of this check

- The motors are ideal torque sources with a hard limit. There is no torque-speed curve, no heat and no CAN delay.
- The IMU and the joint sensors are perfect, except for the optional uniform noise.
- Each test runs once, with one seed. A different seed can change a marginal result, for example a fall at 14 s.
- The model E hose force always points along world −x, also when the robot turns.
