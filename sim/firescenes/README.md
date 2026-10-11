# Synthetic fire scenes for the fire detector

This folder makes test images for Marc's fire detector.
Each image shows what the concept A camera could see: rooms or outdoor ground, 1 to 3 fires, and things that look like fire.
Each sample has an RGB image, a thermal-like image and labels.

**Not verified:** Nobody has compared these images with real camera images. Read "Domain gap" before you use them.
**Assumed:** The camera pose is the concept A RGB camera in `aim/geometry.py`, with the gun at its default tilt (6 deg down).
**Not done:** In samples 0 to 249 and in the sequence, the robot body is not in the scene. Only samples g00000 to g00019 show the gun (see "Samples with the gun in view").
**Different from the gun brief:** The gun barrel is in the top-left corner of the image, not at the bottom. This follows from the CAD camera pose (see "Samples with the gun in view").

## Status

- Built: `firescenes.py` (scene generator), `validate.py` (label check), 250 samples (0 to 249), 20 samples with the gun (g00000 to g00019), one 10 s sequence and a contact sheet.
- All samples and the sequence come from the same script version, with deci-kelvin thermal files and no flame shadows.
- Tested in simulation: the label check (see "Label check").
- Measured on laptop, measured on board: nothing.

## Terms

- RGB image: a normal colour image.
- Thermal image: an image where each pixel value is a temperature.
- Deci-kelvin (dK): 1/10 of a kelvin. 2982 dK = 298.2 K = 25 deg C. A 16-bit value holds up to 6553.5 K, so flames do not clip.
- YOLO format: one text file for each image. Each line is `class x_centre y_centre width height`, all divided by the image size. Class 0 is "fire".
- Box: the smallest rectangle around the visible part of a fire, in pixels: (u_min, v_min, u_max, v_max). u goes right, v goes down, (0, 0) is the top-left corner.
- Robot frame: x forward, y left, z up, metres. The origin is the floor point under the pelvis centre (same as `aim/geometry.py`).
- Domain gap: the difference between synthetic images and real images. A detector trained only on synthetic images often fails on real images.

## Download the samples

The samples are not in git: they are about 50 MB in 5,900 files. Only `out/contact_sheet.jpg` and the sequence videos (`out/sequence/*.mp4`) are in git.
To get all samples without Blender, run these commands from the repository root:

```
curl -L -o firescenes_v1.zip https://github.com/promaaa/vision-sobang/releases/download/firescenes-v1/firescenes_v1.zip
unzip -o firescenes_v1.zip -d sim/firescenes
```

## How to run

Run these commands from the repository root. Blender 5.2 and an NVIDIA GPU (Cycles OptiX) are necessary.

1. To make samples 0 to 199, run:

   ```
   blender -b --factory-startup -P sim/firescenes/firescenes.py -- samples 0 200
   ```

2. To make the 10 s walking sequence and its MP4 files, run:

   ```
   blender -b --factory-startup -P sim/firescenes/firescenes.py -- sequence
   ```

   When `out/sequence/` already has frames, this command does nothing. Delete `out/sequence/` first to make it again.

3. To make the contact sheet, run:

   ```
   blender -b --factory-startup -P sim/firescenes/firescenes.py -- sheet
   ```

4. To check the labels against `aim/geometry.py`, run:

   ```
   uv run python sim/firescenes/validate.py
   ```

Sample number i always gives the same scene, because i is the random seed.

## How to make more samples

1. To add samples 250 to 999, run:

   ```
   blender -b --factory-startup -P sim/firescenes/firescenes.py -- samples 250 750
   ```

2. When the run ends, run step 3 and step 4 of "How to run" again.

One sample took 10 to 13 s on the RTX 3090 while another job used the same GPU.
The renders use 16 samples per pixel for RGB, 8 for the thermal image and 4 for the low-resolution thermal render. The sequence uses 8 for RGB.
To run two batches at the same time, give them different number ranges.
If one sample fails, the batch continues and the log shows `SAMPLE FAILED <number>`.

## Output files

All files are in `out/`. Each sample has a six-digit number, for example `000042`.

