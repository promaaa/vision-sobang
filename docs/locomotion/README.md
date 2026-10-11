# Locomotion: how BHL trains, tests and runs its walking policy

This page explains how the Berkeley Humanoid Lite (BHL) team trains, tests and runs its walking policy.
It then gives our plan to reproduce it, retrain it with our payload, and drive it from `aim/run.py`.

**Status of our work:** the sim-to-sim check of the shipped BHL policy with our payloads is **tested in simulation** (section 8).
Everything else on this page that we do is **planned**. Nothing is measured on laptop or measured on board yet.
The facts about BHL come from their code, their docs site and their paper.

**Not verified:** I did not run the BHL scripts. I ran only their policy file, in our own loop (section 8).
Each "Not verified" note below says what is still open.

## Short answer to Q2

Q2 in `docs/architecture.md` asks how the walking policy receives `vx` and `yaw_rate` on the real robot.

1. In the BHL Python runtime, a USB gamepad gives the command. There is no network input.
2. A thread (`Se2Gamepad`) reads the sticks and writes `velocity_x`, `velocity_y` and `velocity_yaw` into a dictionary (LL `policy/gamepad.py:91-101`).
3. Each control tick, `Humanoid.get_observations()` copies these three numbers into the state vector, slots 32 to 34 (LL `robot/humanoid.py:191-194`).
4. `RlController.update()` reads slots 32 to 34 and puts them first in the 45-number policy input (LL `policy/rl_controller.py:167,176-184`).
5. The stick value goes in without scaling: full stick = 1.0 (m/s or rad/s) (LL `policy/gamepad.py:96-101`).
6. The BHL C runtime reads the command from a 13-byte UDP packet on port 10011 (LL `csrc/real_humanoid.cpp:243-274`).
   The sender of that packet and the policy process for the C runtime are not in the public code.

The smallest change for us: replace the `Se2Gamepad` object, created at LL `robot/humanoid.py:69`, with a subclass that also reads our UDP JSON.
Section 6, part C, describes it.

## 1. Sources

| Short name | What | Version that I read |
| --- | --- | --- |
| BHL | Main repo, shallow clone in `docs/locomotion/_ref/Berkeley-Humanoid-Lite/` | commit `984741a`, 2026-03-10, <https://github.com/HybridRobotics/Berkeley-Humanoid-Lite/tree/984741a3623c93b0583ccfdc479f1f8b1c4d900e> |
| LL | Low-level repo (robot runtime), shallow clone in `docs/locomotion/_ref/Berkeley-Humanoid-Lite-Lowlevel/` | commit `652777c`, 2025-09-07. BHL pins this commit as its submodule. <https://github.com/HybridRobotics/Berkeley-Humanoid-Lite-Lowlevel/tree/652777cc7c49884e7cd7ddfada758dc1979bf627> |
| AS | Assets repo, already in our repo at `third_party/berkeley-humanoid-lite-assets/` | commit `fc90fed`. BHL pins the same commit. |
| D | Docs site | <https://berkeley-humanoid-lite.gitbook.io/docs>, read on 2026-10-08. The site banner says "Last update: 2025-09-07". |
| P | Paper, arXiv 2504.17249v1 | <https://arxiv.org/abs/2504.17249> |

- `_ref/` is in `docs/locomotion/.gitignore`, so git does not track the clones.
- To get them again, run `git clone --depth 1 <url>` for each repo into `docs/locomotion/_ref/`.
- Numbers after a colon are line numbers. This page uses these short paths:

| Short path | Full path |
| --- | --- |
| BHL `biped/...` | `source/berkeley_humanoid_lite/berkeley_humanoid_lite/tasks/locomotion/velocity/config/biped/...` |
| BHL `velocity_env_cfg.py` | `source/berkeley_humanoid_lite/berkeley_humanoid_lite/tasks/locomotion/velocity/velocity_env_cfg.py` |
| BHL `environments/mujoco.py` | `source/berkeley_humanoid_lite/berkeley_humanoid_lite/environments/mujoco.py` |
| BHL `scripts/...`, `configs/...` | the same path from the BHL repo root |
| LL `policy/...`, `robot/...`, `recoil/...` | `berkeley_humanoid_lite_lowlevel/policy/...` and so on, in the LL repo |
| LL `scripts/...`, `csrc/...`, `README.md` | the same path from the LL repo root |
| AS `robots/...` | `third_party/berkeley-humanoid-lite-assets/berkeley_humanoid_lite_assets/robots/...` |
| AS `.../urdf/...`, `.../mjcf/...` | `third_party/berkeley-humanoid-lite-assets/data/robots/berkeley_humanoid/berkeley_humanoid_lite/urdf/...` and so on |
| D `name` | the docs page whose URL ends with `name`, under <https://berkeley-humanoid-lite.gitbook.io/docs/> |

