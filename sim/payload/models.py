"""Build MuJoCo models of Berkeley Humanoid Lite (BHL) with the payload of each body concept A-E.

    uv run python models.py        # writes models/*.xml, then runs the self-check

Payload positions come from cad/concepts.py (robot frame: x forward, y left, z up, feet on the floor,
torso upright). Masses are estimates (see PARTS). Each part is a rigid body welded to the BHL base
(or to the right hand for the lance of C), with a solid-box inertia and a visual box (no collision).
"""
import json
import os

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "models")
BHL = os.path.normpath(os.path.join(HERE, "../../third_party/berkeley-humanoid-lite-assets/data/robots/"
                                          "berkeley_humanoid/berkeley_humanoid_lite"))
MESHDIR = os.path.relpath(os.path.join(BHL, "meshes"), OUT)  # relative, so the saved XML files work from models/
Z0 = 0.039  # cad/concepts.py shifts the URDF down by Z0: robot-frame z + Z0 = BHL base-frame z
T = 0.791  # top of the BHL torso frame, robot frame
URDF_MASS = {"biped": 11.34267, "full": 16.33116}  # sum of <mass> in the two URDF files

STAND = {"hip_pitch": -0.2, "knee_pitch": 0.4, "ankle_pitch": -0.3}  # BHL default pose, both legs
ARM_POSE = {"arm_right_shoulder_pitch_joint": 1.374, "arm_right_shoulder_roll_joint": 0.26,
            "arm_right_shoulder_yaw_joint": -0.78, "arm_right_elbow_pitch_joint": -0.196,
            "arm_left_shoulder_pitch_joint": -0.15, "arm_left_elbow_pitch_joint": 0.35}  # from cad/concepts.py