| Path | Content |
|---|---|
| `rgb/<id>.jpg` | RGB image, 1280x720, 90 deg horizontal field of view (HFOV) |
| `thermal/<id>.png` | Thermal image, 16-bit, deci-kelvin, 1280x720, same camera as the RGB image |
| `thermal_256/<id>.png` | Thermal image, 16-bit, deci-kelvin, 256x192, 56 deg HFOV |
| `thermal_160/<id>.png` | Thermal image, 16-bit, deci-kelvin, 160x120, 56 deg HFOV |
| `preview/<modality>/<id>.png` | 8-bit colour pictures of the thermal images, fixed range 15 to 80 deg C |
| `labels/<id>.json` | Labels (see below) |
| `yolo/<modality>/images`, `yolo/<modality>/labels`, `yolo/<modality>/data.yaml` | YOLO folders for `rgb`, `thermal`, `thermal_256` and `thermal_160` |
| `contact_sheet.jpg` | Samples 0 to 19 and g00000 to g00003, RGB and thermal preview side by side |
| `sequence/` | The walking sequence: the same folders for 100 frames, plus `rgb.mp4`, `thermal.mp4`, `thermal_256.mp4`, `thermal_160.mp4` |

The YOLO image files are links to the RGB images and to the 8-bit thermal previews.
YOLO training tools need 8-bit images. The 16-bit files keep the real values.

To read a thermal PNG in Python, use for example `cv2.imread(path, cv2.IMREAD_UNCHANGED) / 10 - 273.15`. The result is in deg C.

## Samples with the gun in view

Samples `g00000` to `g00019` show the concept A gun. To make more of them, run for example:

```
blender -b --factory-startup -P sim/firescenes/firescenes.py -- gunsamples 20 30
```

- The scene contains the top module parts from `cad/parts/out/` and the stand-in gun of `cad/parts/render_module.py`.
- The gun is at its default tilt (6 deg down) and pan 0. These samples have no camera shake, so the gun stays where the CAD puts it.
- The USB camera's own mount is left out, because the camera point is inside it.
- The camera is 57 mm to the right of the barrel line and 25 mm below the barrel axis. It looks 16 deg further down than the barrel.
  So the barrel and its yellow shroud appear in the top-left corner of the image, not at the bottom.
- **Not verified:** The stand-in gun is the placeholder shape from `cad/concepts.py`, not a chosen gun. The real gun can look different.

## Labels

Each `labels/<id>.json` file has:

- `gun_in_view` (true for the g samples), `scene` (indoor or outdoor), `lighting`, `ambient_c` (room or air temperature) and `distractors` (the objects that look like fire or are warm).
- `robot_pose_world`: robot x, y (m) and heading (rad) in the scene. `robot_bob_m` is the vertical walking motion (sequence only).
- `camera`: pan and tilt (rad) as used by `aim/geometry.py`, and the camera pose in the robot frame (`R_robot_from_optical`, `t_robot`).
- `images`: for each image, the file, the size and the pinhole intrinsics (`fx`, `fy`, `cx`, `cy`).
- `fires`: for each fire:
  - `base_robot` and `centre_robot`: the 3D position of the fire base and fire centre in the robot frame (m).
  - `distance_m`: floor distance from the robot origin to the fire base. `camera_distance_m`: distance from the lens to the fire centre.
  - `width_m`, `height_m`, `temp_min_c`, `temp_max_c`, `smoke`.
  - `boxes`: the box in each image, or `null` when less than 4 pixels of the fire are visible.

The boxes come from the renderer. The thermal render marks each fire pixel with the fire number, so a box includes only the visible part of a fire.
A fire behind furniture has a smaller box or no box.

## What the scenes contain

Each sample makes new random choices:

- Scene: indoor room (65 %) or outdoor ground (35 %).
- Indoor room: 6 to 12 m by 5 to 9 m, 2.7 m walls, random floor and wall colours with a noise texture, 2 to 6 furniture boxes.
- Outdoor ground: grass, earth, asphalt or concrete colour.
- Lighting indoor: ceiling lamps, a window with sun, or dim. Lighting outdoor: sun, overcast or dusk.
- Fires: 1 to 3 fires. Each fire is 10 to 60 cm wide and 1.0 to 1.6 times as tall.
  A fire is a flame-shaped mesh with noise on its surface and a yellow-to-red glow, plus 1 or 2 smaller flames and an orange light.
