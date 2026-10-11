# CAD concepts

Blender scripts that build the five body concepts (A to E) and render them.
The legs, torso and arms are the real Berkeley Humanoid Lite meshes.
All added parts (gun, tanks, pumps, heads, shell) are placeholder shapes with approximate sizes.

Status: planned. Nothing here is built.

## Files

- `bhl.py`: places the Berkeley meshes from the URDF, adds simple shapes, sets up the studio, frames the camera and renders.
- `concepts.py`: the five concepts and the render views (front, rear, close-up, group picture).
- `renders/`: the rendered images (JPG).

## Run

1. When the `third_party/` folder is missing, fetch the Berkeley assets: `scripts/fetch_bhl_assets.sh`
2. Render all concepts (about 5 minutes on an RTX 3090): `blender -b --factory-startup -P cad/concepts.py -- /tmp/renders`
3. Render one concept only: `blender -b --factory-startup -P cad/concepts.py -- /tmp/renders A`

Other Blender scripts can import the concepts:

```python
import sys; sys.path.insert(0, "cad")
import concepts
concepts.scene()
root = concepts.build("A")
```

## Notes

- Robot frame: x forward, y left, z up, metres. The feet touch the floor (z = 0) in the default standing pose (hip −0.2, knee 0.4, ankle −0.3 rad).
- The leg-only URDF places the torso mesh 3.7 cm too low. The scripts use the full URDF and leave out the arms.
- The torso mesh includes the shoulder motors. The scripts delete them for the concepts without arms.
- Berkeley meshes: CC BY-SA 4.0. Renders that show them must credit the Berkeley Humanoid Lite team and use the same licence.
