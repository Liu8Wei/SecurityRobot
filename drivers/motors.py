# Inside drivers/motors.py
def emergency_stop():
    # This turns off all motor pins immediately
    print("[HARDWARE] EMERGENCY STOP TRIGGERED")
    # For ESP32 (MicroPython) it would be: pin.value(0)
    # For Pi (Python) it would be: GPIO.output(pin, False)