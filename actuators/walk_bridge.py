"""Walking bridge: aim/run.py walk commands into the Berkeley Humanoid Lite (BHL) Python runtime.

AimGamepad replaces Se2Gamepad (BHL lowlevel, policy/gamepad.py). The gamepad still gives the mode buttons
(A + right bumper: RL mode, A + left bumper: init, X or a stick press: idle). The velocity comes from UDP:
the JSON lines of aim/run.py on 127.0.0.1:PORT, fields vx (m/s) and yaw_rate (rad/s).
Without a message for TIMEOUT seconds, the velocity command is zero, so the robot stands still.
How to plug it in: actuators/README.md.
"""
import json
import socket
import threading
import time

PORT = 5602
TIMEOUT = 0.5  # s
VX_MAX, YAW_MAX = 0.5, 1.0  # m/s, rad/s: the clip values of docs/locomotion/README.md, part C

try:
    from berkeley_humanoid_lite_lowlevel.policy.gamepad import Se2Gamepad as _Base
except ImportError:  # no BHL code: a small stand-in, so the bridge runs and tests without it
    class _Base:
        def __init__(self):
            self.commands = {"velocity_x": 0.0, "velocity_y": 0.0, "velocity_yaw": 0.0, "mode_switch": 0}
            self._stopped = threading.Event()

        def run(self):
            pass

        def stop(self):
            self._stopped.set()

        def _update_command_buffer(self):
            pass


def clip(x, m):
    return min(max(x, -m), m)


class AimGamepad(_Base):
    def __init__(self, *args, port=PORT, **kwargs):
        super().__init__(*args, **kwargs)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(0.05)
        self._vel, self._t = (0.0, 0.0), -float("inf")

    def run(self):
        super().run()  # the BHL gamepad thread, for the mode buttons
        self.start_udp()

    def start_udp(self):
        threading.Thread(target=self._udp_loop, daemon=True).start()

    def _udp_loop(self):
        while not self._stopped.is_set():
            try:
                m = json.loads(self.sock.recv(65536))
                vx, yaw = float(m["vx"]), float(m["yaw_rate"])
                if vx == vx and yaw == yaw:  # not NaN
                    self._vel, self._t = (clip(vx, VX_MAX), clip(yaw, YAW_MAX)), time.monotonic()
            except (socket.timeout, ValueError, KeyError, TypeError):
                pass
            self._apply()

    def _apply(self):
        vx, yaw = self._vel if time.monotonic() - self._t < TIMEOUT else (0.0, 0.0)
        self.commands.update(velocity_x=vx, velocity_y=0.0, velocity_yaw=yaw)

    def _update_command_buffer(self):  # the gamepad thread: keep its mode switch, replace the stick velocities
        super()._update_command_buffer()
        self._apply()


if __name__ == "__main__":  # print the command that the policy would get
    g = AimGamepad()
    g.start_udp()
    try:
        while True:
            print({k: round(v, 3) for k, v in g.commands.items()})
            time.sleep(0.2)
    except KeyboardInterrupt:
        g.stop()
