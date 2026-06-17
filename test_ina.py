import time
import board
import busio

# IMPORTANT: You must install the INA219 library first!
# Run this in your terminal: pip3 install adafruit-circuitpython-ina219
from adafruit_ina219 import INA219

# --- 1. I2C Bus & Sensor Setup ---
print("Initializing I2C bus for INA219 Power Monitor...")
try:
    # Initialize the I2C bus using the Pi's default SDA/SCL pins
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    
    # Initialize the INA219 module at its default address (0x40)
    ina219 = INA219(i2c_bus, addr=0x40)
    
    print("[SUCCESS] INA219 Sensor found and configured!")
except ValueError as e:
    print(f"\n[!] I2C Error: Could not find INA219. Check wiring! \nDetails: {e}")
    exit()

# --- 2. Live Telemetry Loop ---
print("\n==================================================")
print("           INA219 POWER MONITOR TEST              ")
print("==================================================")
print("Press CTRL+C to stop the test.")
print("--------------------------------------------------")

try:
    while True:
        # 1. Bus Voltage: The voltage from your battery/power source
        bus_voltage = ina219.bus_voltage
        
        # 2. Shunt Voltage: The tiny voltage drop across the sensor's resistor (used to calculate current)
        shunt_voltage = ina219.shunt_voltage
        
        # 3. Current: The amount of electricity being pulled by your robot
        current_ma = ina219.current
        
        # 4. Power: Total power consumption (Voltage x Current)
        power_mw = ina219.power

        # Print the telemetry in a clean format
        print(f"Battery Voltage: {bus_voltage:6.2f} V")
        print(f"Current Draw:    {current_ma:6.2f} mA")
        print(f"Power Usage:     {power_mw:6.2f} mW")
        print("-" * 50)
        
        # Wait 1 second before the next reading
        time.sleep(1)

except KeyboardInterrupt:
    print("\n[!] Test stopped by user.")
except Exception as e:
    print(f"\n[!] An error occurred during reading: {e}")