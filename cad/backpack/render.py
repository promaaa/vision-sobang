"""Render the splash guard and the concept B backpack on the robot (Blender 5.2, Cycles OptiX).

    blender -b --factory-startup -P cad/backpack/render.py -- cad/backpack/renders

Run body.py first: it writes the STLs and out/assembly.json.
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import bhl  # noqa: E402
import concepts  # noqa: E402
from concepts import M  # noqa: E402

OUT = os.path.join(HERE, "out")
PRINTED = {"guard_upper": "red", "guard_lower": "red", "bracket_upper": "orange", "bracket_lower": "orange",
           "plate": "orange", "cradle": "orange", "pump_bracket": "orange"}


def stl(name, m):
    bpy.ops.wm.stl_import(filepath=os.path.join(OUT, f"{name}.stl"))
    o = bpy.context.selected_objects[0]
    o.scale = (0.001, 0.001, 0.001)
    o.data.materials.append(m)
    return o


def main(out):
    concepts.scene()
    robot, _ = concepts.robot()
    parts = [stl(n, M[c]) for n, c in PRINTED.items()]
    a = json.load(open(os.path.join(OUT, "assembly.json")))
    t, p = a["tank"], a["pump"]
    tx, ty, tz, r, h = t["x"], t["y"], t["z0"], t["r"], t["h"] - 0.02  # bottle body without the cap
    bhl.cyl("tank", r, h, (tx, ty, tz + h / 2), M["clear"], bevel=0.006)
    bhl.cyl("water", r - 0.003, h * 0.85, (tx, ty, tz + 0.003 + h * 0.425), M["water"], bevel=0.003)
    bhl.cyl("tank_cap", 0.032, 0.02, (tx, ty, tz + h + 0.01), M["red"])
    for dz in (0.035, 0.130):  # hook-and-loop straps at the saddles
        bhl.cyl("strap", r + 0.002, 0.025, (tx, ty, tz + dz), M["black"], bevel=0.001)
    pz = (p["z0"] + p["z1"]) / 2
    bhl.box("pump_head", (p["h"], p["w"], 0.05), (p["x"], p["y"], p["z0"] + 0.025), M["black"], bevel=0.006)
    bhl.cyl("pump_motor", 0.027, p["z1"] - p["z0"] - 0.05, (p["x"], p["y"], pz + 0.025), M["alu"])
    inlet = (p["x"], p["y"] + p["w"] / 2 + 0.01, p["z0"] + 0.02)
    outlet = (p["x"], p["y"] - p["w"] / 2 - 0.01, p["z0"] + 0.02)
    cap = (t["x"], t["y"], t["z0"] + t["h"] + 0.01)
    bhl.tube("feed", [cap, (t["x"], t["y"] - 0.03, cap[2] + 0.03), (t["x"] - 0.03, 0.0, 0.70), (inlet[0] - 0.02, inlet[1] + 0.02, inlet[2] - 0.03), inlet], 0.006, M["hose"])
    bhl.tube("hose", [outlet, (outlet[0] - 0.02, outlet[1] - 0.02, outlet[2] + 0.05), (p["x"] - 0.04, -0.11, 0.78), (-0.09, -0.09, 0.83), (-0.03, -0.06, 0.84)], 0.006, M["hose"])
    body = bhl.corners(list(robot.values()) + parts)
    res = (1200, 1500)
    bhl.fit(body, -35, 10, 70, res)
    bhl.render(f"{out}/front.png", samples=96)
    bhl.fit(body, -145, 16, 70, res)
    bhl.render(f"{out}/rear.png", samples=96)
    box = [(x, y, z) for x in (-0.19, 0.09) for y in (-0.12, 0.12) for z in (0.54, 0.83)]
    bhl.fit(box, -125, 22, 70, (1400, 1200), margin=1.02)
    bhl.render(f"{out}/rear_detail.png", samples=96)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1])
