# Actuators: from aim commands to servos, water relay and walking

This folder connects `aim/run.py` to the hardware of concept A.
The servos are two Waveshare ST3215 (Feetech STS3215, 12 V) on a Waveshare Bus Servo Adapter (A).
A Raspberry Pi Pico 2 switches a 2-channel 5 V relay module. An e-stop cuts the water.
The parts list is in `docs/hardware/bom_extinction.csv` and `docs/hardware/README.md`.

**Not done:** Nothing here has run on real hardware. The team has not received the parts.
**Not verified:** The driver assumes that the servo adapter does not echo the sent bytes.
**Not verified:** The Pico 2 drives the 5 V relay module with 3.3 V signals. `docs/hardware/README.md` also lists this as unverified.
**Not verified:** The walking bridge has not run inside the Berkeley Humanoid Lite (BHL) runtime. Its test uses a stand-in for the BHL class.

## Status

| Part | Status |
|---|---|
| `st3215.py`: servo protocol (ping, read, write, sync write, state, torque, set id) | built, tested in simulation with a fake serial port |
| `pico_fw/main.py`: relay firmware with timeout and e-stop input | built, logic tested on the laptop (not on a Pico) |
| `actuator_node.py --mock`: full pipe without hardware | built, tested in simulation |
| `actuator_node.py` with servos and Pico | built, not run |
| `walk_bridge.py`: walk commands into the BHL runtime | built, tested in simulation with a stand-in class |
| `selftest.py`: first-day check of all parts | built, tested in simulation with `--mock` |
| Calibration | planned |

"Tested in simulation" here means: with fake ports or mock hardware on the laptop.

## Files

- `st3215.py`: the Feetech STS protocol over pyserial. It also has a small command-line tool to list servos, change an id and read positions.
- `pico_fw/main.py`: MicroPython firmware for the Pico 2. It switches the two relays.
- `actuator_node.py`: reads the aim commands, drives the servos and the relays, and sends the measured angles back.
- `walk_bridge.py`: replaces the BHL gamepad class, so the walking policy gets `vx` and `yaw_rate` from `aim/run.py`.
- `selftest.py`: step-by-step check of the parts on the first day.
- `test_actuators.py`: tests.

## Network ports

All ports are UDP on `127.0.0.1`. Each message is one JSON line.

| Port | From | To | Content |
|---|---|---|---|
| 5600 | fire detector | `aim/run.py` | `FireDetection` (see `aim/README.md`) |
| 5601 | `aim/run.py` | `actuator_node.py` | command: `pan`, `tilt` (rad), `pump_on` |
| 5602 | `aim/run.py` | `walk_bridge.py` | command: `vx` (m/s), `yaw_rate` (rad/s) |
| 5603 | `actuator_node.py` | `aim/run.py --feedback` | measured angles: `{"t", "pan", "tilt", "water", "estop"}` |
| 5604 | `actuator_node.py` | `aim/send_test_detections.py --feedback` | the same measured angles |
| 5605 | robot pose source (planned), or `aim/send_test_detections.py` | `aim/run.py` | pose `{"timestamp", "x", "y", "yaw"}` in the odometry frame, optional `"roll"`, `"pitch"` (IMU) |

`t` is `time.monotonic()` when the node read the angles. `aim/run.py --feedback` uses `t` for its delay compensation.

## Wiring

| From | To | Note |
|---|---|---|
| Robot computer USB (powered hub) | Bus Servo Adapter (A) USB | The adapter USB chip is a CH343P [W3]. |
| 12 V converter output | Bus Servo Adapter (A) DC jack (5.5 x 2.1 mm) | Input 9 to 12.6 V. It must match the servo voltage [W2]. |
| Adapter jumper cap | position **B** | B = USB control. A = UART control [W2]. |
| Adapter servo connector | pan servo, then tilt servo (daisy chain) | Pan = id 1, tilt = id 2. |
| Robot computer USB (powered hub) | Pico 2 USB | Power and the serial link. |
| Pico pin 40 (VBUS, 5 V) | relay module VCC | 5 V for the relay coils. |
| Pico pin 38 (GND) | relay module GND | |
| Pico pin 19 (GP14) | relay module IN1 | Channel 1: water-gun trigger. |
| Pico pin 20 (GP15) | relay module IN2 | Channel 2: 12 V pump. |
| Pico pin 21 (GP16) | one NC contact of the e-stop, then Pico pin 23 (GND) | Pressed or broken wire = input high = stop. |
| Relay 1 COM and NO | across the trigger switch of the water gun | The gun keeps its own battery. |
| Relay 2 COM and NO | in the +12 V wire of the pump | Put the SB560 diode across the pump, cathode to +12 V. |
| E-stop other NC contact | coil circuit of the power relay | As planned in `docs/hardware/README.md`. |

