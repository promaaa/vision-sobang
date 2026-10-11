"""Turntable videos: concept A with the STS3215 module, and the bench rig.

blender -b --factory-startup -P cad/turntable/turntable.py -- <bhl_dir> cad/turntable [concept_A bench]

One full turn in 144 frames (6 s at 24 fps), 1280 x 720, Cycles 12 samples + denoise. The frames go to a
temporary folder; ffmpeg encodes them to H.264 MP4. Frame 1 is also saved as a JPG still.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
os.environ["PARTS_DIR"] = "out_sts3215"
sys.path[:0] = [os.path.join(CAD, "bench"), os.path.join(CAD, "parts"), CAD]
import bhl  # noqa: E402
import render as bench  # noqa: E402  cad/bench/render.py
import render_module as rm  # noqa: E402  cad/parts/render_module.py

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[1]
WHICH = args[2:] or ["concept_A", "bench"]
FRAMES, FPS, RES, SAMPLES = int(os.environ.get("TT_FRAMES", 144)), 24, (1280, 720), 12


def concept_a():
    """Legs-only BHL, STS3215 module on the torso, gun stand-in, splash guard of cad/backpack."""
    bhl.clear()
    bhl.studio()
    M = rm.materials()
    objs = list(rm.robot(M).values())
    objs += rm.load_module(M, (0, 0, rm.T), gun=False) + rm.gun_standin(M, (0, 0, rm.T), 6)
    for n in ("guard_upper", "guard_lower"):      # robot frame, mm, feet on the floor
        bpy.ops.wm.stl_import(filepath=os.path.join(CAD, "backpack", "out", n + ".stl"))
        o = bpy.context.selected_objects[0]
        o.data.materials.append(M["red"])
        o.matrix_world = Matrix.Scale(0.001, 4)
        objs.append(o)
    return objs


def turntable(objs, name, elev, lens):
    sc = bpy.context.scene
    pts = bhl.corners(objs)
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    pivot = bpy.data.objects.new("turntable", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (cx, cy, 0)
    bpy.context.view_layer.update()
    keep = {"floor", "rig", "turntable"}
    for o in list(bpy.data.objects):
        if o.parent is None and o.name not in keep and o.type in ("MESH", "CURVE", "EMPTY"):
            mw = o.matrix_world.copy()
            o.parent = pivot
            o.matrix_world = mw
    ring = [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a), z)
            for x, y, z in pts for a in [i * math.pi / 8 for i in range(16)]]
    bhl.fit(ring, -35, elev, lens, RES, margin=1.04)
    sc.frame_start, sc.frame_end, sc.render.fps = 1, FRAMES, FPS
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"   # constant turn speed
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert("rotation_euler", index=2, frame=1)
    pivot.rotation_euler = (0, 0, 2 * math.pi)
    pivot.keyframe_insert("rotation_euler", index=2, frame=144 + 1)
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = "JPEG"
    bhl.render(f"{OUT}/{name}.jpg", RES, samples=SAMPLES)           # still (frame 1), also sets up Cycles
    tmp = tempfile.mkdtemp(prefix=f"tt_{name}_", dir=os.environ.get("TMPDIR"))
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(tmp, "f")
    bpy.ops.render.render(animation=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26", "-preset", "slow",
                    os.path.join(OUT, f"{name}.mp4")], check=True)
    shutil.rmtree(tmp)
    print(name, os.path.getsize(os.path.join(OUT, f"{name}.mp4")) / 1e6, "MB")


for key in WHICH:
    if key == "concept_A":
        turntable(concept_a(), "concept_A_turntable", 8, 60)
    elif key == "bench":
        turntable(bench.build(), "bench_turntable", 20, 60)
