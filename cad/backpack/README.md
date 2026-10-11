# Splash guard and concept B backpack

Status: **planned**. Nothing here is printed or built. The CAD exists. The checks below are **tested in simulation**: they run on the CAD geometry and the Berkeley Humanoid Lite (BHL) meshes.

This folder has printable, parametric CAD for two things:

1. A splash guard for the front of the torso. All concepts can use it.
2. The concept B backpack: two brackets, a plate, a tank cradle and a pump bracket.

**Not verified:** The tank and pump sizes come from shop pages and a brochure, not from parts in our hands. Measure the real bottle and pump before you print the cradle and the pump bracket.

**Not verified:** The wall check tests the wall parameters in `body.py`, not the meshes.

**Not done:** The leg check keeps both ankle joints at the standing angles. It does not sweep them.

**Assumed:** The leg check passes only with a software knee limit of 1.4 rad. Over the full URDF knee range, the foot and shank touch the backpack (0 mm).

## Terms

- **2020 extrusion:** an aluminium bar with a 20 × 20 mm cross-section and a slot on each face.
- **T-nut:** a nut that sits inside the slot of the extrusion. A drop-in T-nut goes into the slot from the front, so you do not take the frame apart.
- **Heat-set insert:** a brass sleeve with an inner thread. You press it into a printed hole with a hot soldering iron.
- **Countersunk screw:** a screw with a cone-shaped head. The head sits flush in a cone-shaped hole.
- **Drip lip:** a thin edge that sticks out and down. Water drips off its tip and does not run back under it.
- **STEP, STL:** STEP is the exact CAD file for other CAD programs. STL is a triangle mesh for the slicer.
- **Gyroid:** an infill pattern for 3D printing.
- **k-d tree:** a data structure that finds the nearest point in a large point set quickly.

## Files

| File | What it does |
|---|---|
| `measure.py` | Measures the front and rear faces of the torso mesh. |
| `body.py` | Builds all parts (build123d), exports STEP and STL, prints masses, runs the checks. Parameters are at the top. |
| `render.py` | Blender script. Puts the STLs on the robot and renders three images. |
| `out/` | One STEP and one STL per printed part. `ref_tank` and `ref_pump` are simple shapes of the bought parts, for the checks only. `assembly.json` gives the tank and pump positions to the render. `check_log.txt` is the output of the last `body.py` run. |
| `renders/` | `front.png` (front 3/4), `rear.png` (rear 3/4), `rear_detail.png` (close view of the backpack). Cycles OptiX, 96 samples, 1200 × 1500 px. The pump, bottle and hoses in the renders are simple shapes. |

All parts are drawn in the robot frame, in mm: x forward, y left, z up, feet on the floor. The STLs stack on the robot without any transform.

## Run

Run all commands from the repository root.

1. Install the CAD environment once:

```
uv sync --project cad
```

2. Fetch the Berkeley assets once:

```
scripts/fetch_bhl_assets.sh
```

3. Build the parts and run the checks. This takes about 3 minutes.

```
uv run --project cad python cad/backpack/body.py
```

4. Render the three images. This takes about 2 minutes on the RTX 3090.

```
blender -b --factory-startup -P cad/backpack/render.py -- cad/backpack/renders
```

5. To repeat the torso measurement, run:

```
uv run --project cad python cad/backpack/measure.py
```

`body.py` stops with an error when a part does not fit the bed. It also stops when a part is 10 mm or less from a leg, with the knee limited to 1.4 rad.

## Measured torso faces

**Method.** `measure.py` loads `meshes/base_visual.stl` and places it with the base visual origin of the full URDF (`berkeley_humanoid_lite.urdf`). It then shifts it down by 39 mm, like `cad/concepts.py`. It splits the mesh into connected parts and prints the bounding box of each part. A plane section at z = 700 mm through the front left post gives the slot profile. All values are in mm, robot frame.

**Profile.** The frame is 2020 aluminium extrusion (20 × 20 mm) with a 6 mm slot on each face.

| Value | mm |
|---|---|
| Slot opening | 6.2 |
| Wall thickness beside the slot opening | 1.5 |
| Cavity width behind the opening | 12.0 |
| Slot depth from the face to the core | 6.2 |
| Centre hole | about 5 |

**Front face (outer face at x = +70).**