The firmware assumes an active-low relay module: IN low = relay on.
For "off", the firmware sets the pin to input (high impedance), so no current flows in the opto-coupler.
If your module is active-high, set `ACTIVE_LOW = False` in `pico_fw/main.py`.

## Install

1. Install the environment once, from the repository root (see the root README):

```sh
uv sync
```

2. Run the tests:

```sh
uv run pytest actuators
```

Result on 2026-10-10: 10 tests pass.

3. Copy `pico_fw/main.py` to the Pico as `main.py`, for example with Thonny or `mpremote cp pico_fw/main.py :main.py`.

The firmware starts the Pico hardware watchdog (2 s). If you stop the program, the Pico restarts after 2 s. This is normal.

Use the `/dev/serial/by-id/...` names for the two USB devices. Both can appear as `/dev/ttyACM*`, in any order.

## First day with the parts

`selftest.py` checks the parts one step at a time. It asks before each step that moves the gun or switches a relay.
Each step prints PASS, FAIL or SKIP. A FAIL line also prints a hint.

1. Set the servo ids first (next section). The self-test needs id 1 (pan) and id 2 (tilt).
2. Copy `pico_fw/main.py` to the Pico.
3. Plug the adapter and the Pico into the robot computer, and switch on the 12 V supply.
4. Run the self-test:

```sh
uv run python actuators/selftest.py
```

| Step | What it checks | It stops the test when |
|---|---|---|
| 1 | Finds the two serial ports and says which is the servo adapter and which is the Pico | a device is missing |
| 2 | Pings servo ids 1 and 2, reads their voltage and temperature | a servo is missing, or the voltage is outside 9 to 12.6 V |
| 3 | Moves pan and tilt by +10 and -10 degrees at 20 degrees/s, and reads the position error (limit 2 degrees) | |
| 4 | Switches relay 1 and relay 2 on for 0.2 s each. You confirm the clicks | |
| 5 | Switches both relays on, stops sending lines, and checks that the Pico switches both off | |
| 6 | You press the e-stop: the input must read open, and the Pico must refuse `P1`. Then you release it | |
| 7 | Sends one UDP message to itself on each port 5600 to 5605 | |

- When step 1 or 2 fails, the self-test skips steps 3 to 6. Step 7 still runs.
- Step 1 uses the USB vendor id and then a probe. The Pico has the Raspberry Pi id 2e8a. The adapter has the WCH id 1a86 (CH343P chip).
- To give the ports by hand, add `--servo-port <device>` and `--pico-port <device>`.
- Without hardware, add `--mock --yes`. The mock runs the Pico firmware logic on the laptop. Result on 2026-10-10: 7 PASS.

**CAUTION:** Steps 4 and 5 switch the gun trigger and the pump. Remove the water or point the gun at a safe place first.

## Set the servo ids

New servos have id 1 [W1]. Two servos with the same id on one bus do not work.

1. Connect only the tilt servo to the adapter.
2. List the servos on the bus:

```sh
uv run python actuators/st3215.py /dev/serial/by-id/<adapter>
```

3. **CAUTION:** Change the id from 1 to 2. This writes the servo EPROM. You can change it back the same way.

```sh
uv run python actuators/st3215.py /dev/serial/by-id/<adapter> --set-id 1 2
```

4. Connect the pan servo too, and list the servos again. You must see id 1 and id 2.

## Calibration

The calibration is a JSON file with the same keys as `DEFAULT_CALIB` in `actuator_node.py`:

```json
{"pan": {"id": 1, "zero": 2048, "direction": 1, "min_deg": -90, "max_deg": 90, "max_speed_dps": 180},
 "tilt": {"id": 2, "zero": 2048, "direction": 1, "min_deg": -90, "max_deg": 90, "max_speed_dps": 180}}
```

`zero` is the servo position (in steps, 4096 for one turn) when the angle is 0.
`direction` is 1 or -1. Positive pan turns left, seen from above. Positive tilt lifts the muzzle.

1. **CAUTION:** Switch the servo torque off and print the positions. The gun can fall forward, so hold it.