## 2. Training

### 2.1 Framework and tasks

- The code uses Isaac Lab with the RSL-RL library and the PPO algorithm (BHL `scripts/rsl_rl/train.py`, BHL `biped/agents/rsl_rl_ppo_cfg.py`).
  PPO (Proximal Policy Optimization) is a standard reinforcement-learning (RL) method.
- The paper says "Isaac Gym-trained policy" (P, section V-A). The current code uses Isaac Lab, not Isaac Gym.
- Two tasks exist (D `getting-started-with-software/training-environment`):
  - `Velocity-Berkeley-Humanoid-Lite-v0`: full robot, 22 joints.
  - `Velocity-Berkeley-Humanoid-Lite-Biped-v0`: legs only, 12 joints (BHL `biped/__init__.py:10`). **We use this one**, because we keep only the legs and torso.
- Versions disagree between the docs and the code:
  - The docs install Isaac Sim 4.5.0 and Isaac Lab 2.1.0, checked on Ubuntu 24.04 (D `training-environment`).
  - The code at commit `984741a` pins Python 3.11, `isaacsim==5.1.0`, `isaaclab==2.3.2.post1` and `torch==2.7.0` (BHL `pyproject.toml`).
- The default training run (biped):
  - 4096 parallel environments (BHL `velocity_env_cfg.py:66`).
  - 24 steps per environment per iteration, 6000 iterations (BHL `biped/agents/rsl_rl_ppo_cfg.py:7-8`).
  - Policy and critic networks: MLP 256-128-128, ELU activation (same file, lines 14-15).
  - Flat ground plane only (BHL `velocity_env_cfg.py:21-24`). Episodes last 20 s (line 72).
- Training time: the docs say 6000 iterations take "around two hours" (D `training-environment`).
  The docs, the code and the paper do not name the GPU.

### 2.2 Observation and action layout (biped)

The policy input has 45 numbers, in this order (BHL `biped/env_cfg.py:51-73`, LL `policy/rl_controller.py:176-184`):

| Index | Term | Unit | Training noise |
| --- | --- | --- | --- |
| 0-2 | velocity command: vx, vy, yaw rate | m/s, m/s, rad/s | none |
| 3-5 | base angular velocity (from the IMU) | rad/s | ±0.3 |
| 6-8 | projected gravity (gravity direction in the torso frame) | unit vector | ±0.05 |
| 9-20 | joint positions minus default positions | rad | ±0.05 |
| 21-32 | joint velocities | rad/s | ±2.0 |
| 33-44 | previous action | - | none |

- There is no observation history (`history_length: 0`, BHL `configs/policy_biped_25hz_a.yaml`).
- The joint order is the left leg, then the right leg (AS `robots/berkeley_humanoid_lite.py:11-24`).
  Each leg has hip roll, hip yaw, hip pitch, knee pitch, ankle pitch and ankle roll, in this order.
- The default joint positions are hip pitch -0.2, knee 0.4, ankle pitch -0.3, all others 0 rad (same file, lines 60-73).
- The policy gives 12 actions. Joint target = default position + 0.25 × action (BHL `biped/env_cfg.py:95-101`, LL `policy/rl_controller.py:195`).
- The policy does not see the base linear velocity. Only the critic sees it (BHL `biped/env_cfg.py:79-81`).
  The critic is the second network that PPO uses only during training.

### 2.3 Control frequency

| Loop | Rate | Source |
| --- | --- | --- |
| Physics in training | 200 Hz (dt 0.005 s) | BHL `velocity_env_cfg.py:75` |
| Policy in training, biped task | 25 Hz (decimation 8) | BHL `biped/env_cfg.py:348` |
| Shipped checkpoints | 25 Hz (`policy_biped_25hz_a`, `_b`) and 50 Hz (`policy_biped_50hz`) | BHL `configs/*.yaml`, `policy_dt` |
| Policy on the robot (paper) | 25 Hz | P, section V-A |
| CAN and IMU on the robot (paper) | 250 Hz | P, section III-A |
| Robot, Python runtime | one loop at the policy rate: policy, CAN and IMU together | LL `scripts/run_locomotion.py:23-37` |
| Robot, C runtime | motor loop at 250 Hz, joystick input at 20 Hz | LL `csrc/real_humanoid.cpp:479,483` |

