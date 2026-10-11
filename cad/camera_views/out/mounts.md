## Table 4. Camera pose per concept, current and recommended

Goal: no robot part in the central 60 % of the image, floor seen from 0.85 m or closer (about 0.8 m) to at least 5 m, from the robot origin.
Lens = front of the RGB lens. Part frame = the gun (A), head (B) or pod (E) frame at its default tilt, x forward, z up.
Tilt = camera angle below horizontal. The gun, head or pod keeps its default tilt, so the camera needs its own pitch on it.

| Concept | Pose | HFOV | Lens, part frame (m) | Move (m) | Lens, robot frame (m) | Tilt | Pitch on part | Robot in centre 60 % | Robot in image | Near floor (m) | Far floor (m) | Goal met |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | current | 90 deg | (+0.140, +0.000, +0.056) | (+0.000, +0.000, +0.000) | (+0.145, +0.000, +0.927) | 6 deg | +0 deg | 2% | 4% | 2.66 | horizon | no |
| A | recommended | 90 deg | (+0.140, -0.040, -0.024) | (+0.000, -0.040, -0.080) | (+0.137, -0.040, +0.847) | 22 deg | +16 deg | 0% | 5% | 0.81 | horizon | yes |
| A | current | 60 deg | (+0.140, +0.000, +0.056) | (+0.000, +0.000, +0.000) | (+0.145, +0.000, +0.927) | 6 deg | +0 deg | 0% | 2% | 2.64 | horizon | no |
| A | recommended | 60 deg | (+0.140, -0.080, +0.016) | (+0.000, -0.080, -0.040) | (+0.141, -0.080, +0.887) | 28 deg | +22 deg | 0% | 1% | 1.00 | 5.17 | no |
| B | current | 90 deg | (+0.059, +0.028, +0.012) | (+0.000, +0.000, +0.000) | (+0.060, +0.028, +0.873) | 5 deg | +0 deg | 12% | 18% | 1.34 | horizon | no |
| B | recommended | 90 deg | (+0.059, +0.028, -0.028) | (+0.000, +0.000, -0.040) | (+0.056, +0.028, +0.833) | 18 deg | +13 deg | 0% | 0% | 0.82 | horizon | yes |
| B | current | 60 deg | (+0.059, +0.028, +0.012) | (+0.000, +0.000, +0.000) | (+0.060, +0.028, +0.873) | 5 deg | +0 deg | 2% | 11% | 2.12 | horizon | no |
| B | recommended | 60 deg | (+0.059, +0.028, -0.028) | (+0.000, +0.000, -0.040) | (+0.056, +0.028, +0.833) | 26 deg | +21 deg | 0% | 0% | 0.92 | 5.98 | no |
| B, nozzle at (+0.000, -0.050) | current | 90 deg | (+0.059, +0.028, +0.012) | (+0.000, +0.000, +0.000) | (+0.060, +0.028, +0.873) | 5 deg | +0 deg | 0% | 0% | 1.34 | horizon | no |
| B, nozzle at (+0.000, -0.050) | recommended | 90 deg | (+0.059, +0.028, +0.012) | (+0.000, +0.000, +0.000) | (+0.060, +0.028, +0.873) | 20 deg | +15 deg | 0% | 1% | 0.81 | horizon | yes |
| B, nozzle at (+0.000, -0.050) | recommended | 60 deg | (+0.059, +0.028, +0.012) | (+0.000, +0.000, +0.000) | (+0.060, +0.028, +0.873) | 28 deg | +23 deg | 0% | 2% | 0.90 | 5.01 | no |
| E | current | 90 deg | (+0.035, +0.018, +0.000) | (+0.000, +0.000, +0.000) | (-0.015, +0.088, +0.962) | 6 deg | +0 deg | 0% | 2% | 1.34 | horizon | no |
| E | recommended | 90 deg | (+0.035, +0.058, +0.000) | (+0.000, +0.040, +0.000) | (-0.015, +0.128, +0.962) | 20 deg | +14 deg | 0% | 3% | 0.81 | horizon | yes |
| E | current | 60 deg | (+0.035, +0.018, +0.000) | (+0.000, +0.000, +0.000) | (-0.015, +0.088, +0.962) | 6 deg | +0 deg | 0% | 0% | 2.15 | horizon | no |
| E | recommended | 60 deg | (+0.035, +0.058, -0.040) | (+0.000, +0.040, -0.040) | (-0.019, +0.128, +0.923) | 28 deg | +22 deg | 0% | 0% | 0.87 | 5.21 | no |

## Table 5. Nozzle place on concept B, cameras at the current pose

Nozzle axis (y, z) in the head frame. The current nozzle is at (0, 0), 12 mm under the camera axis.
Values are the share of the image that shows robot parts. Thermal = 56 x 42 deg lens at the thermal camera place.

| Nozzle (y, z) (m) | RGB 90 deg | RGB 60 deg | Thermal 56 x 42 deg |
|---|---|---|---|
| (+0.000, +0.000) | 18% | 11% | 35% |
| (+0.000, -0.020) | 5% | 0% | 1% |
| (+0.000, -0.035) | 0% | 0% | 0% |
| (+0.000, -0.050) | 0% | 0% | 0% |
| (+0.010, +0.000) | 22% | 22% | 21% |
| (+0.010, -0.020) | 4% | 0% | 1% |
| (+0.010, -0.035) | 0% | 0% | 0% |
| (+0.010, -0.050) | 0% | 0% | 0% |
| (-0.050, +0.000) | 1% | 0% | 1% |
| (-0.050, -0.020) | 1% | 0% | 0% |
| (-0.050, -0.035) | 0% | 0% | 0% |
| (-0.050, -0.050) | 0% | 0% | 0% |
