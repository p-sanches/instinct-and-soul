"""
test_spine.py — spine with textual terminal UI.

Features:
  - Status bar: connection state based on heartbeat
  - Log panel: scrolling messages from the board
  - Input box: set motor duty values, submit with enter

Requires: pip install websockets textual

Input commands:
  200 300    — set motor A to 200, motor B to 300 (duty 0–1023)
  500        — set both motors to 500
  0          — stop both motors
"""

import asyncio
import time
import websockets
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header, Footer, Input, RichLog, Static

PORT = 8765
HEARTBEAT_TIMEOUT = 12

# ── Instinct templates ──────────────────────────────────────────────────────

INSTINCT_IDLE = """
async def run():
    import struct as _struct

    i2c = I2C(0, sda=Pin(6), scl=Pin(7), freq=400000)
    IMU = 0x6A

    i2c.writeto_mem(IMU, 0x10, bytes([0x40]))  # accel: 104 Hz, +/-2g

    WINDOW = 60
    buf_x = []
    buf_y = []
    buf_z = []

    while True:
        raw = i2c.readfrom_mem(IMU, 0x28, 6)
        rx, ry, rz = _struct.unpack('<hhh', raw)
        s = 0.061 / 1000
        ax, ay, az = rx * s, ry * s, rz * s
        buf_x.append(ax)
        buf_y.append(ay)
        buf_z.append(az)
        if len(buf_x) > WINDOW:
            buf_x.pop(0)
            buf_y.pop(0)
            buf_z.pop(0)

        if len(buf_x) == WINDOW:
            mx = sum(buf_x) / WINDOW
            my = sum(buf_y) / WINDOW
            mz = sum(buf_z) / WINDOW
            vx = sum((v - mx) ** 2 for v in buf_x) / WINDOW
            vy = sum((v - my) ** 2 for v in buf_y) / WINDOW
            vz = sum((v - mz) ** 2 for v in buf_z) / WINDOW
            send("accel x={:.4f} y={:.4f} z={:.4f} var_x={:.6f} var_y={:.6f} var_z={:.6f}".format(
                mx, my, mz, vx, vy, vz))
            buf_x.clear()
            buf_y.clear()
            buf_z.clear()

        await asyncio.sleep_ms(33)
"""

INSTINCT_MOTOR = """
async def run():
    import struct as _struct

    i2c = I2C(0, sda=Pin(6), scl=Pin(7), freq=400000)
    IMU = 0x6A

    motor_a = PWM(Pin(9), freq=1000, duty={a})
    motor_b = PWM(Pin(10), freq=1000, duty={b})
    send("motors=({a},{b})")

    i2c.writeto_mem(IMU, 0x10, bytes([0x40]))  # accel: 104 Hz, +/-2g

    WINDOW = 60
    buf_x = []
    buf_y = []
    buf_z = []

    while True:
        raw = i2c.readfrom_mem(IMU, 0x28, 6)
        rx, ry, rz = _struct.unpack('<hhh', raw)
        s = 0.061 / 1000
        ax, ay, az = rx * s, ry * s, rz * s
        buf_x.append(ax)
        buf_y.append(ay)
        buf_z.append(az)
        if len(buf_x) > WINDOW:
            buf_x.pop(0)
            buf_y.pop(0)
            buf_z.pop(0)

        if len(buf_x) == WINDOW:
            mx = sum(buf_x) / WINDOW
            my = sum(buf_y) / WINDOW
            mz = sum(buf_z) / WINDOW
            vx = sum((v - mx) ** 2 for v in buf_x) / WINDOW
            vy = sum((v - my) ** 2 for v in buf_y) / WINDOW
            vz = sum((v - mz) ** 2 for v in buf_z) / WINDOW
            send("motors=({a},{b}) accel x={{:.4f}} y={{:.4f}} z={{:.4f}} var_x={{:.6f}} var_y={{:.6f}} var_z={{:.6f}}".format(
                mx, my, mz, vx, vy, vz))
            buf_x.clear()
            buf_y.clear()
            buf_z.clear()

        await asyncio.sleep_ms(33)
"""

