# Firefighter Robot

A low-cost firefighter humanoid robot. The body reuses the legs and torso of the
open-source [Berkeley Humanoid Lite](https://arxiv.org/abs/2504.17249).

The goal is a robot that enters a hazardous area, finds a fire, moves toward it,
and puts it out with a mounted water nozzle or a small pump.

**Progress report with videos:** <https://promaaa.github.io/vision-sobang/>
The `gh-pages` branch of this repository holds that website. The `main` branch holds the code, the CAD and the simulations.

## Roadmap

1. Get the Berkeley-based body to move reliably.
2. Detect and localize fire with a lightweight onboard camera system (RGB, thermal, or both).
3. Estimate the fire position relative to the robot.
4. Navigate and aim toward the fire.
5. Trigger and control the extinguisher.
6. Increase autonomy and robustness step by step.

## Quick start

You need `git` and [uv](https://docs.astral.sh/uv/getting-started/installation/).
uv installs Python 3.12 and all packages by itself.
The commands are for Linux or macOS. On Windows, use WSL.

1. Clone the repository:

```bash
git clone https://github.com/promaaa/vision-sobang.git
cd vision-sobang
```

2. Fetch the Berkeley robot model (URDF, MJCF and meshes) into `third_party/`:

```bash
scripts/fetch_bhl_assets.sh
```

3. Install the environment. It goes into `.venv/`:

```bash
uv sync
```

4. Run the tests:

```bash
uv run pytest
```

Run all commands from the repository root, unless a step says `cd`.
`uv run` uses the environment of the nearest `pyproject.toml`, so you do not need to activate it.

## Run the simulations

| What | Command | Time | Output |
| --- | --- | --- | --- |
| Leg torques with each payload | `cd sim/payload && uv run python analyze.py` | 1 min | `sim/payload/results/` |
| Official Berkeley policy with each payload | `uv run python sim/sim2sim/run.py --noise` | 30 s | `sim/sim2sim/results/results_noise.md` |
| Closed loop: see, walk, aim, spray (video) | `MUJOCO_GL=egl uv run python sim/sim2sim/demo.py bhl_A_real -2 -1.5 demo_real` | 10 s | `sim/sim2sim/results/demo_real.mp4` |
| The six test scenarios | `MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --quick` | 1 min | `sim/sim2sim/results/suite_results.md` |
| The six scenarios with your fire detector | `MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --quick --detector my_detector.py` | 1 min | `sim/sim2sim/results/suite_results.md` |
| Software in the loop (real programs over UDP) | `MUJOCO_GL=egl uv run python sim/sim2sim/camera_loop.py --sil` | 2 min | `sim/sim2sim/results/sil_results.md` |
| Aiming code alone (top-view plot) | `cd aim && uv run python sim_demo.py A` | 5 s | `aim/sim_demo_A.png` |
| First-day hardware self-test, without hardware | `uv run python actuators/selftest.py --mock --yes` | 5 s | printed checks |

`MUJOCO_GL=egl` lets MuJoCo render videos without a screen on Linux. On macOS, leave it out.
Videos need `ffmpeg`.
Each simulation folder has a README with all options, the method and the limits.

### Heavier jobs

| What | Needs | Where to start |
| --- | --- | --- |
| Printable parts (STEP, STL) and their checks | `uv sync --project cad` once | `cad/parts/README.md`, `cad/backpack/README.md`, `cad/bench/README.md` |
| Concept renders, camera views, turntable videos | Blender 5.2 | `cad/README.md`, `cad/camera_views/README.md` |
| Synthetic fire images (RGB + thermal-like) | Blender 5.2 and an NVIDIA GPU, or download them | `sim/firescenes/README.md` |
| Train a walking policy | Linux, an NVIDIA GPU, `cd sim/rl && uv sync` | `sim/rl/README.md` |

## Repository map

Status words: built, tested in simulation, measured on laptop, measured on board, planned.
Each folder has a README with the method, the commands and the limits.

| Folder | What | Status |
| --- | --- | --- |
| `aim/` | From a fire detection to a water jet: fire position, aim, spray logic, UDP runtime | tested in simulation |
| `actuators/` | Drivers: ST3215 servos, Pico relay firmware, actuator node, walk bridge, first-day self-test | tested in simulation (mock mode) |
| `sim/payload/` | MuJoCo models with each payload; joint torques, balance and push tests | tested in simulation |
| `sim/sim2sim/` | The official Berkeley walking policy with our payloads; closed loop, camera-in-the-loop and software-in-the-loop scenarios | tested in simulation |
| `sim/rl/` | Our walking-policy training with a payload (MuJoCo Playground) | tested in simulation |
| `sim/firescenes/` | Synthetic fire images (RGB + thermal-like) with labels, from the robot camera | tested in simulation |
| `cad/` | Blender models and renders of the five body concepts (A to E) | planned |
| `cad/parts/` | Printable pan-tilt module for concept A, adapters for B and E (STEP, STL) | planned |
| `cad/backpack/` | Printable splash guard and concept B backpack (STEP, STL) | planned |
| `cad/bench/` | Printable table-top bench rig for the pan-tilt, water system and electronics | planned |
| `cad/camera_views/` | What each robot camera sees, and fire size in pixels per sensor | tested in simulation |
| `cad/turntable/` | Turntable videos of concept A and the bench rig | planned |
| `docs/architecture.md` | How the software parts connect (ports, messages) | planned |
| `docs/hardware/` | Parts list with prices and links, wiring, water-jet estimate, camera comparison | planned |
| `docs/locomotion/` | How the Berkeley team trains and deploys its policy; our plan | planned |
| `docs/site/` | Sources of the progress website | built |
| `scripts/` | `fetch_bhl_assets.sh`: downloads the Berkeley assets at a fixed commit | built |

Simulation outputs (tables, plots, videos, logs) go to a `results/` folder next to the script.
Commit them when the numbers change, so that the READMEs and the website stay true.
Some files change on every run without a real change: STEP files hold a time stamp, and the software-in-the-loop logs depend on timing.
To drop such changes, run `git restore <file>`.

## Python environments

| Environment | Folder of `pyproject.toml` | Install | Used by |
| --- | --- | --- | --- |
| Main | repository root | `uv sync` | `aim/`, `actuators/`, `sim/payload/`, `sim/sim2sim/`, `sim/firescenes/validate.py` |
| CAD | `cad/` | `uv sync --project cad` | `cad/parts/`, `cad/backpack/`, `cad/bench/` (build123d) |
| Training | `sim/rl/` | `cd sim/rl && uv sync` | `sim/rl/` (JAX with CUDA, Linux only) |

The Blender scripts use the Python inside Blender, not these environments.
To add a package to the main environment, run `uv add <package>` and commit `pyproject.toml` and `uv.lock`.

## Licences

- Berkeley Humanoid Lite assets (fetched into `third_party/`): CC BY-SA 4.0. Renders that show the robot must credit the Berkeley Humanoid Lite team and use the same licence.
- `sim/sim2sim/policy_biped_25hz_a.onnx` comes from the Berkeley Humanoid Lite repository, MIT licence (`sim/sim2sim/BHL_LICENCE`).

## Reference

```bibtex
@inproceedings{chi2025berkeleyhumanoidlite,
  author    = {Yufeng Chi and Qiayuan Liao and Junfeng Long and Xiaoyu Huang and Sophia Shao and Borivoje Nikolic and Zhongyu Li and Koushil Sreenath},
  title     = {Demonstrating Berkeley Humanoid Lite: An Open-source, Accessible, and Customizable 3D-printed Humanoid Robot},
  booktitle = {Proceedings of Robotics: Science and Systems},
  year      = {2025},
  doi       = {10.15607/RSS.2025.XXI.062}
}
```
