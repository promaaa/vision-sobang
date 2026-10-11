"""Five firefighter-robot concepts on Berkeley Humanoid Lite legs.

blender -b --factory-startup -P concepts.py -- <out_dir> [A B C D E lineup]

Importable from another Blender script: sys.path.insert(0, "cad"); import concepts; concepts.scene(); concepts.build("A").

Robot frame: x forward, y left, z up, metres, feet on the floor (z = 0).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import bhl  # noqa: E402
from bhl import box, cone, cyl, sphere, tube  # noqa: E402

# Berkeley assets: scripts/fetch_bhl_assets.sh puts them here; the BHL_DIR env var overrides.
BHL = os.environ.get("BHL_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "third_party",
                     "berkeley-humanoid-lite-assets", "data", "robots", "berkeley_humanoid", "berkeley_humanoid_lite"))
Z0 = 0.039  # lowest foot point in the STAND pose
T = 0.791  # top of the BHL torso frame
LEGS_ONLY = {n for n in ("arm_%s_%s" % (s, j) for s in ("left", "right") for j in
             ("shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow_pitch", "elbow_roll", "hand_link"))}
# Right arm pointing forward (grid search on forearm direction); left arm relaxed.
ARM_POSE = {"arm_right_shoulder_pitch_joint": 1.374, "arm_right_shoulder_roll_joint": 0.26,
            "arm_right_shoulder_yaw_joint": -0.78, "arm_right_elbow_pitch_joint": -0.196,
            "arm_left_shoulder_pitch_joint": -0.15, "arm_left_elbow_pitch_joint": 0.35}

M = {}


def materials():
    m = bhl.mat
    M.update(
        pla=m("pla", (0.07, 0.07, 0.075), rough=0.42),
        red=m("red", (0.55, 0.025, 0.02), rough=0.35, coat=0.3),
        yellow=m("yellow", (0.9, 0.42, 0.0), rough=0.4),
        tape=m("tape", (0.85, 0.85, 0.85), rough=0.15, metal=1),
        alu=m("alu", (0.75, 0.75, 0.77), rough=0.32, metal=1),
        black=m("black", (0.015, 0.015, 0.017), rough=0.45),
        rubber=m("rubber", (0.02, 0.02, 0.02), rough=0.8),
        brass=m("brass", (0.85, 0.58, 0.28), rough=0.25, metal=1),
        clear=m("clear", (0.9, 0.95, 1.0), rough=0.08, transmission=1),
        water=m("water", (0.25, 0.55, 0.9), rough=0.02, transmission=1),
        lens=m("lens", (0.01, 0.01, 0.015), rough=0.05, coat=1),
        ir=m("ir", (0.12, 0.1, 0.06), rough=0.2, metal=0.6),
        led=m("led", (1, 1, 1), emission=(1, 0.95, 0.85), strength=15),
        beacon=m("beacon", (0.8, 0.05, 0.02), emission=(1, 0.05, 0.02), strength=8),
        orange=m("orange", (0.95, 0.3, 0.02), rough=0.35),
        hose=m("hose", (0.85, 0.45, 0.02), rough=0.6),
        shell=m("shell", (0.8, 0.8, 0.82), rough=0.22, metal=1),
    )


# ---------- shared parts ----------
def robot(arms=False, q=None):
    pose = dict(bhl.STAND, **(q or {}))
    urdf = f"{BHL}/urdf/berkeley_humanoid_lite.urdf"  # its base visual offset matches base_visual.stl; the biped URDF's does not
    objs, frames = bhl.load_robot(urdf, f"{BHL}/meshes", pose, M["pla"], skip=() if arms else LEGS_ONLY)
    shift = Matrix.Translation((0, 0, -Z0))
    for o in objs.values():
        o.matrix_world = shift @ o.matrix_world
    if not arms:  # base_visual.stl carries the shoulder motors; a legs-only robot does not need them
        bhl.delete_faces(objs["base"], lambda p: abs(p.y) > 0.1 and p.z > 0.62)
    return objs, {k: shift @ v for k, v in frames.items()}


def empty(name, loc, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location, o.rotation_euler = loc, [math.radians(a) for a in rot]
    return o


def stripes(x, y0, y1, z, width=0.016):
    """Yellow / silver / yellow reflective band on a front face at x."""
    w = y1 - y0
    box("stripe_y", (0.004, w, width), (x, (y0 + y1) / 2, z), M["yellow"], bevel=0.001)
    box("stripe_s", (0.005, w + 0.001, width * 0.33), (x, (y0 + y1) / 2, z), M["tape"], bevel=0)


def chest_plate():
    box("chest", (0.008, 0.17, 0.22), (0.078, 0, 0.665), M["red"], bevel=0.006)
    stripes(0.083, -0.085, 0.085, 0.61)
    stripes(0.083, -0.085, 0.085, 0.72)


def pan_tilt(tilt_deg):
    """Deck plate + pan servo + U bracket on the torso top. Returns the tilting parent (x forward)."""
    box("deck", (0.15, 0.17, 0.006), (0, 0, T + 0.003), M["alu"], bevel=0.002)
    cyl("pan_servo", 0.035, 0.03, (0, 0, T + 0.021), M["black"])
    cyl("turntable", 0.045, 0.006, (0, 0, T + 0.039), M["alu"])
    box("u_base", (0.05, 0.11, 0.005), (0, 0, T + 0.044), M["alu"], bevel=0.001)
    for s in (-1, 1):
        box("u_side", (0.05, 0.005, 0.07), (0, s * 0.0525, T + 0.077), M["alu"], bevel=0.001)
    box("tilt_servo", (0.04, 0.02, 0.04), (0, 0.067, T + 0.09), M["black"])
    return empty("tilt", (0, 0, T + 0.095), (0, tilt_deg, 0))


def nozzle(parent, x, r=0.01, length=0.09):
    """Brass nozzle along local +x starting at x."""
    cyl("nozzle", r, length, (x + length / 2, 0, 0), M["brass"], rot=(0, 90, 0), parent=parent)
    cyl("nozzle_ring", r * 1.6, 0.015, (x + length * 0.7, 0, 0), M["rubber"], rot=(0, 90, 0), parent=parent)
    cone("nozzle_tip", r, r * 0.45, 0.025, (x + length + 0.0125, 0, 0), M["brass"], rot=(0, 90, 0), parent=parent)


def cam_rgb(parent, loc, r=0.011):
    cyl("rgb_bezel", r * 1.4, 0.006, loc, M["black"], rot=(0, 90, 0), parent=parent)
    cyl("rgb_lens", r, 0.008, (loc[0] + 0.004, loc[1], loc[2]), M["lens"], rot=(0, 90, 0), parent=parent)


def cam_thermal(parent, loc):
    box("ir_body", (0.008, 0.024, 0.024), loc, M["black"], bevel=0.002, parent=parent)
    cyl("ir_lens", 0.006, 0.006, (loc[0] + 0.005, loc[1], loc[2]), M["ir"], rot=(0, 90, 0), parent=parent)


def tank(x, y, z_bottom, r, h, fill=0.8):
    cyl("tank", r, h, (x, y, z_bottom + h / 2), M["clear"], bevel=0.004)
    cyl("water", r - 0.004, h * fill, (x, y, z_bottom + 0.004 + h * fill / 2), M["water"], bevel=0.002)
    cyl("tank_cap", 0.018, 0.02, (x, y, z_bottom + h + 0.01), M["red"])
    for f in (0.25, 0.75):
        cyl("strap", r + 0.003, 0.012, (x, y, z_bottom + h * f), M["black"], bevel=0.001)


def backpack(r, h):
    """Aluminium frame on the back: clear tank on a tray above the hips, self-priming 12 V pump on top."""
    for s in (-1, 1):
        box("bp_rail", (0.012, 0.012, 0.3), (-0.088, s * 0.055, 0.68), M["alu"], bevel=0.001)
    for z in (0.54, 0.79):
        box("bp_bar", (0.012, 0.13, 0.012), (-0.088, 0, z), M["alu"], bevel=0.001)
    box("bp_tray", (0.11, 0.13, 0.006), (-0.14, 0, 0.55), M["alu"], bevel=0.001)
    box("bp_top", (0.11, 0.13, 0.006), (-0.14, 0, 0.795), M["alu"], bevel=0.001)
    tank(-0.145, 0, 0.553, r, h)
    box("pump", (0.06, 0.05, 0.035), (-0.145, 0.02, 0.816), M["black"], bevel=0.004)
    cyl("pump_motor", 0.016, 0.045, (-0.145, -0.025, 0.816), M["alu"], rot=(90, 0, 0))
    tube("feed", [(-0.145, 0, 0.553 + h + 0.02), (-0.15, 0.03, 0.553 + h + 0.03), (-0.175, 0.03, 0.81)], 0.005, M["hose"])
    return (-0.115, 0.03, 0.816)  # pump outlet


# ---------- concepts ----------
def concept_A():
    """Water gun on a pan-tilt: fastest build."""
    robot()
    g = pan_tilt(6)
    box("gun_body", (0.24, 0.07, 0.085), (0.02, 0, 0), M["orange"], bevel=0.016, parent=g)
    box("gun_rear", (0.03, 0.062, 0.07), (-0.11, 0, 0), M["black"], bevel=0.006, parent=g)
    cyl("gun_barrel", 0.02, 0.12, (0.2, 0, 0.005), M["orange"], rot=(0, 90, 0), parent=g)
    cyl("gun_shroud", 0.027, 0.035, (0.155, 0, 0.005), M["yellow"], rot=(0, 90, 0), parent=g)
    cone("gun_tip", 0.02, 0.008, 0.03, (0.275, 0, 0.005), M["black"], rot=(0, 90, 0), parent=g)
    cyl("gun_tank", 0.038, 0.17, (-0.005, 0, 0.078), M["clear"], rot=(0, 90, 0), parent=g)
    cyl("gun_water", 0.034, 0.15, (-0.005, 0, 0.078), M["water"], rot=(0, 90, 0), parent=g)
    for x in (-0.09, 0.08):
        cyl("gun_tank_end", 0.04, 0.012, (x, 0, 0.078), M["black"], rot=(0, 90, 0), parent=g)
    cyl("gun_fill", 0.014, 0.016, (-0.05, 0, 0.118), M["red"], parent=g)
    box("cam", (0.03, 0.04, 0.028), (0.115, 0, 0.056), M["black"], bevel=0.004, parent=g)
    cam_rgb(g, (0.131, 0, 0.056), r=0.008)
    tube("trigger_wire", [(-0.11, -0.03, T + 0.06), (-0.12, -0.05, T + 0.03), (-0.07, -0.07, T + 0.006)], 0.0025, M["black"])


def concept_B():
    """Backpack tank + pump, camera-and-nozzle head."""
    robot()
    chest_plate()
    out = backpack(0.05, 0.18)
    cyl("neck", 0.03, 0.03, (0, 0, T + 0.016), M["black"])
    h = empty("head", (0, 0, T + 0.075), (0, 5, 0))
    box("head_shell", (0.09, 0.13, 0.075), (0, 0, 0), M["red"], bevel=0.016, parent=h)
    box("face", (0.006, 0.112, 0.056), (0.046, 0, 0.002), M["black"], bevel=0.003, parent=h)
    cam_rgb(h, (0.05, 0.028, 0.012))
    cam_thermal(h, (0.051, -0.008, 0.012))
    for y in (-0.042, 0.052):
        box("led", (0.004, 0.012, 0.008), (0.05, y, 0.012), M["led"], bevel=0.001, parent=h)
    box("head_stripe", (0.092, 0.132, 0.008), (0, 0, 0.03), M["yellow"], bevel=0.003, parent=h)
    nozzle(h, 0.045, r=0.009, length=0.075)  # under the cameras, aims with the head
    tube("hose", [out, (-0.09, 0.04, 0.83), (-0.07, -0.1, 0.85), (-0.01, -0.09, T + 0.07), (0.0, -0.064, T + 0.07)], 0.006, M["hose"])


def concept_C():
    """Full humanoid holding a nozzle lance with its right arm."""
    _, fr = robot(arms=True, q=ARM_POSE)
    chest_plate()
    out = backpack(0.045, 0.15)
    # helmet head with cameras under the brim
    cyl("neck", 0.025, 0.04, (0, 0, T + 0.02), M["black"])
    box("visor", (0.04, 0.1, 0.045), (0.052, 0, T + 0.072), M["black"], bevel=0.012)
    cam_rgb(None, (0.072, 0.025, T + 0.072), r=0.009)
    cam_thermal(None, (0.072, -0.02, T + 0.072))
    sphere("helmet", 0.07, (-0.01, 0, T + 0.1), M["yellow"], scale=(1.12, 0.95, 0.85))
    cyl("brim", 0.095, 0.006, (-0.03, 0, T + 0.098), M["yellow"], bevel=0.003).scale = (1.3, 1.0, 1.0)
    box("comb", (0.13, 0.012, 0.02), (-0.015, 0, T + 0.152), M["yellow"], bevel=0.006)
    box("badge", (0.006, 0.045, 0.05), (0.07, 0, T + 0.135), M["red"], rot=(0, -28, 0), bevel=0.003)
    # lance in the right hand, along the forearm
    hand, elbow = fr["arm_right_hand_link"].translation, fr["arm_right_elbow_pitch"].translation
    d = (hand - elbow).normalized()
    lance = empty("lance", hand)
    lance.rotation_euler = d.to_track_quat("X", "Z").to_euler()
    box("valve", (0.07, 0.032, 0.036), (0.01, 0, 0), M["black"], bevel=0.006, parent=lance)
    nozzle(lance, 0.045, r=0.012, length=0.1)
    bail = tube("bail", [(-0.01, 0, 0.018), (0.0, 0, 0.05), (0.04, 0, 0.05), (0.045, 0, 0.018)], 0.004, M["red"])
    bail.parent = lance
    rear = hand - d * 0.03
    tube("hose", [tuple(rear), tuple(rear - d * 0.06 + Vector((0, -0.02, -0.03))), tuple(elbow + Vector((-0.02, -0.04, -0.03))),
                  (-0.02, -0.19, 0.69), (-0.05, -0.17, 0.82), (-0.09, -0.06, 0.84), out],
         0.007, M["hose"])


def concept_D():
    """Sealed reflective shell, tank inside, fixed chest nozzle: aims with the whole body."""
    robot()
    box("shell", (0.21, 0.27, 0.26), (-0.005, 0, 0.69), M["shell"], bevel=0.045)
    box("front", (0.02, 0.215, 0.2), (0.093, 0, 0.67), M["red"], bevel=0.012)
    box("visor", (0.02, 0.17, 0.046), (0.1, 0, 0.785), M["lens"], bevel=0.012)
    for y in (-0.055, 0.055):
        cam_rgb(None, (0.111, y, 0.785), r=0.01)
    cam_thermal(None, (0.108, 0, 0.785))
    stripes(0.104, -0.105, 0.105, 0.735)
    stripes(0.104, -0.105, 0.105, 0.6)
    nz = empty("nozzle_mount", (0.103, 0, 0.665), (0, 10, 0))
    cyl("guard", 0.032, 0.02, (0.0, 0, 0), M["black"], rot=(0, 90, 0), parent=nz)
    nozzle(nz, 0.008, r=0.011, length=0.07)
    # level gauge on the right side shows the water inside
    cyl("gauge", 0.009, 0.17, (-0.02, -0.137, 0.68), M["clear"])
    cyl("gauge_water", 0.0065, 0.1, (-0.02, -0.137, 0.646), M["water"])
    for z in (0.592, 0.768):
        box("gauge_clip", (0.03, 0.012, 0.01), (-0.02, -0.135, z), M["black"], bevel=0.002)
    tube("handle", [(-0.03, -0.085, 0.815), (-0.03, -0.075, 0.875), (-0.03, 0.075, 0.875), (-0.03, 0.085, 0.815)], 0.008, M["rubber"])
    cyl("beacon_base", 0.02, 0.012, (-0.075, 0.07, 0.826), M["black"])
    sphere("beacon", 0.016, (-0.075, 0.07, 0.84), M["beacon"], scale=(1, 1, 1.25))
    cyl("fill_cap", 0.022, 0.02, (-0.112, 0, 0.75), M["red"], rot=(0, 90, 0))
    box("vent", (0.006, 0.12, 0.05), (-0.11, 0, 0.63), M["black"], bevel=0.003)


def concept_E():
    """No water on board: tethered hose from an external pump, nozzle pan-tilt, camera mast."""
    robot()
    chest_plate()
    g = pan_tilt(4)
    box("valve", (0.06, 0.04, 0.045), (0.0, 0, 0), M["black"], bevel=0.005, parent=g)
    cyl("coil", 0.017, 0.03, (-0.005, 0, 0.035), M["red"], parent=g)
    nozzle(g, 0.03, r=0.01, length=0.11)
    # camera mast on the left rear corner
    cyl("mast", 0.009, 0.16, (-0.055, 0.07, T + 0.08), M["alu"])
    p = empty("pod", (-0.05, 0.07, T + 0.175), (0, 6, 0))
    box("pod_shell", (0.05, 0.08, 0.04), (0, 0, 0), M["red"], bevel=0.01, parent=p)
    cam_rgb(p, (0.026, 0.018, 0.0), r=0.009)
    cam_thermal(p, (0.026, -0.018, 0.0))
    box("pod_led", (0.004, 0.06, 0.006), (0.026, 0, 0.015), M["led"], bevel=0.001, parent=p)
    # tether: swivel on the back of the pelvis, hose and power cable trail on the floor
    cyl("swivel", 0.016, 0.035, (-0.09, 0, 0.53), M["brass"], rot=(0, 90, 0))
    cyl("clamp", 0.02, 0.012, (-0.107, 0, 0.53), M["black"], rot=(0, 90, 0))
    tube("hose_up", [(-0.09, 0, 0.545), (-0.1, -0.03, 0.6), (-0.1, -0.035, 0.76), (-0.06, -0.02, T + 0.09), (-0.035, 0, T + 0.095)], 0.006, M["black"])
    trail = [(-0.115, 0, 0.53), (-0.2, 0, 0.47), (-0.3, 0.02, 0.2), (-0.38, 0.04, 0.016), (-0.7, 0.12, 0.016),
             (-1.1, 0.45, 0.016), (-1.6, 0.75, 0.016), (-2.4, 1.0, 0.016), (-3.5, 1.2, 0.016)]
    tube("tether", trail, 0.014, M["hose"])
    box("power_plug", (0.02, 0.025, 0.02), (-0.09, 0.04, 0.57), M["black"], bevel=0.003)
    tube("power", [(-0.1, 0.04, 0.57)] + [(x, y + 0.03, max(z - 0.005, 0.005)) for x, y, z in trail[1:]], 0.004, M["black"])


CONCEPTS = {k: globals()[f"concept_{k}"] for k in "ABCDE"}


def build(key, offset=(0, 0, 0)):
    before = set(bpy.data.objects)
    CONCEPTS[key]()
    root = empty(f"root_{key}", (0, 0, 0))
    bpy.context.view_layer.update()
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            mw = o.matrix_world.copy()
            o.parent = root
            o.matrix_world = mw
    root.location = offset
    return root


def scene():
    bhl.clear()
    bhl.studio()
    materials()


# close-up of each concept's top part: (centre, half size)
DETAIL = {"A": ((0.06, 0, 0.9), 0.17), "B": ((0.03, 0, 0.85), 0.13), "C": ((0.12, -0.08, 0.78), 0.2),
          "D": ((0.05, 0, 0.7), 0.17), "E": ((0.02, 0.03, 0.92), 0.15)}
PORTRAIT = (1600, 2000)


def robot_corners(root):
    """Bounding box of a concept without the floor-trailing tether."""
    objs = [o for o in root.children_recursive if o.type in ("MESH", "CURVE") and o.name.split(".")[0] not in ("tether", "power")]
    return bhl.corners(objs)


def main(out, which):
    for key in which:
        if key in CONCEPTS:
            scene()
            root = build(key)
            body = robot_corners(root)
            bhl.fit(body, -35, 10, 70, PORTRAIT)
            bhl.render(f"{out}/concept_{key}_front.png")
            bhl.fit(body, -145, 16, 70, PORTRAIT)
            bhl.render(f"{out}/concept_{key}_rear.png")
            (cx, cy, cz), h = DETAIL[key]
            box_pts = [(cx + dx * h, cy + dy * h, cz + dz * h) for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
            for o in root.children_recursive:  # the tether only crosses the close-up as a stray line
                o.hide_render = o.name.split(".")[0] in ("tether", "power")
            bhl.fit(box_pts, -28, 18, 90, PORTRAIT, margin=1.0)
            bhl.render(f"{out}/concept_{key}_detail.png")
        elif key == "lineup":
            scene()
            pts = []
            for i, k in enumerate("ABCDE"):
                y = (i - 2) * 0.62
                pts += robot_corners(build(k, (0, y, 0)))
                bpy.ops.object.text_add(location=(0.33, y, 0.001), rotation=(0, 0, math.radians(90)))
                t = bpy.context.object
                t.data.body, t.data.size, t.data.align_x, t.data.extrude = k, 0.11, "CENTER", 0.002
                t.data.materials.append(M["yellow"])
                pts.append((0.42, y, 0))
            bhl.fit(pts, -18, 10, 85, (2400, 1200), margin=1.1)
            bhl.render(f"{out}/lineup.png", samples=160)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    main(args[0], args[1:] or ["A", "B", "C", "D", "E", "lineup"])
