"""Camera-in-the-loop tests: BHL policy (6 Nm) + rendered robot camera + a pluggable fire detector + aim/ controller.

MUJOCO_GL=egl python camera_loop.py [--scenario NAME] [--detector FILE] [--out NAME]   one scenario, with video
MUJOCO_GL=egl python camera_loop.py --suite [--detector FILE]    all scenarios, video of two_fires only
MUJOCO_GL=egl python camera_loop.py --quick [--detector FILE]    all scenarios in parallel, no video
MUJOCO_GL=egl python camera_loop.py --sil [--detector FILE]      software in the loop: ahead and two_fires, with
    aim/run.py and actuators/actuator_node.py --mock as separate processes over UDP, compared with the in-process runs

The detector module must define detect(rgb, t) -> list[FireDetection] (see README.md). Default: baseline_detector.py.
Outputs go to results/. A single run writes NAME.mp4 (third-person view + robot camera inset), NAME_log.csv and scene_A_real.xml.
The suite writes suite_results.md.
"""
import argparse
import csv
import importlib.util
import json
import math
import multiprocessing as mp
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "aim"))
sys.path.insert(0, str(HERE))  # before aim/: aim/ also has a run.py
from ballistics import jet_path  # noqa: E402
from controller import Controller  # noqa: E402
from geometry import CONCEPTS  # noqa: E402
from run import (ACTION_SCALE, DEFAULT, KD, KP, MODELS, NOISE, PHYSICS_DT, POLICY, POLICY_DT, TILT_LIMIT,  # noqa: E402
                 observation, quat_rotate_inverse)

CFG = CONCEPTS["A"]
CAM = CFG["cameras"]["rgb"]
LIMIT = 6.0  # Nm
AIM_DT = 0.1  # s, camera, detector and aim/ controller at 10 Hz
SERVO_RATE = 3.0  # rad/s, pan-tilt speed limit
FIRE_RADIUS = 0.15  # m
HIT = FIRE_RADIUS + 0.1  # m, the jet puts a fire out when it lands this close for 3 s in total
STRAY = 0.5  # m, a spray that lands farther than this from every fire is a stray spray
RED_BOX = (1.8, -0.9, 0.2)  # distractor: red box, centre
LAMP = (3.9, 0.6, 1.6)  # distractor: warm lamp on a pole, bulb centre
ROOM = 7.0  # m, walls at x, y = +-ROOM
FPS, W, H = 30, 640, 480
FOVY = math.degrees(2 * math.atan(math.tan(math.radians(45)) * H / W))  # 90 deg HFOV at 640 x 480
F_PX = (H / 2) / math.tan(math.radians(FOVY) / 2)  # focal length in pixels (= aim/ K.fx)

# fires: world (x, y) on the floor, m. The robot starts at (0, 0) and faces +x.
# limit: all fires must be out by this time, s. The run then continues until DONE, at most `limit` + 30 s.
SCENARIOS = {
    "ahead": dict(fires=[(2.5, 0.0)], box=True, lamp=True, limit=40.0),
    "behind_right": dict(fires=[(-2.0, -1.5)], box=True, lamp=True, limit=50.0),
    "two_fires": dict(fires=[(2.5, 1.5), (-1.0, -2.5)], box=True, lamp=True, limit=90.0),
    "lamp_only": dict(fires=[], box=False, lamp=True, limit=10.0),
    "too_close": dict(fires=[(0.5, 0.0)], box=True, lamp=True, limit=50.0, back_first=True),
    "far": dict(fires=[(6.0, 0.0)], box=True, lamp=True, limit=70.0),
}


