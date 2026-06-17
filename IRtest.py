import time
import pigpio

# Connect to the Pi's motor/pin engine
pi = pigpio.pi()
if not pi.connected:
    exit("[!] pigpio not running. Run: sudo pigpiod")

# Your exact IR pins from config.py
IR_PINS = [5, 6, 12, 16, 20]

# Tell the Pi to listen to these pins
for pin in IR_PINS:
    pi.set_mode(pin, pigpio.INPUT)

print("======================================")
print(" SENSOR TERMINAL TEST (Ctrl+C to stop)")
print("======================================")

try:
    while True:
        # Grab the live reading (0 or 1) from all 5 sensors
        readings = [pi.read(pin) for pin in IR_PINS]
        
        # Print it to the screen
        print(f"IR Array (Left -> Right): {readings}")
        
        time.sleep(0.5)

except KeyboardInterrupt:
    pi.stop()
    print("\n[!] Test stopped cleanly.")