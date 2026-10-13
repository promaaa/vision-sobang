# Water tanks for a pump inside the torso (R1 and R2)

Status: **planned**. Nothing here is printed or built. The CAD exists. The checks below are **tested in simulation**: they run on the CAD geometry and the Berkeley Humanoid Lite (BHL) meshes.

The team wants the pump inside the torso, for a lower centre of mass (CoM) and better balance.
This folder has printable, parametric CAD for two tank options. The simulation results are in `sim/payload/README.md`, round 5.

- **R1, tank inside the torso.** One tank fills the free space above the mini PC and under the pan-tilt deck. The pump hangs under the tank floor, inside the torso. 0.63 L.
- **R2, side tanks.** Two tanks bolt to the side faces of the torso posts, above the hip actuators. 0.73 L. The pump cannot go inside the torso with R2 (see "Pump").

**Assumed:** The pump is the TCS Micropumps M400K-V. The request named "Centrifugal Brushless Motor Micropumps for Liquids – for 3.2mm ID tubing". I did not find that shop page. The TCS M400K is a brushless centrifugal micropump for 3.2 mm bore tubing. Check the part number before you print.

**Not verified:** The free space comes from the BHL CAD mesh (`base_visual.stl`). The course robot can have other parts inside the torso. The course page lists "Robot XML (v1)" as coming soon. When it is out, check the space again.

**Not verified:** Nobody has printed a tank. Printed tanks often leak. Test each tank with water before you put it in the robot.

## Terms

- **Centrifugal pump:** a pump with a spinning impeller. It cannot pull water up into an empty pump. It needs water at its inlet before it starts. This is "not self-priming".
- **Flooded inlet:** the pump sits lower than the water, so water flows into it by gravity.
- **Baffle:** a wall inside a tank with holes in it. It stops the water from moving from one end to the other in one block (sloshing).
- **Heat-set insert:** a brass sleeve with an inner thread. You press it into a printed hole with a hot soldering iron.
- **Drop-in T-nut:** a nut that goes into the slot of the 2020 aluminium extrusion from the front.
- **STEP, STL:** STEP is the exact CAD file for other CAD programs. STL is a triangle mesh for the slicer.

## Files

| File | What it does |
|---|---|
| `body.py` | Builds all parts (build123d), exports STEP and STL, prints volumes and masses, runs the checks, writes `out/assembly.json`. Parameters are at the top. |
| `render.py` | Blender script. Renders R1 and R2 on the robot with the ST3215 pan-tilt and a nozzle, and two turntable videos. |
| `out/` | STEP and STL per part. `r1_half_*`, `r2_tub` and `r2_inner_plate` are the print pieces. `ref_pump_*` and `water_*` are for the checks and renders only. `assembly.json` has the masses, centres and inner sizes for `sim/payload/`. `check_log.txt` is the output of the last `body.py` run. |
| `renders/` | `r1_cutaway.jpg`, `r1_exploded.jpg`, `r2_front.jpg`, `r2_rear.jpg`, `r2_detail.jpg`, `turntable_r1.mp4`, `turntable_r2.mp4`. |

All parts are drawn in the robot frame, in mm: x forward, y left, z up, feet on the floor, torso frame top at z = 791. The STLs stack on the robot without any transform.

## Run

Run all commands from the repository root.

1. Install the CAD environment once:

```
uv sync --project cad
```

2. Build the parts and run the checks. This takes about 3 minutes.

```
uv run --project cad python cad/torso_tank/body.py
```

3. Rebuild the simulation models, because they read `out/assembly.json`:

```
cd sim/payload && uv run python models.py
```

4. Render the stills. This takes about 2 minutes on the RTX 3090.

```
blender -b --factory-startup -P cad/torso_tank/render.py -- third_party/berkeley-humanoid-lite-assets/data/robots/berkeley_humanoid/berkeley_humanoid_lite cad/torso_tank/renders
```

5. To render the turntable videos, add `turntable_r1 turntable_r2` at the end of the command in step 4. Each takes about 4 minutes.

`body.py` stops with an error when a part does not fit the bed, when an STL is not closed, when a part is less than 1.5 mm from the torso mesh, or when an R2 part is 10 mm or less from a leg with the knee limited to 1.4 rad.

## Free space in the torso (measured on the BHL mesh)