### 2.4 PD gains, effort limits and action scale

The motor drivers run a PD position loop: torque = kp × (target − position) − kd × velocity.
The sim-to-sim script uses the same formula (BHL `environments/mujoco.py:195-196`).

| Setting | Training (Isaac Lab) | Robot, C runtime | Robot, Python runtime |
| --- | --- | --- | --- |
| kp (Nm/rad) | 20 | from YAML: 20 | 20, fixed in code |
| kd (Nm·s/rad) | 2 | from YAML: 2 | 2, fixed in code |
| Torque limit (Nm) | 6 | from YAML: 5 or 6 | 4, fixed in code |
| Action scale | 0.25 | 0.25 | 0.25 |

Sources: AS `robots/berkeley_humanoid_lite.py:78-101` (training, also armature 0.007 and 0.002, velocity limit 10 rad/s).
BHL `configs/policy_biped_*.yaml` `effort_limits` and LL `csrc/real_humanoid.cpp:50-54,508-520` (C runtime).
LL `robot/humanoid.py:121-148` (Python runtime: `enter_damping()` writes kp 20, kd 2, torque limit 4 Nm to all motors).

- The Python runtime does not read `joint_kp`, `joint_kd` or `effort_limits` from the YAML file. It always uses 4 Nm.
- The MuJoCo model allows ±20 Nm (`forcerange`, AS `.../mjcf/berkeley_humanoid_lite_biped.xml:171`). The sim-to-sim script clips to the YAML `effort_limits` (BHL `environments/mujoco.py:199`).
- The paper says walking used only 30% of the actuator torque limit (P, section V-A). The paper does not give the limit value there.

### 2.5 Domain randomisation (biped)

Domain randomisation means random changes to the simulated robot, so that the policy also works on the real robot.

| Term | Value | Source (BHL `biped/env_cfg.py`) |
| --- | --- | --- |
| Friction, static and dynamic | 0.4 to 1.2 | 226-236 |
| **Added base (torso) mass** | **−1.0 to +2.0 kg, added to the `base` body** | **237-245** |
| Default joint position offset | ±0.05 rad | 246-254 |
| kp and kd scale | 0.8 to 1.2 | 255-264 |
| Start pose and velocity | ±0.5 m, any yaw, ±0.5 m/s and rad/s | 267-281 |
| Joint start position scale | 0.5 to 1.5 | 282-289 |
| External force and torque on the base, at reset | ±2 N, ±2 Nm | 290-300 |
| Pushes during the episode | disabled (commented out) | 303-308 |
| **Centre of mass (CoM) offset** | **none** | - |
| Motor delay, torque limit change | none | - |

- The bare biped `base` body has 3.16 kg, with its CoM at z = 0.638 m. The whole biped has 11.34 kg (AS `.../urdf/berkeley_humanoid_lite_biped.urdf:6-10`, and the sum of all link masses).
- Isaac Lab 2.3.2 `randomize_rigid_body_mass` also scales the inertia by the mass ratio. It does not move the CoM (<https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/source/isaaclab/isaaclab/envs/mdp/events.py>, lines 286-397).
- Isaac Lab 2.3.2 has a separate term `randomize_rigid_body_com` (same file, lines 400-438). BHL does not use it.

### 2.6 Velocity commands in training (biped)

| Command | Range | Source (BHL `biped/env_cfg.py`) |
| --- | --- | --- |
| vx | −0.5 to 0.5 m/s | 34 |
| vy | −0.25 to 0.25 m/s | 35 |
| yaw rate | −1.0 to 1.0 rad/s | 36 |

- The command changes every 10 s (line 26).
- All environments use heading mode: a heading error makes the yaw-rate command, clipped to ±1.0 rad/s (lines 29-32).
- Only 2% of environments train with a zero command, that is, standing still (`rel_standing_envs=0.02`, line 31).
- Our `aim/` limits are inside these ranges: walk speed 0.25 m/s and yaw rate up to 0.6 rad/s (`aim/controller.py`, `ControllerConfig`).
  `aim/` also walks at 0.25 m/s or more whenever it turns (`turn_vx`).

### 2.7 Export

- `play.py` exports the policy to ONNX and TorchScript, in `logs/rsl_rl/<experiment>/<run>/exported/` (BHL `scripts/rsl_rl/play.py:97-104`).
- It also writes `configs/policy_latest.yaml` with the gains, limits, rates and default positions for deployment (same file, lines 106-176).
- The `command_velocity` value in that YAML is one random sample from the simulator (lines 161-165). The robot runtime does not use it as the command.
- The ONNX input name is `obs` (LL `policy/rl_controller.py:58-64`).

