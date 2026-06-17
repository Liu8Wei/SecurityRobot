import time
import pigpio

# Hardware Pins
TRIG = 22
ECHO = 27

# Connect to pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    exit("[!] pigpio not running. Run: sudo pigpiod")

# Setup pins
pi.set_mode(TRIG, pigpio.OUTPUT)
pi.set_mode(ECHO, pigpio.INPUT)

# Ensure trigger is low to start
pi.write(TRIG, 0)
time.sleep(0.5)

print("========================================")
print(" ULTRASONIC SENSOR TEST (Ctrl+C to stop)")
print("========================================")
print("Waiting for sensor to settle...")
time.sleep(1)

try:
    while True:
        # 1. Send a 10 microsecond pulse to wake up the sensor
        pi.gpio_trigger(TRIG, 10, 1)

        # 2. Wait for the ECHO pin to go HIGH (Start of the sound wave)
        start_tick = pi.get_current_tick()
        timeout = start_tick
        while pi.read(ECHO) == 0:
            start_tick = pi.get_current_tick()
            if pigpio.tickDiff(timeout, start_tick) > 500000: # 0.5s timeout
                break
                
        # 3. Wait for the ECHO pin to go LOW (Sound wave bounced back)
        end_tick = pi.get_current_tick()
        while pi.read(ECHO) == 1:
            end_tick = pi.get_current_tick()
            if pigpio.tickDiff(start_tick, end_tick) > 500000:
                break

        # 4. Calculate the time difference in microseconds
        diff_us = pigpio.tickDiff(start_tick, end_tick)
        
        # Speed of sound = 34300 cm/s. Distance = (Time / 1,000,000) * (34300 / 2)
        distance_cm = (diff_us / 1000000.0) * 17150
        
        # Filter out junk readings (timeout or out of physical range)
        if 2.0 <= distance_cm <= 400.0:
            print(f"Distance: {distance_cm:.1f} cm")
        else:
            print("[!] Out of range or sensor timeout")

        time.sleep(0.5)

except KeyboardInterrupt:
    pi.stop()
    print("\n[!] Test stopped cleanly.")