```sh
uv run python actuators/st3215.py /dev/serial/by-id/<adapter> --torque-off
```

2. Turn the gun by hand until it points straight forward. Write the id 1 position as the pan `zero`.
3. Put a spirit level on the barrel. Tilt the gun until the barrel is level. Write the id 2 position as the tilt `zero`.
4. Stop the tool with Ctrl-C and save the file, for example `actuators/calib.json`.
5. Start the node with the file, without water:

```sh
uv run python actuators/actuator_node.py --calib actuators/calib.json --servo-port /dev/serial/by-id/<adapter> --pico-port /dev/serial/by-id/<pico>
```

6. In a second terminal, send pan = 0.2 rad for 3 s:

```sh
python3 -c "import json,socket,time; s=socket.socket(2,2); [(s.sendto(json.dumps(dict(pan=0.2,tilt=0.0,pump_on=False)).encode(),('127.0.0.1',5601)),time.sleep(0.1)) for _ in range(30)]"
```

7. When the gun turns right instead of left, set the pan `direction` to -1 and restart the node.
8. Do steps 6 and 7 again for the tilt, with `tilt=0.2`. The muzzle must go up.
9. Set `min_deg` and `max_deg` so that the gun cannot hit the robot or the cables.

The node limits the goal speed to `max_speed_dps`. It also sends this speed to the servo.
After this, do the nozzle and camera calibration of `aim/README.md`.

## Run the full pipe without hardware

1. In a first terminal, start the actuator node with mock servos and a mock relay:

```sh
uv run python actuators/actuator_node.py --mock
```

2. In a second terminal, start the aim runtime with measured angles:

```sh
cd aim && uv run python run.py A --feedback
```

3. In a third terminal, start the fake detector. With `--feedback`, it reads the camera angles from the node:

```sh
cd aim && uv run python send_test_detections.py A --feedback
```

Result on 2026-10-10: `run.py` went SEARCH, APPROACH, AIM, SPRAY, CHECK, SEARCH (20 s, no other fire) and DONE.
The node reported water on for 3.5 s. The fake detector also walks a simulated robot and sends its pose on UDP 5605.
Add `--v2` to the fake detector to test the frame messages of interface v2.
At the start, `run.py` can print "no fresh feedback" once, before the first feedback arrives.

4. Optional: in a fourth terminal, start the walking bridge alone. It prints the command that the policy would get:

```sh
uv run python actuators/walk_bridge.py
```

## Actuator node

- It runs at 50 Hz. It uses the newest command that arrived.
- It holds the servos and switches the water off when no command arrives for 0.5 s.
- It moves the goal angles at `max_speed_dps` at most. It clips them to `min_deg` and `max_deg`.
- It switches the water only when the command is fresh, the servo replies are good and the e-stop is not pressed.
- `--water trigger` (default, concept A) uses relay 1. `--water pump` (concepts B and E) uses relay 2.
- It sends one line to the Pico at each tick. So the Pico timeout (0.5 s) switches the water off when the node stops.

## Pico firmware

The Pico reads lines on its USB serial port. Each line gets one reply line, for example `OK P0 T1 E0`.

| Line | Action |
|---|---|
| `P1` / `P0` | pump relay on / off (channel 2) |
| `T1` / `T0` | gun trigger relay on / off (channel 1) |
| `H` | heartbeat, no change |
| `S` | status |

- Both relays switch off when no line arrives for 0.5 s. When a relay was on, the Pico sends `OFF TIMEOUT`.
- Both relays switch off while the e-stop input is high. When a relay was on, the Pico sends `OFF ESTOP`.
- During the e-stop, the Pico refuses `P1` and `T1` with `ERR ESTOP`.
- `E1` in the reply means that the e-stop is pressed.

## Walking bridge into the BHL runtime

`walk_bridge.py` has the class `AimGamepad`. It replaces `Se2Gamepad` of the BHL low-level code (`policy/gamepad.py`), as `docs/locomotion/README.md` part C describes.

- The gamepad still gives the mode buttons: A + right bumper for the RL mode, A + left bumper for init, X for idle.
- The velocity comes from UDP port 5602: `velocity_x = clip(vx, -0.5, 0.5)`, `velocity_y = 0`, `velocity_yaw = clip(yaw_rate, -1, 1)`.
- When no message arrives for 0.5 s, the velocity is zero, so the robot stands still.
- The BHL gamepad thread needs a connected gamepad, as before.