## 3. Sim-to-sim check in MuJoCo

- Command: `uv run ./scripts/sim2sim/play_mujoco.py --config ./configs/policy_latest.yaml` (D `getting-started-with-software/sim2sim-validation`).
- The script runs the same `RlController` as the robot. It replaces the robot with a MuJoCo model at 2000 Hz physics (BHL `scripts/sim2sim/play_mujoco.py`, BHL `environments/mujoco.py:100-201`, `physics_dt: 0.0005` in the YAML).
- It does PD control in software with the YAML gains and clips to the YAML `effort_limits` (BHL `environments/mujoco.py:183-201`).
- It needs a USB gamepad on the host. It reads the gamepad with the same `Se2Gamepad` class (BHL `environments/mujoco.py:140`, D `sim2sim-validation`).
- It scales the vy stick by 0.5, but not vx or yaw (BHL `environments/mujoco.py:270-272`).
- The check is visual: you drive the robot with the gamepad and watch. The script computes no score.
- **Not verified:** the script loads `source/berkeley_humanoid_lite_assets/data/mjcf/bhl_biped_scene.xml` (BHL `environments/mujoco.py:40`).
  In the pinned assets, this file is at `data/robots/berkeley_humanoid/berkeley_humanoid_lite/mjcf/bhl_biped_scene.xml`. The path may need a fix.

## 4. Deployment on the robot

### 4.1 Hardware and software

| Item | Value | Source |
| --- | --- | --- |
| Computer | Intel N95 mini PC ("BeeLink N95 NUC") in the torso | P, section III-A; D `getting-started-with-software/the-on-board-computer` |
| OS | Ubuntu 22.04 | D `the-on-board-computer` |
| Language | Python runtime, or C++ runtime for the control loop | LL `scripts/run_locomotion.py`, LL `csrc/` |
| Policy format | ONNX with `onnxruntime`, or TorchScript `.pt` | LL `policy/rl_controller.py:125-142` |
| Motor bus | CAN 2.0 at 1 Mbit/s, one bus per limb, 4 USB-CAN adapters | P, section III-A; LL `scripts/start_can_transports.sh:1-4` |
| CAN driver | SocketCAN (`python-can`, `interface="socketcan"`); the docs show the `gs_usb` driver | LL `recoil/core.py:195-206`; D `in-depth-contents/can-communication` |
| Legs on the bus | Python and C runtimes: left leg `can0`, right leg `can1`. CAN IDs left 1,3,5,7,11,13 and right 2,4,6,8,12,14. The docs put the legs on `can2` and `can3` when the arms are present | LL `robot/humanoid.py:34-62`; LL `csrc/real_humanoid.cpp:396-439`; D `in-depth-contents/joint-id-mapping` |
| Motor driver | B-G431B-ESC1 board with the Recoil firmware | P, section III-C; D `getting-started-with-hardware/flashing-the-motor-controllers` |
| IMU | BNO085 through an Arduino (C runtime), or HiWonder IM10A on USB (Python runtime). The docs recommend the IM10A | LL `csrc/consts.h:32-33`; LL `robot/imu.py:163`; D `getting-started-with-hardware/building-the-robot` |
| Battery | 6S 4000 mAh LiPo, about 30 min | P, section III-A |

- The USB-CAN adapter model is not named. The BOM gives only an Amazon link (D `getting-started-with-hardware/materials-and-parts-bom`).
- The gamepad model is not named. The docs figure shows an Xbox-style gamepad (D `sim2sim-validation`).

### 4.2 Two runtimes

**A. Python runtime** (LL `scripts/run_locomotion.py`). The docs give `uv run ./scripts/python/run_locomotion.py` (D `the-on-board-computer`).
The script is at `scripts/run_locomotion.py` in LL `652777c`.

1. It loads the YAML given with `--config`. The default `./configs/policy_biped.yaml` is not in either repo (LL `policy/config.py:59`).
2. It loads the ONNX policy (lines 20-21), then creates `Humanoid()` (line 25).
3. `Humanoid()` opens `can0` and `can1`, the IMU and the gamepad thread. It reads `calibration.yaml` (LL `robot/humanoid.py:27-119`).
4. One loop runs at the policy rate. Each tick does inference, then one CAN exchange with each motor (lines 23-37).
5. Each tick also sends the state vector by UDP to `172.28.0.5:11000`, a hard-coded address (lines 16 and 35).
   The BHL visualiser listens on port 11000 (BHL `scripts/sim2real/visualize.py:23`).