| Part | Position |
|---|---|
| Two posts | y = ±65 (slot centre), z 571 to 771 |
| Top rail | z 771 to 791 (slot centre z = 781), y −125 to +125 |
| Bottom rail | z 551 to 571 (slot centre z = 561), y −75 to +75 |
| Shelf between the posts | x 34 to 70, y ±55, z 613 to 641. It is flush with the front face. |
| Pelvis and hip actuators | below z = 581, all at x ≤ 69.6 |

Free space: the front face is flat from z = 551 to 791 and from y = −75 to +75. Nothing sticks out past x = 70.

**Rear face (outer face at x = −70).**

| Part | Position |
|---|---|
| Two posts | y = ±65, z 571 to 771 |
| Top rail | z 771 to 791 (slot centre z = 781), y −125 to +125 |
| Bottom rail | z 551 to 571 (slot centre z = 561), y −75 to +75 |
| Shelf between the posts | x −70 to −34, y ±55, z 613 to 641, flush with the face |
| "Rear bump" (unknown part) | x −74 to −64, y −76 to +74, z 587 to 627. It sticks out 4 mm past the rear face. |
| Small part inside the left post | x −69 to −51, y 46 to 55, z 653 to 689 (inside the face) |

Free space: the rear posts are free from z = 628 to 771. The top rail is free on its full length. The backpack must stay behind x = −74 between z = 587 and 627.

## Design

### Splash guard (front)

- The guard has two flat panels, 2.5 mm thick and 156 mm wide. The lower panel covers z 551 to 675. The upper panel covers z 676 to 790.
- Each panel bolts flat to the front face with four M5 screws into drop-in T-nuts. Two screws go into the post slots. Two go into the top rail or the bottom rail.
- A drip lip runs along the bottom edge of each panel. It goes 45° down and forward. The lip of the upper panel hangs over the joint, so water does not run into the gap.
- A hood lip at z = 766 covers four vent slots (24 × 4 mm). The vents are under the hood, so a direct jet does not go in.
- A cable slot (40 × 12 mm) is in the lower panel at z 573 to 585, just above the bottom rail. A short hood lip covers it.
- The top edge is at z = 790, 1 mm under the concept A deck plate in `cad/parts/`.
- The guard does not cover the side faces of the torso.

### Backpack (rear, concept B)

- **Upper bracket:** a bar of 150 × 20 × 12 mm sits on the top rail. Two M5 screws in counterbores go into T-nuts. Two M4 heat-set inserts take the plate screws.
- **Lower bracket:** a bar of 170 × 44 × 12 mm sits on the two rear posts, at z 638 to 682. It is above the rear bump. Two M5 screws go into T-nuts. Four M4 inserts take the screws of the cradle and the pump bracket.
- **Plate:** the plate is 216 × 200 × 5 mm and sits at x −82 to −87. It is 8 mm behind the rear bump.
- **Tank cradle:** the cradle has a backing strip, a floor cup with a drain hole, and two saddles. Two hook-and-loop straps go through slots beside each saddle and through a channel behind the backing.
- **Pump bracket:** the bracket is a 5 mm plate with four bosses, 10 mm high. The pump feet bolt into M4 inserts in the bosses.
- The tank is on the left (y = +52 mm). The pump is on the right (y = −54 mm). The pump stands with its motor up and its head down.
- The cradle and the pump bracket each bolt with two screws through the plate into the lower bracket. Two more screws with nuts hold each of them to the plate.

### Bought parts that set the sizes

| Part | Dimensions used | Source |
|---|---|---|
| Tank: Nalgene 32 oz (946 mL) wide mouth bottle | diameter 89 mm (3.5 in), height 210 mm (8.25 in), cap 63.5 mm | well.ca listing, https://well.ca/products/nalgene-32-ounce-wide-mouth-water_85490.html (search result, read 2026-10-08) |
| Pump: Seaflo 21 series SFDP1-010-040-21, 12 V, 3.8 L/min | length 169, height 62, head width 73.5, ports 98 tip to tip, four foot holes Ø5 mm, 0.57 kg | Seaflo brochure, https://www.mygenerator.com.au/assets/images/resource/pdf/SEAFLO-21_SERIES_40psi_3.8LPM_12V_Water_Pump_Product_Brochure.pdf (read 2026-10-08). This is the pump in `docs/hardware/bom_B.csv`. |
| Foot hole pattern of the pump | 79 × 55 mm | Read from the brochure drawing. **Guess:** I read 55 mm as the spacing along the motor and 79 mm as the spacing across. Check on the real pump. |