def build_scene(sc):
    """MJCF text: bhl_A_real.xml with a pan and a tilt joint, the robot camera, a room, the fires and distractors."""
    root = ET.parse(MODELS / "bhl_A_real.xml").getroot()
    root.find("compiler").set("meshdir", str((MODELS / root.find("compiler").get("meshdir")).resolve()))
    ET.SubElement(root, "visual").append(ET.Element("headlight", ambient="0.25 0.25 0.25", diffuse="0.4 0.4 0.4"))
    asset = root.find("asset")
    ET.SubElement(asset, "texture", name="grid", type="2d", builtin="checker", width="512", height="512", rgb1="0.55 0.55 0.52", rgb2="0.45 0.45 0.43")
    ET.SubElement(asset, "material", name="floor", texture="grid", texrepeat="12 12", reflectance="0.05")
    ET.SubElement(asset, "material", name="flame_outer", rgba="1 0.45 0.05 0.9", emission="1")
    ET.SubElement(asset, "material", name="flame_inner", rgba="1 0.85 0.2 0.95", emission="1")
    ET.SubElement(asset, "material", name="bulb", rgba="1 0.65 0.25 1", emission="0.8")  # warm bulb: looks like fire to a colour threshold
    world = root.find("worldbody")
    floor = world.find("geom[@name='floor']")
    floor.attrib.pop("rgba", None)
    floor.set("material", "floor")
    for name, pos, size in [("wall_n", f"0 {ROOM} 0.75", f"{ROOM} 0.05 0.75"), ("wall_s", f"0 {-ROOM} 0.75", f"{ROOM} 0.05 0.75"),
                            ("wall_e", f"{ROOM} 0 0.75", f"0.05 {ROOM} 0.75"), ("wall_w", f"{-ROOM} 0 0.75", f"0.05 {ROOM} 0.75")]:
        ET.SubElement(world, "geom", name=name, type="box", pos=pos, size=size, rgba="0.75 0.73 0.68 1")
    for i, (x, y) in enumerate(sc["fires"]):  # visual only: rgba is set on the geom, so the flicker can change it
        ET.SubElement(world, "geom", name=f"fire{i}_base", type="cylinder", pos=f"{x} {y} 0.005", size=f"{FIRE_RADIUS} 0.005", rgba="0.15 0.12 0.1 1", contype="0", conaffinity="0")
        ET.SubElement(world, "geom", name=f"fire{i}_outer", type="ellipsoid", pos=f"{x} {y} 0.12", size="0.12 0.12 0.12", material="flame_outer", rgba="1 0.45 0.05 0.9", contype="0", conaffinity="0")
        ET.SubElement(world, "geom", name=f"fire{i}_inner", type="ellipsoid", pos=f"{x} {y} 0.09", size="0.07 0.07 0.08", material="flame_inner", rgba="1 0.85 0.2 0.95", contype="0", conaffinity="0")
    if sc["box"]:
        ET.SubElement(world, "geom", name="red_box", type="box", pos=" ".join(map(str, RED_BOX)), size="0.2 0.2 0.2", rgba="0.75 0.08 0.06 1")
    if sc["lamp"]:
        ET.SubElement(world, "geom", name="lamp_pole", type="cylinder", pos=f"{LAMP[0]} {LAMP[1]} {LAMP[2] / 2}", size=f"0.02 {LAMP[2] / 2}", rgba="0.2 0.2 0.2 1", contype="0", conaffinity="0")
        ET.SubElement(world, "geom", name="lamp_bulb", type="sphere", pos=" ".join(map(str, LAMP)), size="0.1", material="bulb", contype="0", conaffinity="0")
        ET.SubElement(world, "light", pos=f"{LAMP[0] - 0.2} {LAMP[1]} {LAMP[2]}", dir="-1 0 -0.6", diffuse="0.6 0.5 0.35", attenuation="1 0.2 0")

    base = world.find("body[@name='base']")
    gun = base.find("body[@name='payload_gun_with_water']")
    base.remove(gun)
    px, py, pz = CFG["pivot"]
    pan = ET.SubElement(base, "body", name="pan", pos=f"{px} {py} {pz}")
    ET.SubElement(pan, "inertial", pos="0 0 0", mass="0.05", diaginertia="2e-5 2e-5 2e-5")
    ET.SubElement(pan, "joint", name="pan", type="hinge", axis="0 0 1", range="-1.5708 1.5708", damping="0.5", armature="0.01", frictionloss="0")
    ET.SubElement(pan, "geom", type="cylinder", size="0.03 0.01", rgba="0.2 0.2 0.2 1", contype="0", conaffinity="0", mass="0")
    tilt = ET.SubElement(pan, "body", name="tilt")
    ET.SubElement(tilt, "joint", name="tilt", type="hinge", axis="0 -1 0", range="-0.7854 0.5236", damping="0.5", armature="0.01", frictionloss="0")
    gpos = [float(v) for v in gun.get("pos").split()]
    gun.set("pos", f"{gpos[0] - px} {gpos[1] - py} {gpos[2] - pz}")  # same place, now in the tilt frame
    gun.find("geom").set("rgba", "0.25 0.25 0.28 1")  # dark grey, so the gun is not orange in its own camera
    tilt.append(gun)
    nx, ny, nz = CFG["nozzle"]
    ET.SubElement(tilt, "geom", type="capsule", fromto=f"0.1 0 {nz} {nx} {ny} {nz}", size="0.012", rgba="0.25 0.25 0.28 1", contype="0", conaffinity="0", mass="0")
    ET.SubElement(tilt, "site", name="nozzle", pos=f"{nx} {ny} {nz}")
    p = CAM["pitch"]
    ET.SubElement(tilt, "camera", name="rgb", pos=" ".join(map(str, CAM["pos"])), fovy=f"{FOVY:.3f}",
                  xyaxes=f"0 -1 0 {-math.sin(p):.4f} 0 {math.cos(p):.4f}")  # looks along +x, pitched down by -pitch
    act = root.find("actuator")
    for j, lo, hi in (("pan", -1.5708, 1.5708), ("tilt", -0.7854, 0.5236)):
        ET.SubElement(act, "position", name=j, joint=j, kp="20", kv="1", ctrlrange=f"{lo} {hi}")
    key = root.find("keyframe/key")  # the keyframe needs the two new joints
    key.set("qpos", key.get("qpos") + " 0 0")
    return ET.tostring(root, encoding="unicode")