**B. C runtime** (LL `csrc/`, start with `make run`). The docs recommend it for locomotion (D `the-on-board-computer`).

1. It runs the motor loop every 4 ms, that is 250 Hz (LL `csrc/real_humanoid.cpp:483`). The code comment says 100 Hz.
2. It sends the 35-number state vector to UDP port 10000, once per policy period (lines 181-198).
3. It reads 12 joint targets from UDP port 10001 (lines 288-297, `csrc/consts.h:9-12`).
4. It reads the gamepad command from UDP port 10011 (lines 243-274).
5. **Not verified:** the process that runs the policy between ports 10000 and 10001 is not in LL or BHL. `policy_forward()` is empty (lines 284-286).
6. **Not verified:** the sender `udp_joystick.py` is named in LL `README.md:43` and in the docs, but it is not in LL `652777c`.

### 4.3 How the velocity command enters the policy (Q2)

Python runtime, step by step:

1. `Se2Gamepad` (LL `policy/gamepad.py:46-117`) runs in its own thread. It blocks on `inputs.get_gamepad()`.
2. Left stick up/down gives `velocity_x`. Right stick left/right gives `velocity_y`. Left stick left/right gives `velocity_yaw` (lines 92-101).
3. The value is `raw / -32768`, so it is between −1 and 1. There is no scaling to m/s or rad/s.
4. `Humanoid.get_observations()` copies the three values into state slots 32-34 every tick (LL `robot/humanoid.py:191-194`).
5. `RlController.update()` reads slots 32-34 as `command_velocity` and puts them at policy input 0-2 (LL `policy/rl_controller.py:167,177`).

C runtime packet on UDP port 10011, 13 bytes (LL `csrc/real_humanoid.cpp:243-274`):

| Byte | Type | Meaning |
| --- | --- | --- |
| 0 | uint8 | mode: 0 = no change, 1 = idle (damping), 2 = RL init, 3 = RL running |
| 1-4 | float32 | vx |
| 5-8 | float32 | vy |
| 9-12 | float32 | yaw rate |

- **Not verified:** the byte order. The code casts the bytes to `float` on an x86 computer, so it is little-endian there.

Problems that we found in this path:

- Full stick gives 1.0 m/s, but the biped policy trained only up to 0.5 m/s. A large stick input is outside the training range.
- If the gamepad thread stops (for example, the gamepad disconnects), the last command stays. No timeout exists in the Python runtime.

### 4.4 Modes and safety

| Action | Gamepad | Effect | Source |
| --- | --- | --- | --- |
| RL init | LB + A | Motors go to position mode. Joints move to the default pose in 100 ticks (Python) or 200 ticks (C) | LL `robot/humanoid.py:243-261`; LL `csrc/real_humanoid.cpp:87-98` |
| RL running | RB + A | The policy targets go to the motors | LL `robot/humanoid.py:263-285` |
| Stop (idle) | X or a stick press | Motors go to damping mode | LL `policy/gamepad.py:113-115` |
| Ctrl+C, first time | keyboard | Damping mode | LL `robot/humanoid.py:150-158`; LL `README.md:76` |
| Ctrl+C, second time | keyboard | Motors unpowered (idle) | same |

- In damping mode the motors resist motion but do not hold a position.
- LL `README.md:74` says the stop button is `B`. The code checks `BTN_X`, which `inputs` names `BTN_NORTH` (LL `policy/gamepad.py:36,114`). The docs figure says X.
  **Not verified:** which physical button this is on our gamepad.
- The runtime has no software joint-limit clamp. The YAML action limits are ±10000 (BHL `configs/policy_biped_50hz.yaml:101-102`).
  The backpack needs knee ≤ 1.4 rad (`cad/backpack/README.md`). So we must add this limit: clip the knee targets in our start script, before `robot.step()`.
- The runtime has no automatic stop when the torso tilts. Training ends an episode at 0.78 rad tilt (BHL `biped/env_cfg.py:215-218`), but the robot code does not.
- The motor firmware has a watchdog. The example motor file sets `watchdog_timeout: 1000` (BHL `motor_configuration.json:39`). **Not verified:** the unit and what happens at timeout.
- The hardware has a main switch with a circuit breaker (D `building-the-robot`, wiring diagram). The docs do not describe an e-stop button.

## 5. Hardware bring-up steps that BHL describes

