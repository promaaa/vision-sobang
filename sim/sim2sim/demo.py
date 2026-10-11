"""Closed-loop demo in MuJoCo: BHL policy (6 Nm) + aim/ controller + one fire on the floor, concept A.

MUJOCO_GL=egl python demo.py [MODEL FIRE_X FIRE_Y NAME]   -> results/NAME.mp4, NAME.png, NAME_log.csv
Default: bhl_A 2.5 1.5 demo. Example: bhl_A_real -2 -1.5 demo_real

aim/ is imported, not changed. The fire detector is synthetic: aim/sim_demo.fake_detections projects the fire
into the concept A camera with the MuJoCo base pose and the simulated pan-tilt angles.
"""
import csv
import math
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE.parents[1] / "aim"))
sys.path.insert(0, str(HERE))  # before aim/: aim/ also has a run.py
from ballistics import jet_path  # noqa: E402
from controller import Controller  # noqa: E402
from geometry import CONCEPTS, nozzle_exit, robot_to_world  # noqa: E402
from sim_demo import FIRE_RADIUS, fake_detections, landing_point  # noqa: E402
from run import (ACTION_SCALE, DEFAULT, KD, KP, MODELS, NOISE, PHYSICS_DT, POLICY, POLICY_DT, TILT_LIMIT,  # noqa: E402
                 observation, quat_rotate_inverse)

MODEL, FIRE_X, FIRE_Y, NAME = sys.argv[1:5] if len(sys.argv) >= 5 else ("bhl_A", 2.5, 1.5, "demo")
FIRE = np.array([float(FIRE_X), float(FIRE_Y), 0.0])  # world frame, m. Default: 2.5 m ahead, 1.5 m left of the start
LIMIT = 6.0  # Nm, training torque limit
AIM_DT = 0.1  # s, aim/ controller and detector at 10 Hz
SERVO_RATE = 3.0  # rad/s, pan and tilt follow the command with this rate limit
T_MAX = 40.0  # s
FPS, W, H = 30, 640, 480
STATES = ["SEARCH", "APPROACH", "AIM", "SPRAY", "CHECK", "DONE"]


def add_geom(scene, gtype, size, pos, rgba, mat=np.eye(3)):
    """Add one visual-only geom to the rendered scene (not to the physics)."""
    if scene.ngeom < scene.maxgeom:
        mujoco.mjv_initGeom(scene.geoms[scene.ngeom], gtype, np.asarray(size, float), np.asarray(pos, float),
                            np.asarray(mat, float).flatten(), np.asarray(rgba, np.float32))
        scene.ngeom += 1


def jet_points(cfg, pose, pan, tilt, v0, drag, z_fire):
    """World points along the jet, from the nozzle exit to the fire height (aim/ballistics.jet_path)."""
    e, d = nozzle_exit(cfg, pan, tilt)
    h = d[:2] / np.linalg.norm(d[:2])
    path = jet_path(v0, tilt, drag, z_stop=z_fire - e[2])
    return [robot_to_world(pose, (e[0] + r * h[0], e[1] + r * h[1], e[2] + z)) for r, z, _ in path[::25]]


