import pigpio
pi = pigpio.pi()
for pin in [17, 24, 25, 23]: pi.set_PWM_dutycycle(pin, 0)
pi.stop()
print("[SYSTEM] All motor pins forcefully reset to 0V.")