# Payload parts: (name, mass kg, centre x y z in the robot frame, box size x y z for the inertia).
# All masses are ESTIMATES. Names that start with "water" are removed in the "_empty" variants.
PARTS = {
    "A": [  # A v1 (variants_a.py): pan axis moved back to x = -0.06, gun centre 0.10 m in front of it, ~1.4 kg
        ("deck_plate", 0.12, (0.0, 0.0, T + 0.003), (0.15, 0.17, 0.006)),
        ("pan_unit", 0.15, (-0.06, 0.0, T + 0.04), (0.07, 0.11, 0.06)),
        ("tilt_servo", 0.07, (-0.06, 0.067, T + 0.09), (0.04, 0.02, 0.04)),
        ("gun_body_camera", 0.65, (0.04, 0.0, T + 0.125), (0.30, 0.07, 0.12)),
        ("water_gun_tank", 0.45, (0.04, 0.0, T + 0.125), (0.15, 0.068, 0.068)),
    ],
    "A_v0": [  # first version: electric water gun on a 2-servo pan-tilt at x = 0, ~1.4 kg
        ("deck_bracket", 0.20, (0.0, 0.0, T + 0.01), (0.15, 0.17, 0.02)),
        ("pan_servo", 0.07, (0.0, 0.0, T + 0.025), (0.07, 0.07, 0.03)),
        ("tilt_servo", 0.07, (0.0, 0.067, T + 0.09), (0.04, 0.02, 0.04)),
        ("gun_body", 0.60, (0.03, 0.0, T + 0.095), (0.30, 0.07, 0.085)),
        ("water_gun_tank", 0.45, (-0.005, 0.0, T + 0.173), (0.15, 0.068, 0.068)),
        ("camera", 0.05, (0.115, 0.0, T + 0.151), (0.03, 0.04, 0.028)),
    ],
    "B": [  # backpack 1.4 L tank + pump, chest plate, camera-and-nozzle head, ~2.7 kg
        ("bp_frame", 0.30, (-0.11, 0.0, 0.67), (0.11, 0.13, 0.26)),
        ("tank_shell", 0.15, (-0.145, 0.0, 0.643), (0.10, 0.10, 0.18)),
        ("water_tank", 1.40, (-0.145, 0.0, 0.643), (0.10, 0.10, 0.18)),
        ("pump", 0.35, (-0.145, 0.0, 0.816), (0.06, 0.09, 0.035)),
        ("chest_plate", 0.15, (0.078, 0.0, 0.665), (0.008, 0.17, 0.22)),
        ("neck_pan_servo", 0.08, (0.0, 0.0, T + 0.016), (0.06, 0.06, 0.03)),
        ("head_cameras", 0.22, (0.0, 0.0, T + 0.075), (0.09, 0.13, 0.075)),
        ("nozzle", 0.05, (0.085, 0.0, T + 0.075), (0.09, 0.02, 0.02)),
    ],
    "C": [  # full humanoid: 1.0 L backpack, chest plate, helmet head, lance in the right hand, ~2.3 kg
        ("bp_frame", 0.30, (-0.11, 0.0, 0.67), (0.11, 0.13, 0.26)),
        ("tank_shell", 0.12, (-0.145, 0.0, 0.628), (0.09, 0.09, 0.15)),
        ("water_tank", 0.95, (-0.145, 0.0, 0.628), (0.09, 0.09, 0.15)),
        ("pump", 0.35, (-0.145, 0.0, 0.816), (0.06, 0.09, 0.035)),
        ("chest_plate", 0.15, (0.078, 0.0, 0.665), (0.008, 0.17, 0.22)),
        ("helmet_cameras", 0.25, (0.0, 0.0, T + 0.09), (0.16, 0.13, 0.12)),
        ("lance", 0.20, None, (0.15, 0.04, 0.04)),  # position set from the right hand (see LANCE)
    ],
    "D": [  # sealed shell, ~1 L tank at the bottom of the shell, pump, fixed chest nozzle, ~2.3 kg
        ("shell", 0.60, (-0.005, 0.0, 0.69), (0.21, 0.27, 0.26)),
        ("front_visor_cameras", 0.20, (0.095, 0.0, 0.72), (0.02, 0.215, 0.2)),
        ("tank_shell", 0.10, (-0.01, 0.0, 0.60), (0.16, 0.22, 0.05)),
        ("water_tank", 1.00, (-0.01, 0.0, 0.60), (0.16, 0.22, 0.05)),
        ("pump", 0.30, (-0.04, 0.0, 0.66), (0.06, 0.09, 0.035)),
        ("chest_nozzle", 0.08, (0.13, 0.0, 0.665), (0.08, 0.06, 0.06)),
        ("handle_beacon_gauge", 0.05, (-0.04, 0.0, 0.84), (0.1, 0.17, 0.06)),
    ],
    "E": [  # tethered hose (no tank), nozzle + valve on pan-tilt, camera mast, ~1.0 kg + hose drag
        ("deck_bracket", 0.20, (0.0, 0.0, T + 0.01), (0.15, 0.17, 0.02)),
        ("pan_servo", 0.07, (0.0, 0.0, T + 0.025), (0.07, 0.07, 0.03)),
        ("tilt_servo", 0.07, (0.0, 0.067, T + 0.09), (0.04, 0.02, 0.04)),
        ("valve_nozzle", 0.25, (0.03, 0.0, T + 0.095), (0.17, 0.04, 0.045)),
        ("camera_mast_pod", 0.15, (-0.05, 0.07, T + 0.15), (0.05, 0.08, 0.1)),
        ("chest_plate", 0.15, (0.078, 0.0, 0.665), (0.008, 0.17, 0.22)),
        ("hose_on_back_with_water", 0.10, (-0.1, -0.03, 0.68), (0.02, 0.02, 0.3)),
        ("swivel_clamp", 0.06, (-0.09, 0.0, 0.53), (0.05, 0.04, 0.04)),
    ],
}