def project_world(d, cam_id, p):
    """World point -> pixel (u, v) in the MuJoCo camera, or None behind it."""
    pc = d.cam_xmat[cam_id].reshape(3, 3).T @ (np.asarray(p) - d.cam_xpos[cam_id])
    if pc[2] > -1e-3:
        return None
    return W / 2 + F_PX * pc[0] / -pc[2], H / 2 - F_PX * pc[1] / -pc[2]


def classify(dets, d, cam_id, objects):
    """Label each detection with the object whose projected centre is nearest (fire i, red_box, lamp or none)."""
    labels = []
    for det in dets:
        u0, v0, u1, v1 = det.bbox
        best, best_d = "none", 60.0
        for name, p in objects.items():
            uv = project_world(d, cam_id, p)
            if uv is None:
                continue
            inside = u0 - 10 <= uv[0] <= u1 + 10 and v0 - 10 <= uv[1] <= v1 + 10
            dist = 0.0 if inside else math.hypot(uv[0] - (u0 + u1) / 2, uv[1] - (v0 + v1) / 2)
            if dist < best_d:
                best, best_d = name, dist
        labels.append(best)
    return labels


def landing(d, m, v0, drag):
    """Where the jet from the MuJoCo nozzle (true pose, with torso tilt) reaches the floor, world x, y."""
    p0 = d.site_xpos[m.site("nozzle").id]
    ax = d.xmat[m.body("tilt").id].reshape(3, 3)[:, 0]
    hor = ax[:2] / max(np.linalg.norm(ax[:2]), 1e-9)
    elev = math.asin(np.clip(ax[2], -1, 1))
    path = jet_path(v0, elev, drag, z_stop=-p0[2])
    return p0[:2] + path[-1][0] * hor, [(p0[0] + r * hor[0], p0[1] + r * hor[1], p0[2] + z) for r, z, _ in path[::25]]


def draw_box(img, box, color, w=3):
    u0, v0, u1, v1 = [int(round(c)) for c in box]
    u0, u1 = np.clip([u0, u1], 0, img.shape[1] - 1)
    v0, v1 = np.clip([v0, v1], 0, img.shape[0] - 1)
    img[v0:v0 + w, u0:u1 + 1] = img[max(v1 - w + 1, 0):v1 + 1, u0:u1 + 1] = color
    img[v0:v1 + 1, u0:u0 + w] = img[v0:v1 + 1, max(u1 - w + 1, 0):u1 + 1] = color