# ── App ─────────────────────────────────────────────────────────────────────

class SpineApp(App):
    CSS = """
    #status {
        dock: top;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    #log {
        height: 1fr;
        border: solid $primary;
    }
    #input {
        dock: bottom;
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit"), ("escape", "quit", "Quit"), ("ctrl+q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.board_ws = None
        self.last_heartbeat = 0.0
        self.motor_a = 0
        self.motor_b = 0
        self._ws_server = None

    def compose(self) -> ComposeResult:
        yield Static("● disconnected", id="status")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Input(placeholder="motor duty: <value> or <a> <b>  (0–1023)", id="input")

    def on_mount(self) -> None:
        self.run_worker(self.ws_server(), exclusive=False)
        self.set_interval(1, self.update_status)
        self.log_msg("spine: listening on port {}".format(PORT))

    def log_msg(self, msg, style=""):
        ts = time.strftime("%H:%M:%S")
        try:
            log = self.query_one("#log", RichLog)
        except Exception:
            return
        if style:
            log.write("[{}]{}[/{}]  {}".format(style, ts, style, msg))
        else:
            log.write("{}  {}".format(ts, msg))

    def update_status(self) -> None:
        try:
            status = self.query_one("#status", Static)
        except Exception:
            return
        if self.board_ws is not None and (time.time() - self.last_heartbeat) < HEARTBEAT_TIMEOUT:
            status.update("[bold green]● connected[/]  motors: ({}, {})".format(
                self.motor_a, self.motor_b))
        elif self.board_ws is not None:
            status.update("[bold yellow]● heartbeat lost[/]  motors: ({}, {})".format(
                self.motor_a, self.motor_b))
        else:
            status.update("[bold red]● disconnected[/]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value.strip()
        event.input.clear()

        if not line:
            return

        parts = line.split()
        try:
            if len(parts) == 1:
                a = b = int(parts[0])
            elif len(parts) == 2:
                a, b = int(parts[0]), int(parts[1])
            else:
                self.log_msg("usage: <duty> or <duty_a> <duty_b>  (0–1023)", style="yellow")
                return
        except ValueError:
            self.log_msg("usage: <duty> or <duty_a> <duty_b>  (0–1023)", style="yellow")
            return

        a = max(0, min(1023, a))
        b = max(0, min(1023, b))
        self.motor_a, self.motor_b = a, b

        if self.board_ws is None:
            self.log_msg("no board connected", style="yellow")
            return

        code = INSTINCT_MOTOR.format(a=a, b=b)
        await self.board_ws.send(code)
        self.log_msg("sent motors=({},{})".format(a, b), style="cyan")

    async def ws_handler(self, ws):
        self.board_ws = ws
        self.last_heartbeat = time.time()
        addr = ws.remote_address
        self.log_msg("board connected from {}:{}".format(addr[0], addr[1]), style="green")

        await ws.send(INSTINCT_IDLE)
        self.log_msg("sent idle instinct with IMU reporting", style="dim")

        try:
            async for msg in ws:
                if msg == "HEARTBEAT":
                    self.last_heartbeat = time.time()
                elif msg.startswith("CRASH:"):
                    self.log_msg(msg, style="bold red")
                else:
                    self.log_msg(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            self.board_ws = None
            self.log_msg("board disconnected", style="red")

    def key_escape(self) -> None:
        self.action_quit()

    def action_quit(self) -> None:
        if self.board_ws is not None:
            self.board_ws.transport.close()
        if self._ws_server is not None:
            self._ws_server.close()
        self.exit()

    async def ws_server(self):
        try:
            self._ws_server = await websockets.serve(self.ws_handler, "0.0.0.0", PORT)
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
        finally:
            if self._ws_server is not None:
                self._ws_server.close()


if __name__ == "__main__":
    SpineApp().run()