| Region | Position (mm, robot frame) | What is there |
|---|---|---|
| Battery (6S LiPo) | x −30 to 33, y −66 to 89, z 583 to 633 | Low in the torso. Its end sticks out of the left side to y = 89. |
| Mini PC | x −52 to 51, y ±58, z 639 to 679 | On the front and rear shelves. |
| USB board | x 14 to 40, y ±67, z 685 to 711 | Front, above the PC. |
| Shoulder brackets | \|y\| ≥ 66.7, z 681 to 791 | Both sides of the upper torso. |
| Pan base of the ST3215 pan-tilt | x −78 to 2, y ±40, z 762 to 791 | Hangs 29 mm under the deck. |
| **Free: upper torso** | x ±48 (±62 between the posts), y ±63, z 712 to 786 | **R1 goes here.** |
| **Free: torso sides** | \|y\| 77 to 124, x ±66, z 590 to 678 | **R2 goes here.** Above the hip actuators (top at z 581), under the shoulder brackets. |

The lower torso has no free space for a tank or for the pump: the battery and the PC fill it. The gaps beside the battery are 17 mm wide. The pump is 25 mm.

## Pump

| Item | Value | Source |
|---|---|---|
| Model | TCS Micropumps M400K-V, brushless centrifugal, "parallel connectors for 3.2mm bore tubing" | TCS M400 range page, http://www.miniaturepumps.co.uk/TCSM400range.htm (read 2026-10-13) |
| Size, mass | 40 × 26 × 25 mm, 32 to 34 g | same page |
| At 12 V | 5.8 W, 380 mbar maximum pressure, 1150 mL/min free flow | same page |
| At 6 V | 1.2 W, 86 mbar, 500 mL/min | same page |
| Protection | IP45 standard, IP67 "waterproof" version | same page |
| Priming | The "-SUB" version is the "self priming variant". So the standard M400K-V is **not** self-priming. | same page |

- The pump weighs 33 g. The Seaflo pump of the backpack weighs 570 g. Where the pump sits does not change the balance much. The water does.
- The pump must sit below the water (flooded inlet).
  - In **R1**, the pump hangs under the tank floor. The tank feeds it by gravity. All the water is usable.
  - In **R2**, the water is lower than any free space inside the torso. So the pump sits in a holder in front of the right hip, below the tank floors. A pump inside the torso would sit above the water, and a centrifugal pump does not lift water into itself. The alternative is the M400K-SUB in a tank.
- The pump draws about 0.5 A from the 12 V rail (5.8 W). The Seaflo drew 4 A.

## Design

### R1: tank inside the torso

- The tank fills the free upper torso: x ±48 mm and y ±63 mm, plus bays to x ±62 between the posts. Floor at z = 714, top at z = 786.
- Notches leave room for the pan base (x −90 to 4, y ±42, above z = 759) and for the cable and hose channel under the deck slot (x −8 to 40, y −70 to −42).
- 3 baffles across x and 2 across y, 2 mm thick, with a window in the middle and drain slots at the floor.
- The tank hangs from the pan-tilt deck. `r1_deck` is the deck of `cad/parts/` with four more M4 holes. Four M4 screws go through the deck into heat-set inserts in closed pillars on the tank top.
- The pump hangs under the tank floor in a drip tray that is part of the tank print. The pump bottom is 7 mm and the tray floor 2 mm above the mini PC. A 6 mm drain hole in the tray takes a tube out of the torso.
- The outlet is an M5 thread in the tank floor, for a brass M5 hose barb (3.2 mm tubing). A short tube loop goes to the pump inlet.
- The fill neck points backward through the rear face, between the rear posts (bore 19 mm). Close it with a silicone stopper with a small vent hole.
- The jet hose goes from the pump up through the channel and the deck slot to the nozzle.

### R2: side tanks

- Each tank is x ±66, y 78 to 124 (left; the right one is the mirror), z 592 to 678.
- A pocket in the inner face clears the end of the battery (x −33 to 36, z 596 to 621). Both tanks have it, so they are mirror images.
- 3 baffles across x.
- Four M5 × 55 screws per tank go through closed tubes in the tank into drop-in T-nuts in the side slot of the posts (x = ±60, z = 603 and 667). Pads on the inner face touch the posts.
- The outlet is an M5 thread on the front face near the floor. The left tank feeds a tube that crosses in front of the torso to the pump. **Not verified:** the tube path across the front is not checked against the legs.
- The pump sits in `r2_pump_holder` in front of the right hip actuator, below both tank floors. Its top plate is glued under the right tank.
- Each fill neck is on the tank top at the front (bore 16 mm, silicone stopper).

