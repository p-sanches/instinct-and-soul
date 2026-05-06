"""
recipes.py — instinct templates for the touchy-pebble tuner.

Each entry maps a recipe name to a spec:
  "args" — list of (arg_name, type, default) tuples used to fill {placeholders}
  "code" — async def run() coroutine string to deploy on the board

Templates use Python str.format substitution: `{name}` is filled at dispatch
time, `{{...}}` survives as `{...}` for the runtime's own .format() calls.
"""

INSTINCT_IDLE = """
async def run():
    import struct as _struct

    i2c = I2C(0, sda=Pin(6), scl=Pin(7), freq=400000)
    IMU = 0x6A
    i2c.writeto_mem(IMU, 0x10, bytes([0x40]))

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

RECIPES = {
    "constant": {
        "args": [("a", int, 0), ("b", int, 0)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty={a})
    motor_b = PWM(Pin(10), freq=1000, duty={b})
    send("motors constant a={a} b={b}")
    while True:
        await asyncio.sleep(1)
""",
    },
    "sweep": {
        "args": [],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty=0)
    motor_b = PWM(Pin(10), freq=1000, duty=0)
    send("sweep: ramping 0 -> 1023, step 25, 3s each")
    for duty in range(0, 1024, 25):
        motor_a.duty(duty)
        motor_b.duty(duty)
        send("sweep duty={}".format(duty))
        await asyncio.sleep_ms(3000)
    motor_a.duty(0)
    motor_b.duty(0)
    send("sweep done")
    while True:
        await asyncio.sleep(1)
