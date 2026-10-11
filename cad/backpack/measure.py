"""Measure the front and rear faces of the BHL torso mesh (numbers used in body.py and the README).

    cad/backpack/.venv/bin/python cad/backpack/measure.py

Places base_visual.stl with the base visual origin of the FULL URDF, shifts it down 39 mm like
cad/concepts.py, splits it into connected parts and prints the parts that touch the front
(x > 30 mm) or rear (x < -30 mm) faces, then one plane section through the front left post.
"""
from pathlib import Path

import numpy as np
import trimesh

BHL = Path(__file__).parent.parent.parent / "third_party/berkeley-humanoid-lite-assets/data/robots/berkeley_humanoid/berkeley_humanoid_lite"

m = trimesh.load(BHL / "meshes/base_visual.stl")
m.apply_translation([-0.0030965, 0.000264765, 0.675059 - 0.039])  # full URDF base visual origin, then the shift
m.apply_scale(1000)
m.merge_vertices()
print("torso bounds mm", np.round(m.bounds, 1).tolist())
for p in sorted(m.split(only_watertight=False), key=lambda p: -np.prod(p.extents)):
    lo, hi = p.bounds
    if np.prod(p.extents) > 2000 and (hi[0] > 30 or lo[0] < -30):
        print("part x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
# profile of the front left post at z = 700: slot opening, lip and cavity
for d in m.section(plane_origin=[0, 0, 700], plane_normal=[0, 0, 1]).discrete:
    if d[:, 0].min() > 45 and d[:, 1].min() > 50 and len(d) > 300:
        face = d[np.isclose(d[:, 0], 70.0, atol=0.05)][:, 1]  # points on the front face x = 70
        print("post z=700 front face points y:", np.round(np.unique(np.round(face, 1)), 1).tolist())
