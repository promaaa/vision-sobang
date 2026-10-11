"""Camera placement and field-of-view study for the firefighter robot concepts (see README.md).

blender -b --factory-startup -P cad/camera_views/views.py -- [render] [A B C D E]

Without "render": writes out/tables.md only (geometry and ray casts, no images).
With "render": also writes the camera views, the bird's-eye overviews and the contact sheets.
Default concepts: A B E.
"""
import math
import os
import subprocess
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bhl  # noqa: E402
import concepts  # noqa: E402
from bhl import box, cone  # noqa: E402

OUT = os.path.join(HERE, "out")
T = concepts.T
# RGB lens of each concept, numbers from concepts.py:
# (tilting empty, its pivot, default tilt in degrees down, lens front in the pivot frame).
# C and D have no tilt joint, so the pivot is the lens itself.
MOUNTS = {
    "A": ("tilt", (0, 0, T + 0.095), 6, (0.140, 0, 0.056)),
    "B": ("head", (0, 0, T + 0.075), 5, (0.059, 0.028, 0.012)),
    "C": (None, (0.081, 0.025, T + 0.072), 0, (0, 0, 0)),
    "D": (None, (0.120, 0.055, 0.785), 0, (0, 0, 0)),
    "E": ("pod", (-0.05, 0.07, T + 0.175), 6, (0.035, 0.018, 0)),
}
ALT_TILT = 20
HFOVS = (60, 90, 120)
RES = (1280, 720)
FIRES = [(1, 0), (2, 0), (3, 0), (5, 0), (2 * math.cos(math.radians(30)), 2 * math.sin(math.radians(30)))]
BACK, SIDE = 8.0, 6.0  # room: back wall at x = 8 m, side walls at y = +-6 m
FIRE_W, FIRE_H = 0.20, 0.25
DISTANCES = (1, 2, 3, 5, 8)
# (name, width px, height px, HFOV, VFOV or None = from the aspect ratio, source)
SENSORS = [
    ("MLX90640 BAB (narrow)", 32, 24, 55, 35, "[1]"),
    ("MLX90640 BAA (wide)", 32, 24, 110, 75, "[1]"),
    ("FLIR Lepton 2.5", 80, 60, 50, None, "[2]"),
    ("FLIR Lepton 3.5", 160, 120, 57, None, "[2]"),
    ("FLIR Lepton 3.1R (wide)", 160, 120, 95, None, "[2]"),
    ("256x192 USB (TOPDON TC001)", 256, 192, 56, 42, "[3]"),
] + [(f"RGB {w}x{h}", w, h, f, None, "") for w, h in ((640, 480), (1280, 720)) for f in HFOVS]


def vfov(hfov, w, h):
    """Vertical FOV of a pinhole camera with square pixels."""
    return math.degrees(2 * math.atan(math.tan(math.radians(hfov) / 2) * h / w))


def pose(key, tilt):
    """World lens position and camera axes (forward, right, up) for a tilt in degrees down."""
    _, pivot, _, lens = MOUNTS[key]
    R = Matrix.Rotation(math.radians(tilt), 3, "Y")
    return Vector(pivot) + R @ Vector(lens), (R @ Vector((1, 0, 0)), Vector((0, -1, 0)), R @ Vector((0, 0, 1)))


def ray(axes, u, v, hf, vf):
    """Direction through image point (u, v), both in [-1, 1], u to the right, v up."""
    f, r, up = axes
    return (f + r * u * math.tan(math.radians(hf) / 2) + up * v * math.tan(math.radians(vf) / 2)).normalized()


def floor_reach(o, tilt, vf):
    """Analytic floor distances along the image centre column, from the robot origin (m): near edge, far edge."""
    lo, hi = math.radians(tilt + vf / 2), math.radians(tilt - vf / 2)
    near = o.x + (o.z / math.tan(lo) if lo < math.pi / 2 else 0.0)
    far = o.x + o.z / math.tan(hi) if hi > 0 else math.inf
    return near, far


def tilts(key):
    return (MOUNTS[key][2], ALT_TILT)


def set_tilt(key, tilt):
    if MOUNTS[key][0]:
        bpy.data.objects[MOUNTS[key][0]].rotation_euler.y = math.radians(tilt)
    bpy.context.view_layer.update()


