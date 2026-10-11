## Table 1. Floor in view, RGB camera at 1280x720 (rendered set)

Distances are along the image centre column, in metres from the robot origin (the floor point between the feet).
Toes: A 0.14 m, B 0.14 m, E 0.14 m, C 0.14 m, D 0.14 m.

| Concept | Tilt down | Lens height (m) | HFOV x VFOV | Near floor, analytic | Near floor, ray cast | Far floor | Robot in image |
|---|---|---|---|---|---|---|---|
| A | 6 deg | 0.93 | 60 x 36 deg | 2.23 | 2.64 (robot in the way) | horizon | 2% |
| A | 6 deg | 0.93 | 90 x 59 deg | 1.45 | 2.66 (robot in the way) | horizon | 4% |
| A | 6 deg | 0.93 | 120 x 89 deg | 0.92 | 2.66 (robot in the way) | horizon | 6% |
| A | 20 deg | 0.89 | 60 x 36 deg | 1.29 | 1.45 (robot in the way) | 25.55 | 2% |
| A | 20 deg | 0.89 | 90 x 59 deg | 0.92 | 1.46 (robot in the way) | horizon | 4% |
| A | 20 deg | 0.89 | 120 x 89 deg | 0.58 | 1.46 (robot in the way) | horizon | 6% |
| B | 5 deg | 0.87 | 60 x 36 deg | 2.12 | 2.12 | horizon | 11% |
| B | 5 deg | 0.87 | 90 x 59 deg | 1.34 | 1.34 | horizon | 18% |
| B | 5 deg | 0.87 | 120 x 89 deg | 0.81 | 0.81 | horizon | 17% |
| B | 20 deg | 0.86 | 60 x 36 deg | 1.16 | 1.16 | 24.50 | 11% |
| B | 20 deg | 0.86 | 90 x 59 deg | 0.80 | 0.80 | horizon | 18% |
| B | 20 deg | 0.86 | 120 x 89 deg | 0.47 | 0.47 | horizon | 17% |
| E | 6 deg | 0.96 | 60 x 36 deg | 2.15 | 2.15 | horizon | 0% |
| E | 6 deg | 0.96 | 90 x 59 deg | 1.34 | 1.34 | horizon | 2% |
| E | 6 deg | 0.96 | 120 x 89 deg | 0.79 | 0.79 | horizon | 3% |
| E | 20 deg | 0.95 | 60 x 36 deg | 1.20 | 1.20 | 27.19 | 3% |
| E | 20 deg | 0.95 | 90 x 59 deg | 0.80 | 0.80 | horizon | 6% |
| E | 20 deg | 0.95 | 120 x 89 deg | 0.44 | 0.49 (robot in the way) | horizon | 11% |
| C | 0 deg | 0.86 | 60 x 36 deg | 2.74 | 2.74 | horizon | 0% |
| C | 0 deg | 0.86 | 90 x 59 deg | 1.62 | 1.62 | horizon | 1% |
| C | 0 deg | 0.86 | 120 x 89 deg | 0.97 | 0.97 | horizon | 4% |
| C | 20 deg | 0.86 | 60 x 36 deg | 1.19 | 1.19 | 24.69 | 4% |
| C | 20 deg | 0.86 | 90 x 59 deg | 0.82 | 0.82 | horizon | 7% |
| C | 20 deg | 0.86 | 120 x 89 deg | 0.50 | 0.50 | horizon | 9% |
| D | 0 deg | 0.79 | 60 x 36 deg | 2.54 | 2.54 | horizon | 0% |
| D | 0 deg | 0.79 | 90 x 59 deg | 1.52 | 1.52 | horizon | 0% |
| D | 0 deg | 0.79 | 120 x 89 deg | 0.93 | 0.93 | horizon | 0% |
| D | 20 deg | 0.79 | 60 x 36 deg | 1.13 | 1.13 | 22.51 | 0% |
| D | 20 deg | 0.79 | 90 x 59 deg | 0.79 | 0.79 | horizon | 0% |
| D | 20 deg | 0.79 | 120 x 89 deg | 0.50 | 0.50 | horizon | 0% |