## Part list and mass

PETG at 1.27 g/cm³, printed solid (100 % infill or 6 perimeters), so that the walls hold water.

| Part | Volume (cm³) | Mass (g) | Size (mm) |
|---|---|---|---|
| R1 tank (two halves 139 g + 132 g) | 213.7 | 271 | 140 × 126 × 110 |
| R1 deck (replaces the deck of `cad/parts/`) | 110.4 | 140 at 100 %, about 91 at the deck print settings | 158 × 130 × 6 |
| R2 tank, each (tub 133 g + inner plate 33 g) | 131.1 | 167 | 141 × 49 × 100 |
| R2 pump holder | 15.7 | 20 | 28 × 45 × 32 |

| Option | Water | Empty system | Full system | Hardware and tubing (guess) |
|---|---|---|---|---|
| R1 | 0.632 L | 0.349 kg | 0.981 kg | 45 g |
| R2 | 0.725 L | 0.526 kg | 1.251 kg | 140 g (8 long M5 screws, T-nuts, more tubing) |

The empty system is the printed tank, the pump and the hardware. It does not include the pan-tilt, the nozzle or the splash guard.

## Checks (tested in simulation)

| Check | Result |
|---|---|
| Bed fit, 220 × 220 × 250 mm | All print pieces fit. The largest is an R1 half, 140 × 63 × 110 mm. |
| STL meshes | Each print piece is one closed body. |
| Wall parameters | 2.0 mm or more (tank wall 2.5, baffle 2.0, holder 2.5, boss walls 2.9 and 2.7). |
| Torso clearance (mesh) | R1 tank 2.0 mm, R2 tanks 2.5 mm (pads touch the posts on purpose), pump holder 2.5 mm, pumps 5.0 and 7.0 mm. |
| Leg clearance R2, full URDF range | **0.1 mm. This fails the 10 mm limit.** With the knee near 2.3 rad and the hip pitch near +0.98 rad, the foot folds up behind the hip and touches the rear end of a tank. |
| Leg clearance R2, knee ≤ 1.4 rad | 46.9 mm (tanks), 50.7 mm (pump holder). |
| Leg clearance R1 | Not needed: R1 sits inside the frame. |

R2 needs the same software knee limit of 1.4 rad as the backpack of concept B (`cad/backpack/README.md`). R1 does not.

## Print and assembly

1. Print the R1 halves on their cut face (y = 0). The notch for the pan base is a 27 mm bridge in this orientation. Use supports there if your printer sags.
2. Glue the R1 halves with a two-part epoxy along the cut face. The baffles are cut in half too, so they glue at the same time.
3. Print the R2 tubs on their outer face. Print the inner plates flat. Glue each plate on its tub with epoxy.
4. Fill each tank with water and let it stand for one hour on paper. If it leaks, coat the inside with a thin epoxy and test again.
5. R1: press the four M4 inserts into the pillars. Tap the outlet M5 and screw in the barb with thread sealant.
6. R1: put the pump in the tray. Connect the outlet barb to the pump inlet with a short tube. Lower the tank into the torso from the top. Bolt the deck to the rails and the tank under the deck.
7. R2: drop eight M5 T-nuts into the side slots of the posts. Bolt each tank with four M5 × 55 screws.

## Open questions

- Which pump did the team order? If it is not the M400K-V, change the pump block in `body.py`.
- R1 puts water above the mini PC. The drip tray catches pump drips only. A leak from the tank floor drips onto the PC. Add a splash cover on the PC, or choose R2.
- The jet of this pump is short. See `sim/payload/README.md`, round 5: a 1.0 to 1.5 mm nozzle gives 5.0 to 6.6 m/s at 0.3 to 0.5 L/min.
- Without the shoulder brackets of the full BHL, the upper torso has more room, and R1 could be wider. I did not compute that volume.

## Licence

Renders show the Berkeley Humanoid Lite meshes (CC BY-SA 4.0). Credit the Berkeley Humanoid Lite team and use the same licence when you share them.