def add_sphere(scene, pos, r, rgba):
    if scene.ngeom < scene.maxgeom:
        mujoco.mjv_initGeom(scene.geoms[scene.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE, np.array([r, r, r]),
                            np.asarray(pos, float), np.eye(3).flatten(), np.asarray(rgba, np.float32))
        scene.ngeom += 1


ROOT = HERE.parents[1]
OUT = HERE / "results"  # videos, logs and result tables
OUT.mkdir(exist_ok=True)
DET_PORT, WALK_PORT, FEEDBACK_PORT, POSE_PORT = 5600, 5602, 5604, 5605  # 5601 and 5603 connect aim/run.py and the actuator node directly


class SilLink:
    """The robot programs as separate processes over UDP, as on the robot. The simulator replaces camera, legs and servos.

    camera_loop --5600 detections--> aim/run.py A --feedback --5601--> actuators/actuator_node.py --mock --5603--> aim/run.py
    aim/run.py --5602--> walk_bridge.AimGamepad (here) -> policy command.  actuator node --5604 angles, water--> here.
    here --5605 base pose at 25 Hz--> aim/run.py (pose=False: no pose, aim/run.py dead-reckons the walk command).
    """

    def __init__(self, stem, pose=True):
        self.pose_on = pose
        sys.path.insert(0, str(ROOT / "actuators"))
        from walk_bridge import AimGamepad
        self.walk = AimGamepad(port=WALK_PORT)  # the robot code path for the walk command (clip, 0.5 s timeout)
        self.walk.start_udp()
        self.fb_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fb_rx.bind(("127.0.0.1", FEEDBACK_PORT))
        self.fb_rx.setblocking(False)
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.node_err = open(OUT / f"{stem}_node.log", "w")
        self.aim_err = open(OUT / f"{stem}_aim_stderr.log", "w")
        self.node = subprocess.Popen([sys.executable, "-u", "actuators/actuator_node.py", "--mock"],
                                     cwd=ROOT, stdout=subprocess.DEVNULL, stderr=self.node_err)
        time.sleep(0.5)  # the node binds 5601 before aim/run.py sends
        self.aim = subprocess.Popen([sys.executable, "-u", "aim/run.py", "A", "--feedback"],
                                    cwd=ROOT, stdout=subprocess.PIPE, stderr=self.aim_err, text=True)
        self.cmd, self.cmd_times, self.fb, self.fb_times = {}, [], None, []
        self.walk_ages, self.fb_ages, self.sent, self.sent_times = [], [], 0, []
        threading.Thread(target=self._read_aim, daemon=True).start()
        time.sleep(0.5)

    def _read_aim(self):  # aim/run.py prints each command line on stdout too: the state for the log
        for line in self.aim.stdout:
            try:
                self.cmd = json.loads(line)
                self.cmd_times.append(time.monotonic())
            except ValueError:
                pass

    def send(self, dets, t_img):
        """Interface v2 (aim/README.md): one frame message per image, with an empty list when there is no fire."""
        msg = dict(timestamp=t_img, camera="rgb", frame=True, detections=[asdict(x) for x in dets])
        self.tx.sendto(json.dumps(msg, default=float).encode(), ("127.0.0.1", DET_PORT))
        self.sent += 1
        self.sent_times.append(time.monotonic())

    def send_pose(self, x, y, R):
        """Base pose from the MuJoCo torso rotation R (3 x 3). Z-Y-X angles, rad: yaw about z (left +),
        pitch about y (nose down +), roll about x (left side up +)."""
        if self.pose_on:
            yaw, pitch, roll = math.atan2(R[1, 0], R[0, 0]), math.asin(-np.clip(R[2, 0], -1, 1)), math.atan2(R[2, 1], R[2, 2])
            msg = dict(timestamp=time.monotonic(), x=float(x), y=float(y), yaw=yaw, roll=roll, pitch=pitch)
            self.tx.sendto(json.dumps(msg).encode(), ("127.0.0.1", POSE_PORT))

    def step(self, now):
        """Latest actuator state and walk command, as a command-like object."""
        while True:
            try:
                self.fb = json.loads(self.fb_rx.recv(65536))
                self.fb_times.append(time.monotonic())
            except BlockingIOError:
                break
        fb = self.fb or dict(t=now, pan=0.0, tilt=0.0, water=False)
        self.fb_ages.append(now - fb["t"])
        if self.cmd_times and self.aim.poll() is None:  # only while aim/run.py sends: it stops at DONE
            self.walk_ages.append((now, now - self.walk._t))
        c = self.walk.commands
        return SimpleNamespace(state=self.cmd.get("state", "START"), pump_on=bool(fb["water"]), vx=c["velocity_x"],
                               yaw_rate=c["velocity_yaw"], pan=fb["pan"], tilt=fb["tilt"])

    def close(self, wall_lag):
        for p in (self.aim, self.node):
            if p.poll() is None:
                p.terminate()
            p.wait()
        self.walk.stop()
        time.sleep(0.1)
        self.walk.sock.close()
        self.fb_rx.close()
        self.node_err.close()
        self.aim_err.close()
        gaps = np.diff(self.cmd_times) if len(self.cmd_times) > 1 else np.zeros(1)
        fb_gaps = np.diff(self.fb_times) if len(self.fb_times) > 1 else np.zeros(1)
        # run.py ticks (one command line each) against detection datagrams: how many datagrams each tick read.
        # Count only ticks while the camera sends (a datagram less than 0.3 s before the tick).
        st, ct = np.array(self.sent_times), np.array(self.cmd_times)
        per_tick = np.histogram(st, bins=ct)[0] if len(ct) > 1 else np.zeros(0)
        active = np.array([np.any((st < c) & (st > c - 0.3)) for c in ct[1:]]) if len(ct) > 1 else np.zeros(0, bool)
        with open(self.aim_err.name) as f:
            err = f.read()
        bad = err.count("bad detection") + err.count("bad pose")
        return dict(det_datagrams=self.sent, bad_detections=bad, commands=len(self.cmd_times), dead_reckoning=err.count("dead reckoning"),
                    ticks_active=int(active.sum()), ticks_no_det=int(((per_tick == 0) & active).sum()),
                    ticks_two_dets=int(((per_tick >= 2) & active).sum()),
                    cmd_gap_max=round(float(gaps.max()), 3), cmd_gaps_over_150ms=int((gaps > 0.15).sum()),
                    walk_age_max=round(max(a for _, a in self.walk_ages), 3) if self.walk_ages else None,
                    walk_timeouts=sum(a >= 0.5 for _, a in self.walk_ages), feedback=len(self.fb_times),
                    fb_gap_max=round(float(fb_gaps.max()), 3), fb_age_max=round(max(self.fb_ages), 3), sim_lag_max=round(wall_lag, 3))


def load_detector(path):
    spec = importlib.util.spec_from_file_location("detector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.detect


def run(name, detector_path, out=None, crf=28, video=True, sil=False, pose=True):
    """Run one scenario. out: file stem for NAME.mp4 and NAME_log.csv, or None for no video and no log.
    sil: the robot programs run as separate processes over UDP (SilLink), in real time."""
    sc = SCENARIOS[name]
    fires = sc["fires"]
    detect = load_detector(detector_path)
    xml = build_scene(sc)
    if out:
        (OUT / "scene_A_real.xml").write_text(xml)
    m = mujoco.MjModel.from_xml_string(xml)
    m.opt.timestep = PHYSICS_DT
    d = mujoco.MjData(m)
    d.qpos[7:19] = DEFAULT  # BHL start: base at (0, 0, 0), upright, default joints
    mujoco.mj_forward(m, d)
    legs = list(range(12))  # leg actuators come first, then pan and tilt
    jpan, jtilt = m.joint("pan").qposadr[0], m.joint("tilt").qposadr[0]
    cam_id, base = m.camera("rgb").id, m.body("base").id
    flames = [[m.geom(f"fire{i}_{k}").id for k in ("outer", "inner")] for i in range(len(fires))]
    size0, rgba0 = m.geom_size.copy(), m.geom_rgba.copy()
    objects = {f"fire{i}": (x, y, 0.1) for i, (x, y) in enumerate(fires)}
    if sc["box"]:
        objects["red_box"] = RED_BOX
    if sc["lamp"]:
        objects["lamp"] = LAMP

    policy = ort.InferenceSession(str(POLICY), providers=["CPUExecutionProvider"])
    ctl = Controller(CFG)
    rng, rng_flicker = np.random.default_rng(0), np.random.default_rng(1)  # separate, so a video run equals a quick run
    robot_view = mujoco.Renderer(m, H, W)
    video = bool(out) and video
    if video:
        view = mujoco.Renderer(m, H, W)
        tp_cam = mujoco.MjvCamera()
        tp_cam.type, tp_cam.distance, tp_cam.elevation = mujoco.mjtCamera.mjCAMERA_FREE, 3.5, -30.0
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-pix_fmt", "yuv420p", "-crf", str(crf), str(OUT / f"{out}.mp4")], stdin=subprocess.PIPE)

    action, cmd_vec = np.zeros(12, np.float32), np.zeros(3, np.float32)
    pan_ref = tilt_ref = 0.0
    cmd, fall, cam_yaw, next_aim, frame, t_done = None, None, 0.0, 0.0, 0, None
    link = SilLink(out or f"sil_{name}", pose) if sil else None
    wall0, wall_lag = time.monotonic(), 0.0
    health, t_out = [1.0] * len(fires), [None] * len(fires)
    pip = np.zeros((H // 3, W // 3, 3), np.uint8)
    jet, log, counts = [], [], {}
    t_max = sc["limit"] + 30.0
    while d.time < t_max:
        quat, gyro = d.sensor("imu_quat").data.copy(), d.sensor("imu_gyro").data.copy()
        obs = observation(cmd_vec, quat, gyro, d.qpos[7:19], d.qvel[6:18], action)
        obs += (rng.uniform(-1, 1, 45) * NOISE).astype(np.float32)  # training noise, as run.py --noise
        action = policy.run(None, {"obs": obs})[0][0]
        target = DEFAULT + ACTION_SCALE * action
        if sil:  # real time: the other programs use time.monotonic()
            lag = time.monotonic() - (wall0 + d.time)
            if lag < 0:
                time.sleep(-lag)
            wall_lag = max(wall_lag, lag)
            R = d.xmat[base].reshape(3, 3)
            link.send_pose(d.xpos[base][0], d.xpos[base][1], R)  # 25 Hz, like odometry + IMU
        for _ in range(round(POLICY_DT / PHYSICS_DT)):
            d.ctrl[legs] = np.clip(KP * (target - d.qpos[7:19]) - KD * d.qvel[6:18], -LIMIT, LIMIT)
            mujoco.mj_step(m, d)

            if d.time >= next_aim:  # 10 Hz: render the robot camera, detect, aim/ controller
                next_aim += AIM_DT
                R = d.xmat[base].reshape(3, 3)
                pose = (d.xpos[base][0], d.xpos[base][1], math.atan2(R[1, 0], R[0, 0]))
                pan, tilt = d.qpos[jpan], d.qpos[jtilt]
                for i, ids in enumerate(flames):  # flicker, 10 Hz: the detector sees a new flame shape in each image
                    if health[i] > 0:
                        m.geom_size[ids] = size0[ids] * np.array([1, 1, 1 + 0.15 * rng_flicker.standard_normal()])
                        m.geom_rgba[ids, 1] = np.clip(rgba0[ids, 1] * (1 + 0.1 * rng_flicker.standard_normal()), 0, 1)
                robot_view.update_scene(d, camera="rgb")
                rgb = robot_view.render()
                t_img = time.monotonic() if sil else d.time
                dets = detect(rgb, t_img)
                labels = classify(dets, d, cam_id, {k: p for k, p in objects.items() if not k.startswith("fire") or health[int(k[4:])] > 0})
                for lab in labels:
                    counts[lab] = counts.get(lab, 0) + 1
                if sil:  # over UDP: detections out; servo angles, water and walk command in
                    link.send(dets, t_img)
                    cmd = link.step(time.monotonic())
                    pan_ref, tilt_ref = cmd.pan, cmd.tilt  # the node's servo angles (it limits the speed)
                else:
                    cmd = ctl.step(d.time, dets, pose, pan, tilt)
                    pan_ref += np.clip(cmd.pan - pan_ref, -SERVO_RATE * AIM_DT, SERVO_RATE * AIM_DT)
                    tilt_ref += np.clip(cmd.tilt - tilt_ref, -SERVO_RATE * AIM_DT, SERVO_RATE * AIM_DT)
                cmd_vec[:] = (np.clip(cmd.vx, -0.5, 0.5), 0.0, np.clip(cmd.yaw_rate, -1.0, 1.0))
                d.ctrl[12], d.ctrl[13] = np.clip(pan_ref, -1.5708, 1.5708), np.clip(tilt_ref, -0.7854, 0.5236)
                if cmd.state == "DONE" and t_done is None:
                    t_done = d.time
                land, jet = landing(d, m, ctl.cc.v0, ctl.cc.drag) if cmd.pump_on else (None, [])
                errs = [math.hypot(land[0] - x, land[1] - y) if land is not None else math.nan for x, y in fires]
                for i, e in enumerate(errs):
                    if health[i] > 0 and e < HIT:
                        health[i] = max(0.0, health[i] - AIM_DT / 3.0)  # out after 3 s of water, as aim/sim_demo.py
                        if health[i] == 0:
                            t_out[i] = d.time
                            m.geom_rgba[flames[i], 3] = 0.0  # extinguished: the flames disappear
                pic = rgb.copy()
                for det, lab in zip(dets, labels):
                    draw_box(pic, det.bbox, (0, 255, 0) if lab.startswith("fire") else (255, 0, 0))
                pip = pic[::3, ::3]
                g = quat_rotate_inverse(d.sensor("imu_quat").data, np.array([0, 0, -1.0]))
                if fall is None and math.acos(np.clip(-g[2], -1, 1)) > TILT_LIMIT:
                    fall = d.time
                log.append(dict(t=round(d.time, 2), state=cmd.state, x=round(pose[0], 3), y=round(pose[1], 3), yaw=round(pose[2], 3),
                                roll=round(math.atan2(R[2, 1], R[2, 2]), 3), pitch=round(math.asin(-np.clip(R[2, 0], -1, 1)), 3),
                                vx_cmd=cmd.vx, yaw_rate_cmd=cmd.yaw_rate, pan_cmd=round(cmd.pan, 3), tilt_cmd=round(cmd.tilt, 3),
                                pan=round(pan, 3), tilt=round(tilt, 3), pump_on=cmd.pump_on, detections=len(dets),
                                labels=" ".join(labels), land_x=None if land is None else round(land[0], 3),
                                land_y=None if land is None else round(land[1], 3),
                                land_err=None if land is None else round(min(errs, default=math.inf), 3),
                                **{f"health_fire{i}": round(h, 2) for i, h in enumerate(health)}))

            if video and d.time * FPS >= frame:  # 30 fps third-person view with the robot camera inset
                frame += 1
                R = d.xmat[base].reshape(3, 3)
                cam_yaw += 0.05 * math.remainder(math.atan2(R[1, 0], R[0, 0]) - cam_yaw, 2 * math.pi)
                tp_cam.lookat[:] = (d.xpos[base][0] + 0.8 * math.cos(cam_yaw), d.xpos[base][1] + 0.8 * math.sin(cam_yaw), 0.3)
                tp_cam.azimuth = math.degrees(cam_yaw) - 35.0
                view.update_scene(d, tp_cam)
                for p in jet:
                    add_sphere(view.scene, p, 0.02, (0.2, 0.5, 1.0, 0.8))
                img = view.render().copy()
                img[4:4 + pip.shape[0], W - 4 - pip.shape[1]:W - 4] = pip
                ff.stdin.write(img.tobytes())

        if (fall is not None and d.time > fall + 2.0) or (t_done is not None and d.time > t_done + 1.0):
            break

    robot_view.close()
    if video:
        ff.stdin.close()
        ff.wait()
        view.close()
    if out:
        with open(OUT / f"{out}_log.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(log[0]))
            w.writeheader()
            w.writerows(log)
    r = result(name, sc, log, counts, fall, t_out, d.time)
    if sil:
        r["sil"] = link.close(wall_lag)
    return r


def result(name, sc, log, counts, fall, t_out, t_end):
    """Metrics and PASS/FAIL for one scenario."""
    first_spray = next((r["t"] for r in log if r["state"] == "SPRAY"), None)
    pump = [r for r in log if r["pump_on"]]
    stray = sum(1 for r in pump if r["land_err"] is None or r["land_err"] > STRAY)
    errs = [r["land_err"] for r in pump if r["land_err"] is not None and r["land_err"] <= STRAY]
    back_first = any(r["vx_cmd"] < 0 for r in log if first_spray is None or r["t"] < first_spray)
    out_ok = all(t is not None and t <= sc["limit"] for t in t_out)
    done = log[-1]["state"] == "DONE"
    checks = {"fires out in time": out_ok, "no stray spray": stray == 0, "no fall": fall is None, "reached DONE": done}
    if sc.get("back_first"):
        checks["stepped back before spraying"] = back_first
    false_dets = sum(v for k, v in counts.items() if not k.startswith("fire"))
    return dict(name=name, passed=all(checks.values()), failed=[k for k, v in checks.items() if not v],
                first_spray=first_spray, t_out=t_out, done_at=round(t_end, 1), stray=stray, fall=fall,
                err=round(float(np.mean(errs)), 3) if errs else None, fire_dets=sum(v for k, v in counts.items() if k.startswith("fire")),
                false_dets=false_dets, counts=counts)


def row(r):
    t_out = ", ".join("-" if t is None else f"{t:.1f}" for t in r["t_out"]) or "no fire"
    verdict = "**PASS**" if r["passed"] else "**FAIL**: " + ", ".join(r["failed"])
    f = lambda x: "-" if x is None else x
    return (f"| {r['name']} | {verdict} | {f(r['first_spray'])} | {t_out} | {f(r['err'])} | {r['stray']} | "
            f"{r['fire_dets']} | {r['false_dets']} | {f(r['fall'])} | {r['done_at']} |")


HEADER = ("| Scenario | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples | "
          "Detections on fires | False detections | Fall (s) | End (s) |\n|---|---|---|---|---|---|---|---|---|---|")


def suite(detector, quick):
    names = list(SCENARIOS)
    if quick:  # parallel, no video: separate processes, so each one has its own EGL context
        with mp.get_context("spawn").Pool(3) as pool:
            results = pool.starmap(run, [(n, detector) for n in names])
    else:
        results = [run(n, detector, out="suite_two_fires" if n == "two_fires" else None, crf=32) for n in names]
    text = f"Detector: `{Path(detector).name}`\n\n{HEADER}\n" + "\n".join(row(r) for r in results) + "\n"
    (OUT / "suite_results.md").write_text(text)
    print(text)
    for r in results:
        print(r["name"], "detections by object:", r["counts"])
    return all(r["passed"] for r in results)


def sil_compare(detector, names=("ahead", "two_fires"), repeat=1, pose=True):
    """The scenarios in-process once and over UDP with the real programs `repeat` times. Writes sil_results[_no_pose].md."""
    tag = "" if pose else "_no_pose"
    rows, timing = [], []
    for item in names:  # "name" or "name:runs"
        n, reps = (item.split(":")[0], int(item.split(":")[1])) if ":" in item else (item, repeat)
        runs = [("in-process", run(n, detector))]
        runs += [(f"SIL {k + 1}{' no pose' if not pose else ''}", run(n, detector, out=f"sil_{n}{tag}_{k + 1}", video=False, sil=True, pose=pose))
                 for k in range(reps)]
        for mode, r in runs:
            out = ", ".join("-" if t is None else f"{t:.1f}" for t in r["t_out"])
            rows.append(f"| {n} | {mode} | {'PASS' if r['passed'] else 'FAIL: ' + ', '.join(r['failed'])} | {r['first_spray']} | {out} | "
                        f"{r['err']} | {r['stray']} | {r['fall'] or '-'} | {r['done_at']} |")
            s = r.get("sil")
            if s:
                timing.append(f"| {n} | {mode} | {s['det_datagrams']} | {s['bad_detections']} | {s['ticks_active']} | {s['ticks_no_det']} | "
                              f"{s['ticks_two_dets']} | {s['cmd_gap_max']} | {s['walk_timeouts']} | {s['fb_gap_max']} | {s['sim_lag_max']} | "
                              f"{s['dead_reckoning']} |")
            print(rows[-1], flush=True)
    text = (f"Detector: `{Path(detector).name}`. Pose on UDP 5605: {'yes' if pose else 'no'}. Frame messages: interface v2.\n\n"
            "| Scenario | Mode | Result | First SPRAY (s) | Fire out (s) | Mean landing error (m) | Stray spray samples | Fall (s) | End (s) |\n"
            "|---|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) +
            "\n\n| Scenario | Run | Frame messages sent | Rejected by run.py | run.py ticks while the camera sends | ... with no new frame | "
            "... with 2 frames | Largest command gap (s) | Walk timeouts | Largest feedback gap (s) | Largest simulator lag (s) | "
            "run.py dead-reckoning messages (1 = only at the start, before the first pose) |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n" + "\n".join(timing) + "\n")
    (OUT / f"sil_results{tag}.md").write_text(text)
    print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", default=str(HERE / "baseline_detector.py"), help="module file with detect(rgb, t)")
    ap.add_argument("--scenario", default="two_fires", choices=list(SCENARIOS))
    ap.add_argument("--out", default="camera_loop")
    ap.add_argument("--suite", action="store_true", help="run all scenarios, with a video of two_fires")
    ap.add_argument("--quick", action="store_true", help="run all scenarios in parallel, without video")
    ap.add_argument("--sil", action="store_true", help="software in the loop: ahead and two_fires over UDP, compared with in-process")
    ap.add_argument("--sil-scenarios", default="ahead,two_fires", help="comma-separated scenarios for --sil, each with an optional :runs, e.g. two_fires:5,ahead:3")
    ap.add_argument("--repeat", type=int, default=1, help="SIL runs per scenario")
    ap.add_argument("--no-pose", action="store_true", help="SIL without the pose stream on 5605: aim/run.py dead-reckons")
    args = ap.parse_args()
    if args.sil:
        return sil_compare(args.detector, args.sil_scenarios.split(","), args.repeat, not args.no_pose)
    if args.suite or args.quick:
        sys.exit(0 if suite(args.detector, args.quick) else 1)
    r = run(args.scenario, args.detector, out=args.out)
    print(HEADER)
    print(row(r))
    print("detections by object:", r["counts"])


if __name__ == "__main__":
    main()
