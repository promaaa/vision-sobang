"""Actuator node: aim commands in, pan-tilt servos and water relay out, measured angles back.

python actuator_node.py --mock
python actuator_node.py --servo-port /dev/ttyACM0 --pico-port /dev/ttyACM1 [--water trigger|pump] [--calib calib.json]

In:  UDP 127.0.0.1:CMD_PORT, the JSON command lines of aim/run.py (pan, tilt in rad, pump_on).
Out: ST3215 servos (ids in the calibration), the Pico relay link, and one JSON line per tick to each FEEDBACK_PORTS:
     {"t": time.monotonic() when the angles were read, "pan": rad, "tilt": rad, "water": bool, "estop": bool}
"""
import argparse
import json
import math
import socket
import sys
import time

from st3215 import ServoError

HOST = "127.0.0.1"
CMD_PORT = 5601  # aim/run.py commands
FEEDBACK_PORTS = [5603, 5604]  # measured angles: 5603 aim/run.py --feedback, 5604 aim/send_test_detections.py --feedback
RATE = 50.0  # Hz
CMD_TIMEOUT = 0.5  # s, water off and servos hold when no command arrives for this time
TICKS_PER_RAD = 4096 / (2 * math.pi)

# Calibration: ticks at angle 0, sign, limits and speed for each axis. Calibration steps: actuators/README.md.
DEFAULT_CALIB = {
    "pan": {"id": 1, "zero": 2048, "direction": 1, "min_deg": -90, "max_deg": 90, "max_speed_dps": 180},
    "tilt": {"id": 2, "zero": 2048, "direction": 1, "min_deg": -90, "max_deg": 90, "max_speed_dps": 180},
}


def clip_rad(c, rad):
    return min(max(rad, math.radians(c["min_deg"])), math.radians(c["max_deg"]))


def to_ticks(c, rad):
    return round(c["zero"] + c["direction"] * clip_rad(c, rad) * TICKS_PER_RAD)


def to_rad(c, ticks):
    return (ticks - c["zero"]) * c["direction"] / TICKS_PER_RAD


def step_toward(current, goal, max_step):
    return current + min(max(goal - current, -max_step), max_step)


class MockServos:
    """Two servos that move to the goal at their maximum speed."""

    def __init__(self, calib):
        self.calib, self.angles = calib, {"pan": 0.0, "tilt": 0.0}

    def move(self, goals, dt):
        for k, g in goals.items():
            self.angles[k] = step_toward(self.angles[k], g, math.radians(self.calib[k]["max_speed_dps"]) * dt)

    def read(self):
        return self.angles["pan"], self.angles["tilt"]


class Servos:
    def __init__(self, calib, device):
        from st3215 import Bus
        self.calib, self.bus = calib, Bus.open(device)
        for c in calib.values():
            if not self.bus.ping(c["id"]):
                sys.exit(f"servo id {c['id']} does not answer on {device}")
            self.bus.torque(c["id"], True)

    def move(self, goals, dt):
        self.bus.sync_write_goal({self.calib[k]["id"]: (to_ticks(self.calib[k], g), round(math.radians(self.calib[k]["max_speed_dps"]) * TICKS_PER_RAD), 0)
                                  for k, g in goals.items()})

    def read(self):
        return tuple(to_rad(self.calib[k], self.bus.state(self.calib[k]["id"])["position"]) for k in ("pan", "tilt"))


class MockPico:
    estop = False

    def set(self, channel, on):
        self.on = on


class Pico:
    """Line link to actuators/pico_fw/main.py. One line per tick also feeds the Pico timeout."""

    def __init__(self, device):
        import serial
        self.ser, self.estop, self.buf = serial.Serial(device, 115200, timeout=0), False, b""

    def set(self, channel, on):  # channel "T" (gun trigger) or "P" (pump)
        self.ser.write(f"{channel}{int(on)}\n".encode())
        self.buf = (self.buf + self.ser.read(self.ser.in_waiting or 1))[-256:]
        for line in self.buf.split(b"\n")[:-1]:
            if line.startswith(b"OK"):
                self.estop = b"E1" in line
            elif line.startswith(b"OFF ESTOP") or line.startswith(b"ERR ESTOP"):
                self.estop = True
        self.buf = self.buf.split(b"\n")[-1]


def run(servos, pico, channel, calib, seconds=None):
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind((HOST, CMD_PORT))
    rx.setblocking(False)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    goals = dict(zip(("pan", "tilt"), servos.read()))
    cmd, t_cmd, dt = None, -math.inf, 1 / RATE
    tick = start = time.monotonic()
    while seconds is None or tick - start < seconds:
        while True:
            try:
                c = json.loads(rx.recv(65536))
                c = dict(pan=float(c["pan"]), tilt=float(c["tilt"]), pump_on=c["pump_on"] is True)
                if not (math.isfinite(c["pan"]) and math.isfinite(c["tilt"])):
                    raise ValueError("pan or tilt is not finite")
                cmd, t_cmd = c, time.monotonic()
            except BlockingIOError:
                break
            except (ValueError, KeyError, TypeError) as e:
                print(f"bad command line: {e}", file=sys.stderr)
        fresh = cmd is not None and time.monotonic() - t_cmd < CMD_TIMEOUT
        if fresh:  # software rate limit on the goal, the servo limits its speed too
            for k in goals:
                goals[k] = step_toward(goals[k], clip_rad(calib[k], float(cmd[k])), math.radians(calib[k]["max_speed_dps"]) * dt)
        try:
            servos.move(goals, dt)
            pan, tilt = servos.read()
            servo_ok = True
        except (ServoError, OSError) as e:  # a lost servo reply: water off, no feedback this tick
            print(f"servo bus: {e}", file=sys.stderr)
            servo_ok = False
        t_read = time.monotonic()
        water = fresh and servo_ok and cmd["pump_on"] and not pico.estop
        pico.set(channel, water)
        line = json.dumps(dict(t=round(t_read, 4), pan=round(pan, 5), tilt=round(tilt, 5), water=water, estop=pico.estop))
        for port in FEEDBACK_PORTS if servo_ok else ():
            try:
                tx.sendto(line.encode(), (HOST, port))
            except OSError:
                pass
        tick += dt
        time.sleep(max(0.0, tick - time.monotonic()))
    pico.set(channel, False)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mock", action="store_true", help="no hardware: simulated servos and relay")
    ap.add_argument("--servo-port", default="/dev/ttyACM0")
    ap.add_argument("--pico-port", default="/dev/ttyACM1")
    ap.add_argument("--water", choices=("trigger", "pump"), default="trigger", help="relay channel for pump_on: trigger (A) or pump (B, E)")
    ap.add_argument("--calib", help="calibration JSON, same keys as DEFAULT_CALIB")
    ap.add_argument("--seconds", type=float, help="stop after this time (for tests)")
    a = ap.parse_args()
    calib = DEFAULT_CALIB
    if a.calib:
        with open(a.calib) as f:
            calib = {k: dict(DEFAULT_CALIB[k], **v) for k, v in json.load(f).items()}
    servos = MockServos(calib) if a.mock else Servos(calib, a.servo_port)
    pico = MockPico() if a.mock else Pico(a.pico_port)
    print(f"actuator_node: {'mock' if a.mock else 'hardware'}, commands on udp {CMD_PORT}, feedback to {FEEDBACK_PORTS}", file=sys.stderr)
    try:
        run(servos, pico, "T" if a.water == "trigger" else "P", calib, a.seconds)
    except KeyboardInterrupt:
        pico.set("T" if a.water == "trigger" else "P", False)


if __name__ == "__main__":
    main()