1. Flash each motor driver with STM32CubeIDE and the Recoil firmware. Set the CAN ID (1 to 63) in `motor_controller_conf.h` (D `flashing-the-motor-controllers`).
2. Calibrate the electrical offset of each motor: `calibrate_electrical_offset.py -c can0 -i 1`. The motor must turn freely (D `flashing-the-motor-controllers`; LL `scripts/motor/calibrate_electrical_offset.py`).
3. Start the CAN buses: `sudo ./scripts/start_can_transports.sh`, 1 Mbit/s on `can0` to `can3` (LL `README.md:21-27`; LL `scripts/start_can_transports.sh:1-4`).
4. Check that each motor answers: `ping.py` or `check_connection.py` (D `the-on-board-computer`; LL `scripts/check_connection.py`).
5. Test the IMU: `test_imu.py` (D `the-on-board-computer`; LL `scripts/test_imu.py`).
6. After **each** power cycle, calibrate the joint zero positions with `calibrate_joints.py` (LL `README.md:46-58`).
   - Each joint has only one encoder on the motor shaft, so the joint zero is lost at power-off.
   - You move each joint by hand to its mechanical limit. Then you press the stop button.
   - The script saves `calibration.yaml` with offset = measured limit − expected limit angle (LL `scripts/calibrate_joints.py:29-83`).
   - The expected limit angles are fixed in the script, for example hip pitch 56.25° and ankle pitch −45° (lines 29-43).
7. Run the controller (`make run` or `run_locomotion.py`). Press LB + A, then RB + A (LL `README.md:62-74`).

- The docs have no page for joint zero calibration, first power-on, payload or mass changes (the docs-reading subagent checked all pages in D `llms.txt`).
- Some script paths differ between the docs pages and the LL repo, for example `robot/check_connection.py` against `scripts/check_connection.py`.
- The docs build the C runtime in `./csrc/` and run `./build/real_humanoid` (D `the-on-board-computer`).
  The LL `Makefile` builds `./build/main` from the repo root (LL `Makefile:3-12`).

## 6. Our plan for next week

Status of every step: **planned**.

### A. Reproduce the BHL biped policy in their setup

1. Use the PC that holds this repo: Arch-based OS (Omarchy), NVIDIA RTX 3090 with 24 GB, 62 GB RAM, 8 CPU cores, driver 610.57.
2. Before you train, check that the GPU is free. At 23:50 KST on 2026-10-08 the `sim/rl/` training used 100% of it and 17.6 GB.
3. Clone BHL at commit `984741a` in a folder outside our repo.
   Its `.gitmodules` uses SSH URLs (`git@github.com:...`). Without a GitHub SSH key, clone the LL and AS submodules over HTTPS into `source/`.
4. Install with `uv sync`, so that the versions match `pyproject.toml` (Isaac Sim 5.1.0, Isaac Lab 2.3.2.post1).
5. Connect a USB gamepad. Then run the shipped checkpoint in MuJoCo: `play_mujoco.py --config configs/policy_biped_25hz_a.yaml`.
   If the MuJoCo scene file is not found, see the note at the end of section 3.
6. Train: `uv run ./scripts/rsl_rl/train.py --task Velocity-Berkeley-Humanoid-Lite-Biped-v0 --headless`.
7. Export: `uv run ./scripts/rsl_rl/play.py --task Velocity-Berkeley-Humanoid-Lite-Biped-v0 --num_envs 16`.
8. Run our policy in MuJoCo with `configs/policy_latest.yaml`.
9. Pass criterion (our proposal): the robot walks 30 s at vx 0.25 m/s without a fall.
   It also turns at 0.6 rad/s while it walks at 0.25 m/s.

### B. Retrain with our payload

Do not edit the BHL files. Make a subclass of `BerkeleyHumanoidLiteBipedEnvCfg` in our repo and register a new task name.
Change these settings in its `__post_init__`:

| Setting | BHL value (BHL `biped/env_cfg.py`) | Our value | Why |
| --- | --- | --- | --- |
| `events.add_base_mass` `mass_distribution_params` | (−1.0, 2.0) kg, line 241 | (0.0, 3.5) kg | Covers 0 kg (bring-up), 1.54 to 2.76 kg (A_real, B_real empty and full) and a margin |
| new `events.payload_com` with `mdp.randomize_rigid_body_com`, `body_names="base"`, `mode="startup"` | none | `com_range` x (−0.06, 0.02), y (−0.01, 0.01), z (0.0, 0.12) m | The payload moves the torso CoM. See the table below |
| `commands.base_velocity.rel_standing_envs` | 0.02, line 31 | 0.2 | Our robot stands still while it aims and sprays |
| `commands.base_velocity.ranges.lin_vel_x` | (−0.5, 0.5), line 34 | keep | `aim/` uses 0.25 m/s |
| knee pitch joint limit | URDF range | knee ≤ 1.4 rad | Backpack clearance (`cad/backpack/README.md`). Set it in the training model too. **Not verified:** the exact Isaac Lab setting |
| actuator `effort_limit` | 6 Nm (AS `robots/berkeley_humanoid_lite.py:85,96`) | keep 6 Nm | Change only after we know the real motor limit (section 7) |