- Smoke: 30 % of the fires have a grey smoke volume above them. The smoke is only in the RGB image.
- Distractors: a person (50 %), a floor lamp with a hot shade (50 %, indoor only), red or orange boxes, cylinders and cones, and bright sun spots on the floor (40 %).
- Robot: 0.8 to 6 m from fire 1, facing fire 1 within 29 deg. The other fires can be out of view.
- Camera shake: pan and tilt each change by a random value up to 1.5 deg.
- The furniture and distractors stay out of a 0.6 m strip between the robot and fire 1. So fire 1 is usually in view.

The sequence: the robot walks at 0.5 m/s straight toward a fire, from 6 m to 1 m, for 10 s at 10 frames per second.
The camera moves 1.5 cm up and down and 1.5 deg in tilt at 2 Hz, and 1 deg in pan at 1 Hz. The flames flicker.

## Thermal model

What the thermal image is:

- Each object has one set temperature. Each pixel shows the temperature of the surface that the camera sees.
- Flames: 600 to 900 deg C, hottest at the base. Person: 34 deg C. Lamp shade: 80 to 200 deg C.
- Room walls: the ambient temperature (20 to 30 deg C). The floor is 1 deg C colder. Furniture and red objects vary by up to 1 deg C.
- Sun spot: 8 to 20 deg C above ambient. Sunny outdoor ground: 5 to 15 deg C above ambient. Sky: 30 to 40 deg C below ambient.
- The 256x192 and 160x120 images average blocks of 5x5 and 8x8 pixels of a 1280x960 render. So a small fire fills part of a pixel and raises its value only partly.

What the thermal image is NOT:

- It is not a real sensor model.
- There is no sensor noise, no fixed-pattern noise and no NUC. NUC (non-uniformity correction) is the flat-field correction that real thermal cameras do from time to time.
- There is no optics blur, no lens distortion, no vignetting and no automatic gain.
- There is no emissivity and no reflection. A shiny floor does not reflect the fire.
- There is no heat spread: the floor around a fire stays at ambient temperature.
- Smoke is not in the thermal image.
- The averaging is done in kelvin, not in radiance. Real sensors add radiance, which weights hot parts more.

## Label check

`validate.py` reads every label file. It rebuilds the camera pose with `aim/geometry.py` and checks that it is the pose used by the renderer.
Then it projects each fire centre into each image and compares the point with the fire's box.
It also reads every 1280x720 thermal PNG. It checks that no pixel clips and that the hottest pixel in each fire box is a flame temperature.

Result for samples 0 to 249 and g00000 to g00019 (tested in simulation):

```
image        fires  inside box  mean error (px)  median (px)  max (px)  skipped: cut by image edge
rgb            339        98%              8.3          5.5      92.8     21
thermal        339        98%              8.3          5.5      92.8     21
thermal_256    237        98%              2.6          1.8      32.0     90
thermal_160    234        98%              1.7          1.1      19.9     93
thermal PNG: no clipped pixel; hottest pixel in the fire box is in the flame range for 99% of 357 fires
```

Result for the 100 sequence frames:

```
image        fires  inside box  mean error (px)  median (px)  max (px)  skipped: cut by image edge
rgb            100       100%              3.9          2.5      19.0     15
thermal        100       100%              3.9          2.5      19.0     15
thermal_256     99       100%              1.4          1.0       6.6      1
thermal_160     99       100%              0.9          0.7       4.3      1
thermal PNG: no clipped pixel; hottest pixel in the fire box is in the flame range for 100% of 115 fires
```

The script skips boxes that touch the image edge, because the edge cuts the fire and moves the box centre.

The fire centre is the middle of the set fire height. The box covers the visible flame, which has random noise and extra small flames.
So the box centre is not exactly at the projected point. Furniture that hides part of a fire also moves the box centre.

## Domain gap

These images are synthetic. A detector that works on them can still fail on a real robot.

- The flames are smooth glowing shapes. Real flames are partly transparent, change shape quickly and have sparks and soot.
- The rooms are simple boxes with plain colours. Real rooms have texture, clutter, glass and screens.
- The RGB images have no motion blur, no camera noise and no auto exposure. A real USB camera at a bright fire often saturates.
- The thermal images are ideal (see "Thermal model").
- Use these images to test the pipeline, the label format and the geometry. Do not use them alone to prove that the detector works.
- Before a detector is trusted, test it on real images of real fires, taken with the real cameras.