**Assumed:** The bottle is 1 L, not 1.4 L. The hardware README lists a Daiso 2 L bottle. That bottle has no published size, and 2 L of water is heavy behind the torso. Change `TANK_D`, `TANK_H` and the saddle positions in `body.py` for another bottle.

**Guess:** The pump body is a box of 169 × 73.5 × 62 mm, centred on the foot holes. The real feet are probably not at the centre of the length.

## Part list and mass

I use PLA at 1.24 g/cm³. The print settings are 4 perimeters, 5 top and 5 bottom layers and 30 % gyroid infill. **Guess:** with these settings, the parts are about 70 % of solid mass, because the walls are only 2.5 to 12 mm thick.

| Part | Volume (cm³) | Solid mass (g) | Estimated print mass (g) | Size (mm) |
|---|---|---|---|---|
| guard_upper | 51.5 | 64 | 45 | 156 × 121 × 11 |
| guard_lower | 52.5 | 65 | 46 | 156 × 131 × 11 |
| bracket_upper | 34.2 | 42 | 30 | 150 × 20 × 12 |
| bracket_lower | 87.6 | 109 | 76 | 170 × 44 × 12 |
| plate | 215.2 | 267 | 187 | 216 × 200 × 5 |
| cradle | 202.1 | 251 | 175 | 113 × 150 × 72 |
| pump_bracket | 39.7 | 49 | 34 | 96 × 76 × 15 |

- The splash guard is about 91 g.
- The printed backpack parts are about 502 g.
- The empty backpack is about 1.37 kg: 502 g printed + 570 g pump + 180 g bottle (guess) + 120 g screws, straps and hose (guess).
- With 946 g of water, the backpack is about 2.32 kg.

## Checks (tested in simulation)

| Check | Result |
|---|---|
| Bed fit, 220 × 220 × 250 mm | All 7 parts fit. The largest is the plate, 216 × 200 × 5 mm. |
| STL meshes | Each printed part is one closed (watertight) body. A slicer can use it directly. |
| Wall thickness | All wall parameters are 2.0 mm or more (panel 2.5, lip 2.5, cradle wall 3.0, strap channel wall 3.0, plate 5.0, insert boss wall 3.2). This is a check of the parameters, not of the meshes. |
| Leg clearance, full URDF range | **0 mm. This range fails the 10 mm limit.** The shank and foot touch the cradle, the bottle, the pump and the plate. Worst pose: left leg, hip roll 0.12, hip yaw 0.07, hip pitch +0.98, knee 2.04 rad. |
| Leg clearance, knee ≤ 1.4 rad | Minimum 23 mm (bottle). Worst pose: right leg, hip roll −0.26, hip yaw +0.98, hip pitch +0.98, knee 1.40 rad. |
| Splash guard clearance | Minimum 34 mm over the full URDF range (lower panel). The guard passes without a knee limit. |
| Knee limit and clearance | Knee ≤ 1.30 rad: 43 mm. Knee ≤ 1.40 rad: 23 mm. Knee ≤ 1.45 rad: 11.5 mm. Knee ≤ 1.6 rad: 0.2 mm. |

**How I checked the clearance.** `body.py` sweeps hip roll, hip yaw, hip pitch and knee for each leg. Each joint takes 7 values between its URDF limits, so each leg has 2401 poses. Then a finer grid (5 values per joint) refines the worst pose of each part. The ankle pitch stays at −0.3 rad and the ankle roll at 0. The script samples about 6000 points on each leg link and 30 000 points on each part. A k-d tree then finds the nearest points. The point spacing gives an error of about 2 mm. Distances above 60 mm are reported only as "more than 60 mm". The run takes about 2 minutes.

**Where the contact happens.** The contact needs hip pitch near its rear limit (+0.98 rad) and the knee bent more than about 1.5 rad. The foot then folds up behind the hips into the backpack. Walking does not use this pose, but a fall or a crouch can.