## Table 2. Blind zone and far floor for every sensor (analytic, no robot parts)

Cell: near floor / far floor, metres from the robot origin. Same lens position as the RGB camera.

| Sensor | HFOV x VFOV | A 6 deg | A 20 deg | B 5 deg | B 20 deg | C 0 deg | C 20 deg | D 0 deg | D 20 deg | E 6 deg | E 20 deg |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MLX90640 BAB (narrow) | 55 x 35 deg | 2.28 / horizon | 1.31 / 20.55 | 2.17 / horizon | 1.18 / 19.69 | 2.82 / horizon | 1.21 / 19.85 | 2.61 / horizon | 1.14 / 18.10 | 2.20 / horizon | 1.23 / 21.83 |
| MLX90640 BAA (wide) | 110 x 75 deg | 1.12 / horizon | 0.72 / horizon | 1.01 / horizon | 0.61 / horizon | 1.21 / horizon | 0.63 / horizon | 1.14 / horizon | 0.62 / horizon | 1.00 / horizon | 0.59 / horizon |
| FLIR Lepton 2.5 | 50 x 39 deg | 2.11 / horizon | 1.24 / > 30 | 2.00 / horizon | 1.11 / > 30 | 2.55 / horizon | 1.14 / > 30 | 2.36 / horizon | 1.08 / > 30 | 2.02 / horizon | 1.15 / > 30 |
| FLIR Lepton 3.5 | 57 x 44 deg | 1.88 / horizon | 1.13 / horizon | 1.76 / horizon | 1.01 / horizon | 2.20 / horizon | 1.03 / horizon | 2.05 / horizon | 0.99 / horizon | 1.78 / horizon | 1.04 / horizon |
| FLIR Lepton 3.1R (wide) | 95 x 79 deg | 1.06 / horizon | 0.68 / horizon | 0.95 / horizon | 0.57 / horizon | 1.14 / horizon | 0.59 / horizon | 1.08 / horizon | 0.59 / horizon | 0.94 / horizon | 0.55 / horizon |
| 256x192 USB (TOPDON TC001) | 56 x 42 deg | 1.96 / horizon | 1.18 / horizon | 1.85 / horizon | 1.05 / horizon | 2.33 / horizon | 1.07 / horizon | 2.16 / horizon | 1.02 / horizon | 1.87 / horizon | 1.08 / horizon |
| RGB 640x480 | 60 x 47 deg | 1.79 / horizon | 1.09 / horizon | 1.67 / horizon | 0.97 / horizon | 2.07 / horizon | 0.99 / horizon | 1.93 / horizon | 0.95 / horizon | 1.69 / horizon | 0.99 / horizon |
| RGB 640x480 | 90 x 74 deg | 1.14 / horizon | 0.73 / horizon | 1.03 / horizon | 0.62 / horizon | 1.23 / horizon | 0.64 / horizon | 1.17 / horizon | 0.63 / horizon | 1.02 / horizon | 0.61 / horizon |
| RGB 640x480 | 120 x 105 deg | 0.72 / horizon | 0.43 / horizon | 0.62 / horizon | 0.33 / horizon | 0.75 / horizon | 0.35 / horizon | 0.72 / horizon | 0.37 / horizon | 0.58 / horizon | 0.29 / horizon |
| RGB 1280x720 | 60 x 36 deg | 2.23 / horizon | 1.29 / 25.55 | 2.12 / horizon | 1.16 / 24.50 | 2.74 / horizon | 1.19 / 24.69 | 2.54 / horizon | 1.13 / 22.51 | 2.15 / horizon | 1.20 / 27.19 |
| RGB 1280x720 | 90 x 59 deg | 1.45 / horizon | 0.92 / horizon | 1.34 / horizon | 0.80 / horizon | 1.62 / horizon | 0.82 / horizon | 1.52 / horizon | 0.79 / horizon | 1.34 / horizon | 0.80 / horizon |
| RGB 1280x720 | 120 x 89 deg | 0.92 / horizon | 0.58 / horizon | 0.81 / horizon | 0.47 / horizon | 0.97 / horizon | 0.50 / horizon | 0.93 / horizon | 0.50 / horizon | 0.79 / horizon | 0.44 / horizon |