Torso CoM shift that I computed from the real-CAD models `sim/payload/models/bhl_*_real.xml`.
The masses match `sim/payload/README.md`, section "Round 3: A_real and B_real from the CAD parts".

| Concept | Payload mass (kg) | Shift of the `base` CoM, x / y / z (m) |
| --- | --- | --- |
| A_real, water gun on the pan-tilt | 1.54 | −0.011 / 0.000 / +0.096 |
| B_real, backpack, tank full | 2.76 | −0.045 / +0.006 / +0.048 |
| B_real, backpack, tank empty | 1.81 | −0.028 / −0.003 / +0.044 |

- Shift = payload mass × (payload CoM − base CoM) / (base mass + payload mass). Base: 3.16 kg, CoM (−0.005, 0.000, 0.638) m.
- These numbers come from the CAD masses. Update them when the CAD or `sim/payload/` changes.
- Isaac Lab applies the mass and the CoM terms independently. It scales the inertia as if the torso had uniform density. A real payload adds more inertia than that.
- When we choose one concept, a better model is a fixed `payload` link in the biped URDF.
  Then convert it to USD with AS `scripts/convert_urdf_to_usd.py`. This needs Isaac Sim.
- After training, run the policy in MuJoCo with the payload model. `sim/rl/bhl_biped_payload.xml` may serve for this.
  Compare the peak joint torques with 4, 5 and 6 Nm.

### C. Feed `vx` and `yaw_rate` from `aim/run.py` into the policy

`aim/run.py` sends the same JSON line per tick to UDP `127.0.0.1:5601` (actuator driver) and `127.0.0.1:5602` (walking bridge).
An example is `{"vx": 0.25, "yaw_rate": 0.3, ...}` (`aim/run.py:21,75-77`; port table in `aim/README.md:147-151`).

The smallest change:

1. Write a subclass of `Se2Gamepad` in our repo, for example `locomotion/aim_gamepad.py`.
2. The subclass keeps the gamepad for the mode buttons and the stop button.
3. A second thread reads our UDP JSON on port 5602. It writes `velocity_x = clip(vx, −0.5, 0.5)`, `velocity_y = 0` and `velocity_yaw = clip(yaw_rate, −1, 1)`.
4. If no packet arrives for 0.5 s, the thread writes zeros, so the robot stands still.
5. The subclass ignores the sticks for velocity. Skipped: a stick override of the `aim/` command. Add it when a person must drive the robot by hand.
6. Use it at the one place where BHL creates the command source, LL `robot/humanoid.py:69`. Do not edit that file. Replace the name from our start script:

```python
import berkeley_humanoid_lite_lowlevel.robot.humanoid as bhl_humanoid
from aim_gamepad import AimGamepad
bhl_humanoid.Se2Gamepad = AimGamepad  # Humanoid() now creates AimGamepad
# then run the same 20-line loop as LL scripts/run_locomotion.py
```

- The units already match: `aim/` gives m/s and rad/s. Positive yaw rate turns left in both `aim/controller.py:21` and the gamepad mapping.
- The same name swap works for sim-to-sim, because BHL `environments/mujoco.py:11,140` also creates `Se2Gamepad`. Test `aim/` with the policy in MuJoCo first.
- For the C runtime, the bridge would instead send the 13-byte packet of section 4.3 to port 10011. The missing policy process makes this path harder. Use the Python runtime first.

## 7. Risks and unknowns

1. **Torque margin with payload.** Training uses 6 Nm. The Python runtime limits the motors to 4 Nm (LL `robot/humanoid.py:128`).
   `sim/payload/README.md` (results, "Mass budget") finds that slow single-leg stance needs 6.0 Nm at the pitch joints with 2 kg added at the torso top.
   That result is tested in simulation (MuJoCo, static poses), not measured on board.
   We do not know the safe continuous torque of the actuator. The paper did not study heat effects on the printed parts (P, section VI).
