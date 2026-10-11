"""Round 2: search a better camera pose for concepts A, B and E, and a better nozzle place on B (see README.md).

blender -b --factory-startup -P cad/camera_views/mounts.py -- [render]

Writes out/mounts.md. With "render" it also writes out/round2/*.jpg and out/round2_contact_sheet.jpg.
"""
import itertools
import math
import os
import subprocess
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import views as V  # noqa: E402
import concepts  # noqa: E402  (views puts cad/ on sys.path)

NEAR_MAX, FAR_MIN = 0.85, 5.0  # floor target ("about 0.8 m"), metres from the robot origin
CENTRE = 0.6  # no robot part in the central 60 % of the image width and height
STEPS = (-0.08, -0.04, 0.0, 0.04, 0.08)  # lens moves in the gun / head / pod frame (m)
MAX_MOVE = 0.09  # keep the lens within about 8 cm (at most 9 cm) of its current place
TILTS = range(10, 41, 2)  # camera tilt down from horizontal (degrees)
THERMAL_B = ((0.060, -0.008, 0.012), 56, 42)  # B thermal lens front in the head frame, 256x192 class FOV
NOZZLE_B = [(y, z) for y in (0.0, 0.01, -0.05) for z in (0.0, -0.02, -0.035, -0.05)]  # nozzle axis (y, z) on the head
OUT = os.path.join(V.OUT, "round2")


def cam_pose(key, move, tilt, lens=None):
    """Lens moved by `move` on the gun/head/pod (left at its default tilt); camera tilted `tilt` degrees down."""
    _, pivot, part_tilt, base = V.MOUNTS[key]
    o = Vector(pivot) + Matrix.Rotation(math.radians(part_tilt), 3, "Y") @ (Vector(lens or base) + Vector(move))
    R = Matrix.Rotation(math.radians(tilt), 3, "Y")
    return o, (R @ Vector((1, 0, 0)), Vector((0, -1, 0)), R @ Vector((0, 0, 1)))


def measure(cast, key, move, tilt, hf, checks):
    vf = V.vfov(hf, *V.RES)
    o, axes = cam_pose(key, move, tilt)
    near, far = V.floor_reach(o, tilt, vf)
    seen, blocked = V.first_floor(cast, o, axes, hf, vf)
    if not blocked:
        V.check(key, tilt, hf, near, seen, checks)
    return dict(move=move, tilt=tilt, hf=hf, o=o, near=seen, far=far,
                centre=V.robot_share(cast, o, axes, hf, vf, CENTRE, 24), whole=V.robot_share(cast, o, axes, hf, vf))


def step(near):
    """Near floor rounded up to 5 cm, so that a 1 cm gain does not pick a larger lens move."""
    return math.ceil(near * 20 - 1e-9) / 20


def search(cast, key, hf, checks):
    """Centre free and far floor >= 5 m; then near floor down to the target; then the smallest move and tilt change."""
    vf, best = V.vfov(hf, *V.RES), None
    for move in itertools.product((0.0, 0.04, 0.08), STEPS, STEPS):
        if Vector(move).length > MAX_MOVE:
            continue
        for tilt in TILTS:
            o, axes = cam_pose(key, move, tilt)
            near, far = V.floor_reach(o, tilt, vf)
            score = [max(step(near), NEAR_MAX), round(Vector(move).length, 3), abs(tilt - V.MOUNTS[key][2])]
            if far < FAR_MIN or (best and score >= best[0]) or V.robot_share(cast, o, axes, hf, vf, CENTRE, 16) > 0:
                continue
            score[0] = max(step(V.first_floor(cast, o, axes, hf, vf)[0]), NEAR_MAX)  # ray cast: robot parts can hide the floor
            if not best or score < best[0]:
                best = (score, move, tilt)
    return measure(cast, key, best[1], best[2], hf, checks)


def move_nozzle(y, z):
    for name in ("nozzle", "nozzle_ring", "nozzle_tip"):
        bpy.data.objects[name].location.yz = (y, z)


def nozzle_table(cast_fn, checks):
    """Robot share of the B images at the current camera pose for each nozzle place."""
    rows = []
    lens, thf, tvf = THERMAL_B
    for y, z in NOZZLE_B:
        move_nozzle(y, z)
        cast = cast_fn()
        tilt = V.MOUNTS["B"][2]
        r = [measure(cast, "B", (0, 0, 0), tilt, hf, checks)["whole"] for hf in (90, 60)]
        o, axes = cam_pose("B", (0, 0, 0), tilt, lens)
        rows.append(((y, z), *r, V.robot_share(cast, o, axes, thf, tvf)))
    return rows


def pos(v):
    return "(" + ", ".join(f"{c:+.3f}" for c in v) + ")"