# ---------- scene ----------
def room():
    """Neutral lit room: light floor, three light walls, open top under a grey sky and a sun."""
    bhl.clear()
    concepts.materials()
    sc = bpy.context.scene
    sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.85, 1)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(30), math.radians(-25), 0))
    bpy.context.object.data.energy = 2.5
    floor_m, wall_m = bhl.mat("floor", (0.45, 0.45, 0.43), rough=0.8), bhl.mat("wall", (0.7, 0.7, 0.68), rough=0.9)
    box("floor", (BACK + 4, 2 * SIDE, 0.02), (BACK / 2 - 2, 0, -0.01), floor_m, bevel=0)
    box("wall", (0.1, 2 * SIDE, 2.6), (BACK + 0.05, 0, 1.3), wall_m, bevel=0)
    for s in (-1, 1):
        box("wall", (BACK + 4, 0.1, 2.6), (BACK / 2 - 2, s * (SIDE + 0.05), 1.3), wall_m, bevel=0)
    for o in bpy.data.objects:  # no wall shadow bands on the floor
        o.visible_shadow = o.name.split(".")[0] != "wall"


def text(body, loc, size, m):
    """Flat text on the floor that reads from the robot (letters point to +x)."""
    bpy.ops.object.text_add(location=loc, rotation=(0, 0, math.radians(-90)))
    t = bpy.context.object
    t.data.body, t.data.size = body, size
    t.data.materials.append(m)


def markings():
    """0.5 m floor grid, blue lines and labels at 1, 2, 3 and 5 m, and the fires."""
    g, blue = bhl.mat("grid", (0.08, 0.08, 0.08)), bhl.mat("mark", (0.02, 0.12, 0.6))
    for i in range(-2, int(2 * BACK)):
        box("grid", (0.02, 2 * SIDE, 0.002), (i * 0.5, 0, 0.001), g, bevel=0)
    for j in range(-2 * int(SIDE), 2 * int(SIDE) + 1):
        box("grid", (BACK + 1, 0.02, 0.002), (BACK / 2 - 0.5, j * 0.5, 0.001), g, bevel=0)
    for d in (1, 2, 3, 5):
        box("mark", (0.05, 2 * SIDE, 0.003), (d, 0, 0.0015), blue, bevel=0)
        text(f"{d} m", (d + 0.06, -0.3, 0.003), 0.2, blue)
    outer = bhl.mat("flame", (1, 0.3, 0.02), emission=(1, 0.3, 0.02), strength=3)
    core = bhl.mat("flame_core", (1, 0.8, 0.2), emission=(1, 0.75, 0.2), strength=6)
    for x, y in FIRES:  # 20 cm wide, 25 cm tall
        cone("fire", FIRE_W / 2, 0, FIRE_H, (x, y, FIRE_H / 2), outer)
        cone("fire_core", 0.06, 0, 0.17, (x - 0.045, y, 0.085), core)


def camera(ortho=False):
    sc = bpy.context.scene
    c = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(c)
    sc.camera = c
    c.data.sensor_fit, c.data.clip_start, c.data.clip_end = "HORIZONTAL", 0.005, 100
    if ortho:
        c.data.type, c.data.ortho_scale = "ORTHO", 2 * SIDE + 0.3
    sc.render.image_settings.file_format, sc.render.image_settings.quality = "JPEG", 90
    return c


# ---------- analysis ----------
def caster(robot):
    """cast(origin, direction) -> (hit point or None, True if the hit is a robot part)."""
    bpy.context.view_layer.update()
    sc, dg = bpy.context.scene, bpy.context.evaluated_depsgraph_get()

    def cast(o, d):
        hit, loc, _, _, ob, _ = sc.ray_cast(dg, o, d)
        return (loc, ob.original.name in robot) if hit else (None, False)
    return cast


def first_floor(cast, o, axes, hf, vf):
    """Walk up the image centre column until a ray reaches the room. Returns (x of that point, robot in the way?)."""
    for i in range(201):
        loc, on_robot = cast(o, ray(axes, 0, -1 + i * 0.01, hf, vf))
        if loc is not None and not on_robot:
            return loc.x, i > 0
    return math.inf, True


def check(key, tilt, hf, near, seen, checks):
    """The self-check: analytic blind zone = ray cast within 2 cm."""
    assert abs(seen - near) < 0.02, (key, tilt, hf, seen, near)
    checks.append((key, tilt, hf, near, seen))