## Table 3. Size of a 20 cm wide, 25 cm tall fire in pixels (width x height)

Pinhole model, fire at the image centre. **Bold** = fewer than 3 pixels in width or height.

| Sensor | Pixels | HFOV x VFOV | Source | 1 m | 2 m | 3 m | 5 m | 8 m |
|---|---|---|---|---|---|---|---|---|
| MLX90640 BAB (narrow) | 32x24 | 55 x 35 deg | [1] | 6.1 x 9.5 | 3.1 x 4.8 | **2.0 x 3.2** | **1.2 x 1.9** | **0.8 x 1.2** |
| MLX90640 BAA (wide) | 32x24 | 110 x 75 deg | [1] | **2.2 x 3.9** | **1.1 x 2.0** | **0.7 x 1.3** | **0.4 x 0.8** | **0.3 x 0.5** |
| FLIR Lepton 2.5 | 80x60 | 50 x 39 deg | [2] (VFOV computed) | 17.2 x 21.4 | 8.6 x 10.7 | 5.7 x 7.1 | 3.4 x 4.3 | **2.1 x 2.7** |
| FLIR Lepton 3.5 | 160x120 | 57 x 44 deg | [2] (VFOV computed) | 29.5 x 36.8 | 14.7 x 18.4 | 9.8 x 12.3 | 5.9 x 7.4 | 3.7 x 4.6 |
| FLIR Lepton 3.1R (wide) | 160x120 | 95 x 79 deg | [2] (VFOV computed) | 14.7 x 18.3 | 7.3 x 9.2 | 4.9 x 6.1 | **2.9 x 3.7** | **1.8 x 2.3** |
| 256x192 USB (TOPDON TC001) | 256x192 | 56 x 42 deg | [3] | 48.1 x 62.5 | 24.1 x 31.3 | 16.0 x 20.8 | 9.6 x 12.5 | 6.0 x 7.8 |
| RGB 640x480 | 640x480 | 60 x 47 deg |  (VFOV computed) | 110.9 x 138.6 | 55.4 x 69.3 | 37.0 x 46.2 | 22.2 x 27.7 | 13.9 x 17.3 |
| RGB 640x480 | 640x480 | 90 x 74 deg |  (VFOV computed) | 64.0 x 80.0 | 32.0 x 40.0 | 21.3 x 26.7 | 12.8 x 16.0 | 8.0 x 10.0 |
| RGB 640x480 | 640x480 | 120 x 105 deg |  (VFOV computed) | 37.0 x 46.2 | 18.5 x 23.1 | 12.3 x 15.4 | 7.4 x 9.2 | 4.6 x 5.8 |
| RGB 1280x720 | 1280x720 | 60 x 36 deg |  (VFOV computed) | 221.7 x 277.1 | 110.9 x 138.6 | 73.9 x 92.4 | 44.3 x 55.4 | 27.7 x 34.6 |
| RGB 1280x720 | 1280x720 | 90 x 59 deg |  (VFOV computed) | 128.0 x 160.0 | 64.0 x 80.0 | 42.7 x 53.3 | 25.6 x 32.0 | 16.0 x 20.0 |
| RGB 1280x720 | 1280x720 | 120 x 89 deg |  (VFOV computed) | 73.9 x 92.4 | 37.0 x 46.2 | 24.6 x 30.8 | 14.8 x 18.5 | 9.2 x 11.5 |

Self-check: 23 ray casts matched the analytic blind zone within 2 cm, e.g. B 5 deg 60 deg: 2.117 vs 2.117 m, B 5 deg 90 deg: 1.337 vs 1.337 m, B 5 deg 120 deg: 0.812 vs 0.812 m.