""",
    },
    "heartbeat": {
        "args": [("duty", int, 80)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty=0)
    motor_b = PWM(Pin(10), freq=1000, duty=0)
    duty = {duty}
    send("heartbeat pattern duty={{}}".format(duty))
    while True:
        # thump
        motor_a.duty(duty)
        motor_b.duty(duty)
        await asyncio.sleep_ms(80)
        motor_a.duty(0)
        motor_b.duty(0)
        await asyncio.sleep_ms(120)
        # thump
        motor_a.duty(duty)
        motor_b.duty(duty)
        await asyncio.sleep_ms(80)
        motor_a.duty(0)
        motor_b.duty(0)
        # pause
        await asyncio.sleep_ms(700)
""",
    },
    "breathe": {
        "args": [("duty", int, 80)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty=0)
    motor_b = PWM(Pin(10), freq=1000, duty=0)
    peak = {duty}
    send("breathe pattern peak={{}}".format(peak))
    step = 0
    while True:
        import math
        d = int(peak * (math.sin(step * 0.033) ** 2))
        motor_a.duty(d)
        motor_b.duty(d)
        step += 1
        if step > 190:
            step = 0
        await asyncio.sleep_ms(16)
""",
    },
    "pulse": {
        "args": [("duty", int, 80), ("ms", int, 300)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty=0)
    motor_b = PWM(Pin(10), freq=1000, duty=0)
    duty = {duty}
    ms = {ms}
    send("pulse duty={{}} on/off={{}}ms".format(duty, ms))
    while True:
        motor_a.duty(duty)
        motor_b.duty(duty)
        await asyncio.sleep_ms(ms)
        motor_a.duty(0)
        motor_b.duty(0)
        await asyncio.sleep_ms(ms)
""",
    },
    "ripple": {
        "args": [("duty", int, 80)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty=0)
    motor_b = PWM(Pin(10), freq=1000, duty=0)
    duty = {duty}
    send("ripple pattern duty={{}}".format(duty))
    while True:
        motor_a.duty(duty)
        motor_b.duty(0)
        await asyncio.sleep_ms(200)
        motor_a.duty(0)
        motor_b.duty(duty)
        await asyncio.sleep_ms(200)
""",
    },
    "mix": {
        "args": [("a", int, 200), ("b", int, 600)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty={a})
    motor_b = PWM(Pin(10), freq=1000, duty={b})
    send("mix a={a} b={b}")
    while True:
        await asyncio.sleep(1)
""",
    },
    "mixsweep": {
        "args": [("a", int, 300)],
        "code": """
async def run():
    motor_a = PWM(Pin(9), freq=1000, duty={a})
    motor_b = PWM(Pin(10), freq=1000, duty=0)
    send("mixsweep: A fixed at {a}, sweeping B 0 -> 1023, step 50, 3s each")
    for duty_b in range(0, 1024, 50):
        motor_b.duty(duty_b)
        send("mixsweep A={a} B={{}}".format(duty_b))
        await asyncio.sleep_ms(3000)
    motor_a.duty(0)
    motor_b.duty(0)
    send("mixsweep done")
    while True:
        await asyncio.sleep(1)
""",
    },
    "imutune": {
        "args": [],
        "code": """
async def run():
    import struct as _struct

    i2c = I2C(0, sda=Pin(6), scl=Pin(7), freq=400000)
    IMU = 0x6A
    i2c.writeto_mem(IMU, 0x10, bytes([0x40]))  # accel 104 Hz

    motor_a = PWM(Pin(9), freq=1000, duty=0)
    motor_b = PWM(Pin(10), freq=1000, duty=0)

    async def measure_variance(n=60):
        bx, by, bz = [], [], []
        for _ in range(n):
            raw = i2c.readfrom_mem(IMU, 0x28, 6)
            rx, ry, rz = _struct.unpack('<hhh', raw)
            s = 0.061 / 1000
            bx.append(rx * s)
            by.append(ry * s)
            bz.append(rz * s)
            await asyncio.sleep_ms(10)
        mx = sum(bx) / n
        my = sum(by) / n
        mz = sum(bz) / n
        vx = sum((v - mx) ** 2 for v in bx) / n
        vy = sum((v - my) ** 2 for v in by) / n
        vz = sum((v - mz) ** 2 for v in bz) / n
        return vx, vy, vz

    send("imutune: measuring baseline then each duty level")
    send("imutune: DO NOT TOUCH the pebble during this test")
    await asyncio.sleep_ms(2000)

    vx, vy, vz = await measure_variance()
    send("duty=0 (baseline) var_x={:.8f} var_y={:.8f} var_z={:.8f} total={:.8f}".format(
        vx, vy, vz, vx + vy + vz))

    for duty in [50, 100, 130, 150, 175, 200, 250, 300, 400, 500, 700, 1023]:
        motor_a.duty(duty)
        motor_b.duty(duty)
        await asyncio.sleep_ms(500)

        vx, vy, vz = await measure_variance()
        send("duty={} var_x={:.8f} var_y={:.8f} var_z={:.8f} total={:.8f}".format(
            duty, vx, vy, vz, vx + vy + vz))

        motor_a.duty(0)
        motor_b.duty(0)
        await asyncio.sleep_ms(1000)

    send("imutune done")
    while True:
        await asyncio.sleep(1)
""",
    },
    "imulog": {
        "args": [],
        "code": """
async def run():
    import struct as _struct

    i2c = I2C(0, sda=Pin(6), scl=Pin(7), freq=400000)
    IMU = 0x6A
    i2c.writeto_mem(IMU, 0x10, bytes([0x40]))  # accel 104 Hz

    PWM(Pin(9), freq=1000, duty=0)
    PWM(Pin(10), freq=1000, duty=0)

    WINDOW = 30
    bx, by, bz = [], [], []

    send("imulog: live accel variance, motors off. pick it up, hold, shake...")
    while True:
        raw = i2c.readfrom_mem(IMU, 0x28, 6)
        rx, ry, rz = _struct.unpack('<hhh', raw)
        s = 0.061 / 1000
        bx.append(rx * s)
        by.append(ry * s)
        bz.append(rz * s)
        if len(bx) > WINDOW:
            bx.pop(0)
            by.pop(0)
            bz.pop(0)

        if len(bx) == WINDOW:
            mx = sum(bx) / WINDOW
            my = sum(by) / WINDOW
            mz = sum(bz) / WINDOW
            vx = sum((v - mx) ** 2 for v in bx) / WINDOW
            vy = sum((v - my) ** 2 for v in bx) / WINDOW
            vz = sum((v - mz) ** 2 for v in bz) / WINDOW
            total = vx + vy + vz
            send("var_x={:.8f} var_y={:.8f} var_z={:.8f} total={:.8f}".format(vx, vy, vz, total))
            bx.clear()
            by.clear()
            bz.clear()

        await asyncio.sleep_ms(10)
""",
    },
}