def robot_share(cast, o, axes, hf, vf, lim=1.0, n=48):
    """Share of an n x n ray grid over the central lim x lim part of the image that hits the robot."""
    g = [lim * (-1 + (k + 0.5) * 2 / n) for k in range(n)]
    return sum(cast(o, ray(axes, u, v, hf, vf))[1] for u in g for v in g) / n ** 2


def analyse(key, robot, checks):
    """Per tilt and HFOV (16:9): analytic near/far floor, near floor seen by ray casts, share of image on the robot."""
    rows = []
    for tilt in tilts(key):
        set_tilt(key, tilt)
        cast = caster(robot)
        o, axes = pose(key, tilt)
        for hf in HFOVS:
            vf = vfov(hf, *RES)
            near, far = floor_reach(o, tilt, vf)
            seen, blocked = first_floor(cast, o, axes, hf, vf)
            if not blocked:
                check(key, tilt, hf, near, seen, checks)
            share = robot_share(cast, o, axes, hf, vf)
            rows.append((key, tilt, o.z, hf, vf, near, seen, blocked, far, share))
    return rows


def fmt(x):
    return "horizon" if x == math.inf else "> 30" if x > 30 else f"{x:.2f}"


def toe_x(root):
    return max(c[0] for c in bhl.corners([o for o in root.children_recursive if "ankle_roll" in o.name]))


def write_tables(rows, toes, checks):
    L = ["## Table 1. Floor in view, RGB camera at 1280x720 (rendered set)", "",
         "Distances are along the image centre column, in metres from the robot origin (the floor point between the feet).",
         "Toes: " + ", ".join(f"{k} {x:.2f} m" for k, x in toes.items()) + ".", "",
         "| Concept | Tilt down | Lens height (m) | HFOV x VFOV | Near floor, analytic | Near floor, ray cast | Far floor | Robot in image |",
         "|---|---|---|---|---|---|---|---|"]
    for key, tilt, z, hf, vf, near, seen, blocked, far, share in rows:
        s = f"{seen:.2f}" + (" (robot in the way)" if blocked else "")
        L.append(f"| {key} | {tilt} deg | {z:.2f} | {hf} x {vf:.0f} deg | {near:.2f} | {s} | {fmt(far)} | {share:.0%} |")
    keys = sorted({r[0] for r in rows})
    L += ["", "## Table 2. Blind zone and far floor for every sensor (analytic, no robot parts)", "",
          "Cell: near floor / far floor, metres from the robot origin. Same lens position as the RGB camera.", "",
          "| Sensor | HFOV x VFOV | " + " | ".join(f"{k} {t} deg" for k in keys for t in tilts(k)) + " |",
          "|---|---|" + "---|" * sum(len(tilts(k)) for k in keys)]
    for name, w, h, hf, vf, _ in SENSORS:
        vf = vf or vfov(hf, w, h)
        cells = []
        for k in keys:
            for t in tilts(k):
                n, f = floor_reach(pose(k, t)[0], t, vf)
                cells.append(f"{n:.2f} / {fmt(f)}")
        L.append(f"| {name} | {hf} x {vf:.0f} deg | " + " | ".join(cells) + " |")
    L += ["", "## Table 3. Size of a 20 cm wide, 25 cm tall fire in pixels (width x height)", "",
          "Pinhole model, fire at the image centre. **Bold** = fewer than 3 pixels in width or height.", "",
          "| Sensor | Pixels | HFOV x VFOV | Source | " + " | ".join(f"{d} m" for d in DISTANCES) + " |",
          "|---|---|---|---|" + "---|" * len(DISTANCES)]
    for name, w, h, hf, vf, src in SENSORS:
        src += " (VFOV computed)" if vf is None else ""
        vf = vf or vfov(hf, w, h)
        cells = []
        for d in DISTANCES:
            pw = w * FIRE_W / (2 * d * math.tan(math.radians(hf) / 2))
            ph = h * FIRE_H / (2 * d * math.tan(math.radians(vf) / 2))
            c = f"{pw:.1f} x {ph:.1f}"
            cells.append(f"**{c}**" if min(pw, ph) < 3 else c)
        L.append(f"| {name} | {w}x{h} | {hf} x {vf:.0f} deg | {src} | " + " | ".join(cells) + " |")
    L += ["", f"Self-check: {len(checks)} ray casts matched the analytic blind zone within 2 cm, e.g. "
          + ", ".join(f"{k} {t} deg {hf} deg: {n:.3f} vs {s:.3f} m" for k, t, hf, n, s in checks[:3]) + "."]
    with open(f"{OUT}/tables.md", "w") as fh:
        fh.write("\n".join(L) + "\n")