def real_parts():
    """Round 3: A_real and B_real from the CAD outputs (cad/parts/out, cad/backpack/out and their READMEs)."""
    cad = os.path.normpath(os.path.join(HERE, "../../cad"))
    a = json.load(open(os.path.join(cad, "parts/out/assembly.json")))
    b = json.load(open(os.path.join(cad, "backpack/out/assembly.json")))
    m0, c0 = a["com_no_gun"]["mass_kg"], np.array(a["com_no_gun"]["xyz_m"])
    m1, c1 = a["com_with_gun"]["mass_kg"], np.array(a["com_with_gun"]["xyz_m"])
    gun = (m1 * c1 - m0 * c0) / (m1 - m0)  # gun with water = module with gun minus module without gun
    # splash guard (cad/backpack/README.md): upper panel 45 g at z 0.676-0.790, lower 46 g at z 0.551-0.675,
    # on the front face x = 0.070, 11 mm deep with the lips
    guard = ("splash_guard", 0.091, (0.0755, 0.0, 0.672), (0.011, 0.156, 0.24))
    tk, pu = b["tank"], b["pump"]
    water_h = 0.946e-3 / (np.pi * tk["r"] ** 2)  # 946 mL in the bottle
    backpack = [  # masses from cad/backpack/README.md (print masses at 70 % of solid, bottle and hardware guessed there)
        ("bracket_upper", 0.030, (-0.076, 0.0, 0.781), (0.012, 0.15, 0.02)),
        ("bracket_lower", 0.076, (-0.076, 0.0, 0.660), (0.012, 0.17, 0.044)),
        ("plate", 0.187, (-0.0845, 0.0, 0.688), (0.005, 0.216, 0.2)),
        ("cradle", 0.175, (-0.115, tk["y"], 0.666), (0.072, 0.113, 0.15)),
        ("pump_bracket", 0.034, (-0.0945, pu["y"], 0.690), (0.015, 0.076, 0.096)),
        ("pump", 0.570, (pu["x"], pu["y"], (pu["z0"] + pu["z1"]) / 2), (pu["h"], pu["w"], pu["z1"] - pu["z0"])),
        ("bottle", 0.180, (tk["x"], tk["y"], tk["z0"] + tk["h"] / 2), (2 * tk["r"], 2 * tk["r"], tk["h"])),
        ("water_bottle", 0.946, (tk["x"], tk["y"], tk["z0"] + water_h / 2), (2 * tk["r"], 2 * tk["r"], water_h)),
        ("screws_straps_hose", 0.120, (-0.09, 0.0, 0.69), (0.02, 0.2, 0.2)),
    ]
    head_b = [p for p in PARTS["B"] if p[0] in ("neck_pan_servo", "head_cameras", "nozzle")]  # old B head
    return {
        "A_real": [("top_module_no_gun", m0, tuple(c0), (0.16, 0.13, 0.11)),
                   ("gun_with_water", m1 - m0, tuple(gun), (0.30, 0.07, 0.12)), guard],
        "B_real": backpack + [guard] + head_b,
    }


PARTS.update(real_parts())


def torso_tank_parts():
    """Round 5: R1 (tank inside the torso) and R2 (side tanks) with the TCS M400K-V pump, from
    cad/torso_tank/out/assembly.json. The top is the A_real pan-tilt without the gun, plus a nozzle (estimate)."""
    f = os.path.normpath(os.path.join(HERE, "../../cad/torso_tank/out/assembly.json"))
    if not os.path.exists(f):
        return {}
    a = json.load(open(f))["options"]
    top = [PARTS["A_real"][0], ("nozzle_fitting", 0.03, (0.03, 0.0, 0.905), (0.06, 0.02, 0.02)), PARTS["A_real"][2]]
    out = {}
    for k, o in a.items():
        tank = [(p["name"], p["mass_kg"], tuple(p["com_m"]), tuple(p["size_m"])) for p in o["parts"]]
        for fill, suffix in (("full", ""), ("half", "_half")):
            water = [(w["name"], w["mass_kg"], tuple(w["com_m"]), tuple(w["size_m"])) for w in o["water"][fill]]
            out[k + suffix] = top + tank + water
    return out


PARTS.update(torso_tank_parts())
HOSE_POINT = (-0.115, 0.0, 0.53)  # E: hose connector at the back of the pelvis, robot frame
LANCE_OFFSET = 0.05  # C: lance centre is 5 cm past the hand frame, along the forearm (cad/concepts.py)


def box_inertia(m, s):
    sx, sy, sz = s
    return [m / 12 * (sy * sy + sz * sz), m / 12 * (sx * sx + sz * sz), m / 12 * (sx * sx + sy * sy)]


def lance_local(m):
    """Lance centre in the right-hand body frame: hand + LANCE_OFFSET along elbow->hand, in ARM_POSE."""
    d = mujoco.MjData(m)
    d.qpos[3] = 1
    for j, v in ARM_POSE.items():
        d.joint(j).qpos = v
    mujoco.mj_kinematics(m, d)
    hand, elbow = d.body("arm_right_hand_link"), d.body("arm_right_elbow_pitch")
    u = hand.xpos - elbow.xpos
    return hand.xmat.reshape(3, 3).T @ (u / np.linalg.norm(u) * LANCE_OFFSET)


