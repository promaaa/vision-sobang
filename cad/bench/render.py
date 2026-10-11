"""Blender renders of the bench rig: front 3/4 and top view.

blender -b --factory-startup -P cad/bench/render.py -- <bhl_dir> cad/bench/renders

Uses cad/bhl.py (studio, fit, render) and cad/parts/render_module.py (module import, gun stand-in).
Reads cad/bench/out/ (bench.py) and cad/parts/out_sts3215/ (top_module_sts3215.py).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["PARTS_DIR"] = "out_sts3215"
sys.path[:0] = [os.path.join(os.path.dirname(HERE), "parts"), os.path.dirname(HERE)]
import bhl  # noqa: E402
import render_module as rm  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 2]
B = json.load(open(os.path.join(HERE, "out", "bench.json")))
LIFT = B["h_base_mm"] / 1000          # bench z = 0 (rail top) above the table (studio floor)


def stl(path, m, name):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.name = name
    o.data.materials.append(m)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
    o.matrix_world = Matrix.Translation((0, 0, LIFT)) @ Matrix.Scale(0.001, 4)
    return o


def mm(*p):
    return tuple(v / 1000 for v in p[:2]) + (p[2] / 1000 + LIFT,)


def build():
    """Studio, module, gun stand-in, bench parts, e-stop and hoses. Returns the objects to frame."""
    bhl.clear()
    bhl.studio()
    M = rm.materials()
    M["hose"] = bhl.mat("hose", (0.85, 0.45, 0.02), rough=0.6)
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    objs = rm.load_module(M, (0, 0, LIFT), gun=False) + rm.gun_standin(M, (0, 0, LIFT), rm.TILT_DEG)
    d = os.path.join(HERE, "out")
    for n in ("base_clamp", "tray", "cradle", "ebox", "ebox_lid"):
        objs.append(stl(os.path.join(d, n + ".stl"), M["pla"] if n.startswith("ebox") else M["part"], n))
    for n, m in (("ref_rail_r", M["steel"]), ("ref_rail_f", M["steel"]), ("ref_bottle", M["water"]), ("ref_pump", M["black"])):
        objs.append(stl(os.path.join(d, "ref", n + ".stl"), m, n))
    e = B["estop_xyz_mm"]
    bhl.cyl("estop", 0.02, 0.012, mm(e[0], e[1], e[2] + 6), M["red"])
    bhl.cyl("estop_ring", 0.015, 0.006, mm(e[0], e[1], e[2]), M["yellow"])
    bx, by = B["bottle_xy_mm"]
    px, py, pz = B["pump_xyz_mm"]
    bhl.tube("hose_in", [mm(bx, by, B["bottle_top_z_mm"] + 5), mm(bx + 30, by - 20, B["bottle_top_z_mm"] + 30),
                         mm(px - 20, py + 95, pz + 10), mm(px, py + 90, pz)], 0.005, M["hose"])
    bhl.tube("hose_out", [mm(px, py - 90, pz), mm(px + 20, py - 110, pz + 20), mm(-60, -70, 60), mm(-40, -40, 110)], 0.005, M["hose"])
    return objs


if __name__ == "__main__":
    objs = build()
    pts = bhl.corners(objs)
    bhl.fit(pts, -35, 18, 70, (1600, 1200), margin=1.06)
    bhl.render(f"{OUT}/bench_front.jpg", samples=96)
    bhl.fit(pts, -90, 88, 70, (1600, 1200), margin=1.04)
    bhl.render(f"{OUT}/bench_top.jpg", samples=96)