Steps (planned, not tested):

1. Install the BHL low-level code on the robot computer, as in its README.
2. Copy `walk_bridge.py` to the robot computer.
3. Make a start script next to it with these lines, then the loop of the BHL `scripts/run_locomotion.py`:

```python
import berkeley_humanoid_lite_lowlevel.robot.humanoid as bhl_humanoid
from walk_bridge import AimGamepad
bhl_humanoid.Se2Gamepad = AimGamepad  # Humanoid() now creates AimGamepad
```

4. Start `aim/run.py` on the same computer.
5. Put the robot in the RL mode with the gamepad. The robot then follows `vx` and `yaw_rate` from `aim/run.py`.

## Servo facts and sources

A subagent read these sources on 2026-10-10. The tests check the packet examples of the manual (U2).

| Fact | Value | Source |
|---|---|---|
| Default baud rate, default id | 1 000 000 baud (register value 0), id 1 | W1, U1 |
| Packet | `FF FF ID LEN INSTR PARAMS CHECKSUM`, LEN = number of params + 2 | U2 |
| Checksum | `~(ID + LEN + INSTR + params) & 0xFF`. The status packet has ERROR in place of INSTR | U2, U4 |
| Instructions | PING 0x01, READ 0x02, WRITE 0x03, SYNC_WRITE 0x83. Broadcast id 0xFE | U5, U7, U2 |
| Byte order | little endian (low byte first) | U1, U4 |
| Sign | sign bit plus magnitude: bit 15 for position and speed, bit 10 for load | U3, U6 |
| Registers | id 5, baud 6, torque enable 40, acceleration 41, goal position 42, goal time 44, goal speed 46, lock 55 | U1, U3 |
| Registers | present position 56, speed 58, load 60, voltage 62, temperature 63 | U1, U3 |
| Units | 4096 steps per turn, voltage 0.1 V, temperature 1 deg C, load 0.1 %, speed in steps/s | U1, W1 |
| Set the id | one servo on the bus: lock = 0, write id, lock = 1 | W1, U2 |
| Pico 2 watchdog | `machine.WDT` exists, maximum 16 777 ms on the RP2350 | M1, M2 |

Notes on the sources:

- The Feetech manual (U2) calls 0x06 RESET. The official libraries call 0x06 RECOVERY and use 0x0A for RESET. The driver uses neither.
- The position offset register (31) uses bit 11 as its sign bit. The driver does not write it.
- The manual has a typo in one ping example (`FF FF FF 01 02 01 FB`). Its table gives the correct `FF FF 01 02 01 FB`.

Sources:

- U1: Waveshare ST3215 memory table, https://files.waveshare.com/upload/2/27/ST3215%20memory%20register%20map-EN.xls
- U2: Feetech communication protocol manual, https://files.waveshare.com/upload/2/27/Communication_Protocol_User_Manual-EN%28191218-0923%29.pdf
- U3: https://raw.githubusercontent.com/ftservo/FTServo_Python/main/scservo_sdk/sms_sts.py
- U4: https://raw.githubusercontent.com/ftservo/FTServo_Python/main/scservo_sdk/protocol_packet_handler.py
- U5: https://raw.githubusercontent.com/ftservo/FTServo_Python/main/scservo_sdk/scservo_def.py
- U6: https://raw.githubusercontent.com/ftservo/FTServo_Arduino/main/src/SMS_STS.cpp
- U7: https://raw.githubusercontent.com/ftservo/FTServo_Arduino/main/src/INST.h
- W1: https://www.waveshare.com/wiki/ST3215_Servo
- W2: https://www.waveshare.com/wiki/Bus_Servo_Adapter_(A)
- W3: https://files.waveshare.com/wiki/Bus-Servo-Adapter-(A)/Bus%20Servo%20Adapter%20(A)-Sch.pdf
- M1: https://docs.micropython.org/en/latest/library/machine.WDT.html
- M2: https://raw.githubusercontent.com/micropython/micropython/master/ports/rp2/machine_wdt.c

## Not done

- No test on real servos, a real Pico or the BHL runtime.
- `aim/geometry.py` uses the DS3218 module heights. The ST3215 module has its tilt axis 9.3 mm lower (63.0 mm, `cad/parts/README.md`).
- The node does not read the servo load, voltage or temperature in its loop. `st3215.py` can read them.
- The node does not check that the measured angle follows the goal (a blocked gun).