def base_spec(kind):
    f = "berkeley_humanoid_lite_biped.xml" if kind == "biped" else "berkeley_humanoid_lite.xml"
    s = mujoco.MjSpec.from_file(os.path.join(BHL, "mjcf", f))
    s.meshdir = os.path.join(BHL, "meshes")  # the original says meshdir="assets" and file="merged/..."
    for mesh in s.meshes:
        mesh.file = mesh.file.replace("merged/", "")
    if kind == "biped":
        # base_visual.stl is the full-robot torso. The biped MJCF places it at the biped base CoM, 3.7 cm
        # too low (the same error as the biped URDF). Use the full MJCF placement. Visual only.
        g = next(g for g in s.body("base").geoms if g.meshname == "base_visual")
        g.pos = [-0.0030965, 0.000264765, 0.675059]
    s.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05], rgba=[0.3, 0.35, 0.4, 1])
    s.worldbody.add_light(pos=[0, 0, 2.5], dir=[0, 0, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL)
    return s


def build(concept=None, empty=False):
    """MjSpec for 'biped', 'full' or a concept A-E (empty=True removes the water)."""
    kind = "full" if concept in ("C", "full") else "biped"
    s = base_spec(kind)
    s.modelname = f"bhl_{concept or kind}" + ("_empty" if empty else "")
    if concept in PARTS:
        lance = lance_local(s.compile()) if concept == "C" else None
        for name, mass, pos, size in PARTS[concept]:
            if empty and name.startswith("water"):
                continue
            if name == "lance":
                parent, p = s.body("arm_right_hand_link"), lance
            else:
                parent, p = s.body("base"), [pos[0], pos[1], pos[2] + Z0]
            b = parent.add_body(name=f"payload_{name}", pos=p)
            b.mass, b.ipos, b.inertia, b.explicitinertial = mass, [0, 0, 0], box_inertia(mass, size), True
            rgba = [0.25, 0.55, 0.9, 0.6] if name.startswith("water") else [0.85, 0.2, 0.1, 1]
            b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[v / 2 for v in size], contype=0, conaffinity=0,
                       group=1, mass=0, rgba=rgba)
        if concept == "E":
            s.body("base").add_site(name="hose_connector", pos=[HOSE_POINT[0], HOSE_POINT[1], HOSE_POINT[2] + Z0])
    return s


VARIANTS = {"biped": ("biped", False), "full": ("full", False), "A": ("A", False), "A_v0": ("A_v0", False),
            "A_real": ("A_real", False), "B_real": ("B_real", False), "B_real_empty": ("B_real", True),
            "B": ("B", False),
            "B_empty": ("B", True), "C": ("C", False), "C_empty": ("C", True), "D": ("D", False),
            "D_empty": ("D", True), "E": ("E", False)}
VARIANTS.update({v: (v.replace("_empty", ""), v.endswith("_empty")) for k in ("R1", "R2") if k in PARTS
                 for v in (k, f"{k}_half", f"{k}_empty")})


def path(variant):
    return os.path.join(OUT, f"bhl_{variant}.xml")


def load(variant):
    return mujoco.MjModel.from_xml_path(path(variant))


def write_all():
    os.makedirs(OUT, exist_ok=True)
    from poses import stand_qpos  # local import: poses.py imports this module
    for v, (c, empty) in VARIANTS.items():
        s = build(c, empty)
        m = s.compile()
        s.add_key(name="stand", qpos=stand_qpos(m, STAND), ctrl=np.zeros(m.nu))  # feet flat, 1 mm above the floor
        with open(path(v), "w") as f:  # relative mesh path, so the file works from any working directory
            f.write(s.to_xml().replace(f'meshdir="{s.meshdir}', f'meshdir="{MESHDIR}'))


def payload_mass(concept, empty=False):
    return sum(m for n, m, _, _ in PARTS[concept] if not (empty and n.startswith("water")))


def self_check():
    for v, (c, empty) in VARIANTS.items():
        m = load(v)
        bare = URDF_MASS["full" if c in ("C", "full") else "biped"]
        expect = bare + (payload_mass(c, empty) if c in PARTS else 0)
        got = m.body_subtreemass[1]
        assert abs(got - expect) < 1e-3, (v, got, expect)
        assert m.nkey == 1 and m.nu == (22 if c in ("C", "full") else 12), v
    print("self-check models: masses match URDF + payload table, keyframe present")


if __name__ == "__main__":
    write_all()
    self_check()
    for v in VARIANTS:
        print(f"{v:8s} total mass {load(v).body_subtreemass[1]:6.2f} kg  -> {os.path.relpath(path(v), HERE)}")