2. **Payload outside the training range.** BHL trains with up to +2.0 kg on the torso and no CoM change.
   The real-CAD payloads are A_real 1.54 kg, B_real 2.76 kg full and 1.81 kg empty (`sim/payload/README.md`, round 3). Retrain with 0 to 3.5 kg.
3. **GPU and Isaac Sim.** Isaac Sim 5.1 lists an RTX 4080 with 16 GB as the minimum GPU (<https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html>).
   The same page lists Ubuntu 22.04 or 24.04 and a Linux driver 580.65.06 or newer.
   Our PC has an RTX 3090 with 24 GB on an Arch-based OS. NVIDIA does not list this setup. **Not verified:** that Isaac Sim runs on it. A Docker image is an option (BHL `docker/`).
4. **Version drift.** The docs use Isaac Sim 4.5.0 and Isaac Lab 2.1.0. The code pins 5.1.0 and 2.3.2.post1. Their shipped checkpoints may come from an older code version.
5. **Missing parts of the C runtime.** The policy process and `udp_joystick.py` are not in the public repos at the pinned commits.
6. **Gamepad dependence.** The Python runtime and the sim-to-sim script need a USB gamepad. Calibration also uses a gamepad button to finish.
7. **Joint zero calibration after each power cycle.** If our build changes a mechanical stop, the expected limit angles in `calibrate_joints.py:29-43` are wrong for us.
8. **No software safety stops.** No joint-limit clamp, no tilt stop, and no command timeout exist in the Python runtime. Our bridge adds the command timeout only.
9. **Hard-coded values.** The IMU port (`/dev/ttyUSB0` in Python, a PCI path in C), the visualisation address `172.28.0.5` and the CAN names are in the code.
10. **Licences.** The BHL code is MIT (BHL `LICENCE`). The assets are CC BY-SA 4.0 (AS `LICENCE`; BHL `README.md`, section License).
    CC BY-SA requires attribution. Changed versions of the assets, for example a URDF with our payload link, must use the same licence.

## 8. Sim-to-sim results with our payloads

`sim/sim2sim/README.md` runs the shipped BHL policy `policy_biped_25hz_a.onnx` on our payload models. Status: tested in simulation (MuJoCo, CPU).

- At 6 Nm, no model falls, including concept B with a full tank. At 4 Nm, B full falls within 1 s and other models fall in some walk tests.
- The shipped policy does not turn on the spot: a yaw-only command of 0.5 rad/s gives at most 0.06 rad/s.
  BHL gives the stepping reward only when the linear command is above 0.1 m/s (BHL `.../velocity/mdp/rewards.py:55-56`).
- **Handled in `aim/`:** `aim/` now always walks at 0.25 m/s or more when it turns (`aim/controller.py`, `Controller._walk` and `turn_vx`).
  The policy limit itself is unchanged. A retrained policy should also reward steps for a yaw-only command.

## 9. Not verified (summary)

- I did not run any BHL script: no training, no export, no sim-to-sim, no robot runtime.
- The MuJoCo scene path in BHL `environments/mujoco.py:40` may not match the pinned assets.
- I did not find the C-runtime policy process or `udp_joystick.py`.
- I did not check which physical gamepad button `BTN_NORTH` is.
- I did not check the motor watchdog unit or the byte order of the port-10011 packet on the robot.
- I did not check that Isaac Sim 5.1 runs on our RTX 3090 with an Arch-based OS.
- The docs and the paper do not name the training GPU.
- The C runtime sends the raw IMU angular velocity (LL `csrc/real_humanoid.cpp:159-161`). The Python runtime converts deg/s to rad/s (LL `robot/humanoid.py:185-186`). I did not check the unit that the BNO085 sketch sends.

## 10. Terms

- **Bring-up**: the first start of new robot hardware, step by step.
- **Checkpoint**: a saved policy file.
- **CoM**: centre of mass.
- **Decimation**: the number of physics steps for each policy step.
- **E-stop**: an emergency stop button that cuts motor power.
- **MLP**: a simple neural network made of fully connected layers.
- **ONNX**: a standard file format for neural networks. `onnxruntime` runs it on a normal CPU.
- **PD control**: the motor torque depends on the position error (P, gain kp) and the velocity (D, gain kd).
- **Policy**: the neural network that maps the observations to joint targets.
- **Sim-to-sim**: run a policy that you trained in one simulator (Isaac Lab) in a second simulator (MuJoCo), to check it.
- **SocketCAN**: the Linux interface for CAN buses. Each bus appears as a network device, for example `can0`.
- **TorchScript**: a PyTorch file format for a saved model.