def main():
    cfg = CONCEPTS["A"]
    cam = next(iter(cfg["cameras"]))
    ctl = Controller(cfg)
    rng_det, rng_obs = np.random.default_rng(1), np.random.default_rng(0)

    m = mujoco.MjModel.from_xml_path(str(MODELS / f"{MODEL}.xml"))
    m.opt.timestep = PHYSICS_DT
    d = mujoco.MjData(m)
    d.qpos[7:19] = DEFAULT  # BHL start: base at (0, 0, 0), upright, default joints
    mujoco.mj_forward(m, d)
    policy = ort.InferenceSession(str(POLICY), providers=["CPUExecutionProvider"])
    base = m.body("base").id

    renderer = mujoco.Renderer(m, H, W)
    camera = mujoco.MjvCamera()
    camera.type, camera.distance, camera.elevation = mujoco.mjtCamera.mjCAMERA_FREE, 3.5, -35.0
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-pix_fmt", "yuv420p", "-crf", "28", str(OUT / f"{NAME}.mp4")],
                          stdin=subprocess.PIPE)

    action = np.zeros(12, np.float32)
    cmd_vec = np.zeros(3, np.float32)
    pan = tilt = 0.0
    cmd, health, fall, cam_yaw = None, 1.0, None, 0.0
    next_aim, frame, log = 0.0, 0, []
    while d.time < T_MAX:
        quat, gyro = d.sensor("imu_quat").data.copy(), d.sensor("imu_gyro").data.copy()
        obs = observation(cmd_vec, quat, gyro, d.qpos[7:19], d.qvel[6:18], action)
        obs += (rng_obs.uniform(-1, 1, 45) * NOISE).astype(np.float32)  # training noise, as in run.py --noise
        action = policy.run(None, {"obs": obs})[0][0]
        target = DEFAULT + ACTION_SCALE * action
        for _ in range(round(POLICY_DT / PHYSICS_DT)):
            d.ctrl[:] = np.clip(KP * (target - d.qpos[7:19]) - KD * d.qvel[6:18], -LIMIT, LIMIT)
            mujoco.mj_step(m, d)
            R = d.xmat[base].reshape(3, 3)
            pose = (d.xpos[base][0], d.xpos[base][1], math.atan2(R[1, 0], R[0, 0]))

            if d.time >= next_aim:  # 10 Hz: detector, aim/ controller, kinematic pan-tilt, fire health
                next_aim += AIM_DT
                dets = fake_detections(cfg, cam, pan, tilt, pose, FIRE, d.time, rng_det) if health > 0 else []
                cmd = ctl.step(d.time, dets, pose, pan, tilt)
                cmd_vec[:] = (np.clip(cmd.vx, -0.5, 0.5), 0.0, np.clip(cmd.yaw_rate, -1.0, 1.0))  # the planned bridge
                if cmd.pump_on:
                    hit = robot_to_world(pose, landing_point(cfg, pan, tilt, ctl.cc.v0, ctl.cc.drag, FIRE[2]))
                    if np.linalg.norm(hit[:2] - FIRE[:2]) < FIRE_RADIUS + 0.1:
                        health = max(0.0, health - AIM_DT / 3.0)  # out after 3 s of water on it, as aim/sim_demo.py
                pan += np.clip(cmd.pan - pan, -SERVO_RATE * AIM_DT, SERVO_RATE * AIM_DT)
                tilt += np.clip(cmd.tilt - tilt, -SERVO_RATE * AIM_DT, SERVO_RATE * AIM_DT)
                g = quat_rotate_inverse(d.sensor("imu_quat").data, np.array([0, 0, -1.0]))
                if fall is None and np.arccos(np.clip(-g[2], -1, 1)) > TILT_LIMIT:
                    fall = d.time
                log.append(dict(t=round(d.time, 2), x=pose[0], y=pose[1], yaw=pose[2], state=cmd.state, vx_cmd=cmd.vx,
                                yaw_rate_cmd=cmd.yaw_rate, pan=pan, tilt=tilt, pump_on=cmd.pump_on, fire_health=health,
                                dist=float(np.hypot(*(FIRE[:2] - pose[:2])))))

            if d.time * FPS >= frame:  # 30 fps video, camera behind, above and 35 deg to the right of the robot
                frame += 1
                cam_yaw += 0.05 * math.remainder(pose[2] - cam_yaw, 2 * math.pi)  # smoothed heading, so the view does not shake with each step
                camera.lookat[:] = (pose[0] + 0.8 * math.cos(cam_yaw), pose[1] + 0.8 * math.sin(cam_yaw), 0.3)
                camera.azimuth = math.degrees(cam_yaw) - 35.0
                renderer.update_scene(d, camera)
                s = renderer.scene
                lit = health > 0
                add_geom(s, mujoco.mjtGeom.mjGEOM_CYLINDER, (FIRE_RADIUS, 0.005, 0), FIRE + (0, 0, 0.005),
                         (0.2, 0.2, 0.2, 1) if not lit else (1.0, 0.45, 0.0, 1))
                if lit:
                    add_geom(s, mujoco.mjtGeom.mjGEOM_SPHERE, (0.08 * (0.5 + health),) * 3, FIRE + (0, 0, 0.1), (1, 0.1, 0, 0.9))
                if cmd is not None and cmd.pump_on:
                    for p in jet_points(cfg, pose, pan, tilt, ctl.cc.v0, ctl.cc.drag, FIRE[2]):
                        add_geom(s, mujoco.mjtGeom.mjGEOM_SPHERE, (0.02,) * 3, p, (0.2, 0.5, 1.0, 0.8))
                ff.stdin.write(renderer.render().tobytes())

        if (fall is not None and d.time > fall + 2.0) or (cmd is not None and cmd.state == "DONE" and d.time > ctl.t_state + 2.0):
            break

    ff.stdin.close()
    ff.wait()
    renderer.close()
    with open(OUT / f"{NAME}_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    plot(log)
    spray = next((r["t"] for r in log if r["state"] == "SPRAY"), None)
    print(f"reached SPRAY: {spray is not None}, time to SPRAY: {spray} s, final state: {log[-1]['state']}, "
          f"fire out: {health <= 0}, final distance to fire: {log[-1]['dist']:.2f} m, fall: {fall}, sim time: {d.time:.1f} s")


def plot(log):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = np.array([r["t"] for r in log])
    xy = np.array([(r["x"], r["y"]) for r in log])
    st = np.array([STATES.index(r["state"]) for r in log])
    colors = plt.cm.tab10(np.arange(len(STATES)))
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5))
    for i, name in enumerate(STATES):
        k = st == i
        if k.any():
            a.scatter(xy[k, 0], xy[k, 1], s=8, color=colors[i], label=name)
    a.add_patch(plt.Circle(FIRE[:2], FIRE_RADIUS, color="orangered", label="fire"))
    a.plot(0, 0, "k^", label="start")
    a.set(xlabel="x (m)", ylabel="y (m)", title="Base path (MuJoCo), coloured by aim/ state", aspect="equal")
    a.legend(loc="lower right", fontsize=8)
    b.step(t, st, where="post", color="k", label="state")
    b.set_yticks(range(len(STATES)), STATES)
    b2 = b.twinx()
    b2.plot(t, [r["vx_cmd"] for r in log], label="vx command (m/s)")
    b2.plot(t, [r["yaw_rate_cmd"] for r in log], label="yaw rate command (rad/s)")
    b2.plot(t, [r["dist"] for r in log], label="distance to fire (m)")
    b2.plot(t, [r["fire_health"] for r in log], label="fire health")
    b2.legend(loc="upper right", fontsize=8)
    b.set(xlabel="time (s)", title="aim/ state and commands")
    fig.tight_layout()
    fig.savefig(OUT / f"{NAME}.png", dpi=100)


if __name__ == "__main__":
    main()
