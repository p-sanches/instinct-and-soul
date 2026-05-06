from machine import Pin, PWM
import time

# Setup PWM on D9 and D10
# On XIAO ESP32C3: D9 = GPIO9, D10 = GPIO10
motor1 = PWM(Pin(9), freq=1000, duty=0)
motor2 = PWM(Pin(10), freq=1000, duty=0)

def vibrate(motor, duty=512, duration=1.0):
    """Run a motor at given duty (0-1023) for duration seconds."""
    motor.duty(duty)
    time.sleep(duration)
    motor.duty(0)

print("Testing Motor 1 (D9)...")
vibrate(motor1)
time.sleep(0.5)

print("Testing Motor 2 (D10)...")
vibrate(motor2)
time.sleep(0.5)

print("Both motors together...")
motor1.duty(512)
motor2.duty(512)
time.sleep(1)
motor1.duty(0)
motor2.duty(0)
time.sleep(0.5)

print("Ramp up/down Motor 1...")
for d in range(0, 1024, 64):
    motor1.duty(d)
    time.sleep(0.05)
for d in range(1023, -1, -64):
    motor1.duty(d)
    time.sleep(0.05)
motor1.duty(0)
time.sleep(0.5)

print("Alternating pattern...")
for _ in range(5):
    motor1.duty(700)
    motor2.duty(0)
    time.sleep(0.3)
    motor1.duty(0)
    motor2.duty(700)
    time.sleep(0.3)

motor1.duty(0)
motor2.duty(0)

print("Done!")
