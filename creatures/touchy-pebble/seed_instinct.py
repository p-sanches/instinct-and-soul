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