def write(results, nozzles):
    L = ["## Table 4. Camera pose per concept, current and recommended", "",
         "Goal: no robot part in the central 60 % of the image, floor seen from 0.85 m or closer (about 0.8 m) to at least 5 m, from the robot origin.",
         "Lens = front of the RGB lens. Part frame = the gun (A), head (B) or pod (E) frame at its default tilt, x forward, z up.",
         "Tilt = camera angle below horizontal. The gun, head or pod keeps its default tilt, so the camera needs its own pitch on it.", "",
         "| Concept | Pose | HFOV | Lens, part frame (m) | Move (m) | Lens, robot frame (m) | Tilt | Pitch on part | Robot in centre 60 % | Robot in image | Near floor (m) | Far floor (m) | Goal met |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for label, r in results:
        key = label[0]
        lens = Vector(V.MOUNTS[key][3]) + Vector(r["move"])
        L.append(f"| {label} | {'current' if not any(r['move']) and r['tilt'] == V.MOUNTS[key][2] else 'recommended'} "
                 f"| {r['hf']} deg | {pos(lens)} | {pos(r['move'])} | {pos(r['o'])} | {r['tilt']} deg | {r['tilt'] - V.MOUNTS[key][2]:+d} deg "
                 f"| {r['centre']:.0%} | {r['whole']:.0%} | {r['near']:.2f} | {V.fmt(r['far'])} "
                 f"| {'yes' if r['centre'] == 0 and r['near'] <= NEAR_MAX and r['far'] >= FAR_MIN else 'no'} |")
    L += ["", "## Table 5. Nozzle place on concept B, cameras at the current pose", "",
          "Nozzle axis (y, z) in the head frame. The current nozzle is at (0, 0), 12 mm under the camera axis.",
          "Values are the share of the image that shows robot parts. Thermal = 56 x 42 deg lens at the thermal camera place.", "",
          "| Nozzle (y, z) (m) | RGB 90 deg | RGB 60 deg | Thermal 56 x 42 deg |", "|---|---|---|---|"]
    for (y, z), a, b, t in nozzles:
        L.append(f"| ({y:+.3f}, {z:+.3f}) | {a:.0%} | {b:.0%} | {t:.0%} |")
    with open(f"{V.OUT}/mounts.md", "w") as fh:
        fh.write("\n".join(L) + "\n")


def shoot(key, r, name):
    cam = V.camera()
    o, (fwd, _, _) = cam_pose(key, r["move"], r["tilt"])
    cam.location, cam.rotation_euler = o, fwd.to_track_quat("-Z", "Y").to_euler()
    cam.data.angle = math.radians(r["hf"])
    V.bhl.render(f"{OUT}/{key}_{name}.jpg", res=V.RES, samples=32)


def main(args):
    do_render = "render" in args
    os.makedirs(OUT, exist_ok=True)
    results, checks, nozzles = [], [], []
    for key in "ABE":
        V.room()
        root = concepts.build(key)
        robot = {o.name for o in root.children_recursive}
        cast_fn = lambda: V.caster(robot)  # noqa: E731
        cast = cast_fn()
        now = {hf: measure(cast, key, (0, 0, 0), V.MOUNTS[key][2], hf, checks) for hf in (90, 60)}
        best = {hf: search(cast, key, hf, checks) for hf in (90, 60)}
        results += [(key, now[90]), (key, best[90]), (key, now[60]), (key, best[60])]
        if key == "B":  # nozzle search and camera search with the moved nozzle, before the fires enter the scene
            nozzles = nozzle_table(cast_fn, checks)
            (y, z), *_ = min(nozzles, key=lambda n: (n[1] + n[3], abs(n[0][0]) + abs(n[0][1])))
            move_nozzle(y, z)
            cast, label = cast_fn(), f"B, nozzle at ({y:+.3f}, {z:+.3f})"
            moved = {hf: search(cast, key, hf, checks) for hf in (90, 60)}
            results += [(label, measure(cast, key, (0, 0, 0), V.MOUNTS[key][2], 90, checks)), (label, moved[90]), (label, moved[60])]
            move_nozzle(0, 0)
        if do_render:
            V.markings()
            shoot(key, now[90], "1_before")
            shoot(key, best[90], "2_after_camera")
            if key == "B":
                move_nozzle(y, z)
                shoot(key, now[90], "3_after_nozzle")
                shoot(key, moved[90], "4_after_nozzle_and_camera")
    assert checks
    write(results, nozzles)
    if do_render:
        imgs = sorted(os.listdir(OUT))
        subprocess.run(["magick", "montage", "-pointsize", "22"] + [a for v in imgs for a in ("-label", v[:-4], f"{OUT}/{v}")]
                       + ["-tile", "2x", "-geometry", "640x360+4+4", f"{V.OUT}/round2_contact_sheet.jpg"], check=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