**Proposed fix.** No single CAD parameter fixes this, because the foot reaches the full height of the backpack. I propose a software knee limit of 1.4 rad in the walking policy and the joint controller. This is `KNEE_MAX` in `body.py`, and the check asserts with it. A softer rule is also possible: limit the knee only when hip pitch is above 0.3 rad. With hip pitch ≤ 0.3 rad and the full knee range, the clearance is 21 mm.

## Hardware list

| Item | Qty | Where |
|---|---|---|
| M5 drop-in T-nut for 2020, 6 mm slot | 12 | 8 for the guard, 4 for the brackets |
| M5 × 8 button head screw (ISO 7380) + M5 washer | 8 | guard panels |
| M5 × 10 button head screw | 4 | brackets (head in a 7 mm counterbore) |
| M4 heat-set insert, M4 × 8.1, hole 5.6 mm | 10 | 2 upper bracket, 4 lower bracket, 4 pump bosses |
| M4 × 12 button head screw | 2 | plate to upper bracket |
| M4 × 18 countersunk screw (DIN 7991) | 2 | cradle through plate into the lower bracket |
| M4 × 16 countersunk screw | 6 | 2 pump bracket into the lower bracket, 4 with nuts (cradle and pump bracket to the plate) |
| M4 nut + M4 washer | 4 | robot side of the plate |
| M4 × 20 pan head screw + M4 washer | 4 | pump feet into the bosses. **Guess:** check the foot thickness. |
| Hook-and-loop strap, 25 mm wide, about 400 mm long | 2 | tank |

## Print settings

- PLA, 0.4 mm nozzle, 0.2 mm layers, 4 perimeters, 5 top and 5 bottom layers, 30 % gyroid infill.
- PETG resists heat and sun better than PLA. Use PETG when the robot works near a fire or outside.
- No part needs supports when you use these orientations:
  - Guard panels: the flat back (robot side) on the bed. The lips point up at 45°.
  - Brackets: the robot side on the bed. The holes are vertical.
  - Plate: flat.
  - Cradle: the plate side on the bed. The strap channels are short bridges (27 mm).
  - Pump bracket: the plate side on the bed. The bosses point up.

## Assembly

1. Press the M4 heat-set inserts into the brackets and the pump bosses with a soldering iron.
2. Drop two M5 T-nuts into each slot that you use. Turn each T-nut so that it locks in the slot.
3. Bolt the lower guard panel, then the upper guard panel, to the front face.
4. Bolt the upper bracket to the rear face of the top rail.
5. Bolt the lower bracket to the rear faces of the two rear posts, at z 638 to 682.
6. Bolt the cradle and the pump bracket to the plate with the four screws and nuts at z = 700.
7. Hold the plate against the two brackets. Put the four countersunk screws at z = 670 through the cradle, the pump bracket and the plate into the lower bracket.
8. Put the two M4 × 12 screws through the plate into the upper bracket.
9. Bolt the pump to the bosses.
10. Put the bottle in the cradle. Pass each strap through the channel behind the cradle and around the bottle.

## Open questions

- The knee limit of 1.4 rad must go into the walking policy and the controller. Check that the policy does not need a larger knee angle.
- The backpack is about 2.3 kg at about 130 mm behind the torso centre. The payload simulation (`sim/payload/`, round 3, model B_real) used `out/assembly.json`. Its status is tested in simulation.
  - B_real moves the centre of mass back by 15 mm when the tank is full.
  - The worst single-leg pitch torque is 3.9 Nm when full and 4.4 Nm when empty.
  - The worst hip roll torque is 9.6 Nm.
  - Nobody has tested the balance on the real robot.
- Seaflo may allow only some pump orientations. Check the manual before you mount the pump with its head down.
- A leak from the pump or the tank drips onto the hip actuators below. A drip tray under the pump is a possible addition.
- I do not know what the rear bump is (z 587 to 627, it sticks out 4 mm). It is maybe a battery holder or a switch plate. Check it on the real robot.
- The tank cap is at z ≈ 805, 14 mm above the torso top. A head or deck on the torso top can make refilling difficult.
- The vent slots and the cable slot are small. Change `VENT` and `CABLE` when the real cables are known.
- The splash guard does not seal. It stops water from the front and from above. It does not make the torso waterproof.

## Licence

Renders show the Berkeley Humanoid Lite meshes (CC BY-SA 4.0). Credit the Berkeley Humanoid Lite team and use the same licence when you share them.