# ---------- images ----------
def footprint(o, axes, hf, vf, reach=6.0, n=40):
    """Floor outline of the view, cut at `reach` metres from the lens."""
    edge = ([(-1 + 2 * i / n, -1) for i in range(n)] + [(1, -1 + 2 * i / n) for i in range(n)]
            + [(1 - 2 * i / n, 1) for i in range(n)] + [(-1, 1 - 2 * i / n) for i in range(n)])
    pts = []
    for u, v in edge:
        d = ray(axes, u, v, hf, vf)
        h = Vector((d.x, d.y))
        r = min(reach, -o.z * h.length / d.z) if d.z < 0 else reach
        pts.append(o.xy + h.normalized() * r)
    return pts


def flat(name, pts, z, m, line=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(p.x, p.y, z) for p in pts], [], [list(range(len(pts)))])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(m)
    c = bpy.data.curves.new(name + "_edge", "CURVE")
    c.dimensions, c.bevel_depth = "3D", 0.015
    s = c.splines.new("POLY")
    s.points.add(len(pts) - 1)
    for sp, p in zip(s.points, pts):
        sp.co = (p.x, p.y, z + 0.001, 1)
    s.use_cyclic_u = True
    e = bpy.data.objects.new(name + "_edge", c)
    bpy.context.scene.collection.objects.link(e)
    e.data.materials.append(line)


def render_views(key):
    cam = camera()
    for tilt in tilts(key):
        set_tilt(key, tilt)
        o, (f, _, _) = pose(key, tilt)
        cam.location, cam.rotation_euler = o, f.to_track_quat("-Z", "Y").to_euler()
        for hf in HFOVS:
            cam.data.angle = math.radians(hf)
            bhl.render(f"{OUT}/views/{key}_tilt{tilt:02d}_hfov{hf:03d}.jpg", res=RES, samples=32)
    set_tilt(key, MOUNTS[key][2])


def render_overview(key):
    colors = {60: (0.05, 0.3, 1.0), 90: (0.05, 0.7, 0.15), 120: (1.0, 0.45, 0.0)}
    tilt = MOUNTS[key][2]
    o, axes = pose(key, tilt)
    for k, hf in enumerate(reversed(HFOVS)):
        c = colors[hf]
        fill = bhl.mat(f"fov{hf}", c, alpha=0.25, emission=c, strength=0.3)
        flat(f"fov{hf}", footprint(o, axes, hf, vfov(hf, *RES)), 0.005 + 0.002 * k, fill, bhl.mat(f"fov{hf}_line", c))
        text(f"{hf} deg", (5.6, SIDE - 0.3 - 1.4 * k, 0.01), 0.35, bhl.mat(f"fov{hf}_line", c))
    text(f"{key}  tilt {tilt} deg", (5.6, -SIDE + 3.2, 0.01), 0.35, bhl.mat("black_text", (0, 0, 0)))
    cam = camera(ortho=True)
    cam.location, cam.rotation_euler = (2.75, 0, 20), (0, 0, math.radians(-90))
    bhl.render(f"{OUT}/overview_{key}.jpg", res=RES, samples=32)


def main(args):
    do_render = "render" in args
    keys = [a for a in args if a in MOUNTS] or ["A", "B", "E"]
    rows, toes, checks = [], {}, []
    for key in keys:
        room()
        root = concepts.build(key)
        robot = {o.name for o in root.children_recursive}
        toes[key] = toe_x(root)
        rows += analyse(key, robot, checks)
        if do_render:
            markings()
            render_views(key)
            render_overview(key)
    assert checks, "no mount had a clear bottom ray to check"
    write_tables(rows, toes, checks)
    if do_render:
        views = sorted(os.listdir(f"{OUT}/views"))
        subprocess.run(["magick", "montage", "-pointsize", "22"] + [a for v in views for a in ("-label", v[:-4], f"{OUT}/views/{v}")]
                       + ["-tile", "3x", "-geometry", "640x360+4+4", f"{OUT}/contact_sheet.jpg"], check=True)
        subprocess.run(["magick", "montage"] + [f"{OUT}/overview_{k}.jpg" for k in keys]
                       + ["-tile", "3x", "-geometry", "960x540+4+4", f"{OUT}/overview.jpg"], check=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
