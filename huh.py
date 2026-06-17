import time
import pigpio

# Hardware I2C Pins on Raspberry Pi Zero 2W
SDA_PIN = 2  # BCM 2, Physical Pin 3
SCL_PIN = 3  # BCM 3, Physical Pin 5

# Target I2C Address (0x40 = 64 in decimal)
TARGET_ADDRESS = 0x40

# Connect to pigpio
pi = pigpio.pi()
if not pi.connected:
    exit("[!] pigpio daemon is not running! Run: sudo pigpiod")

print("==================================================")
print("        MANUAL I2C HARDWARE DIAGNOSTICS")
print("==================================================")

# --- TEST 1: STATIC PHYSICAL LINE VOLTAGE TEST ---
print("\n[TEST 1] Checking physical line voltages (pull-ups)...")
print("--------------------------------------------------")
# Note: RPi Pins 3 & 5 have physical 1.8k Ohm pull-up resistors to 3.3V built-in.
# Therefore, when idle, they MUST read as HIGH (1 / 3.3V).

sda_state = pi.read(SDA_PIN)
scl_state = pi.read(SCL_PIN)

print(f"SDA (GPIO 2, Physical Pin 3) State: {'HIGH (3.3V)' if sda_state == 1 else 'LOW (0V)'}")
print(f"SCL (GPIO 3, Physical Pin 5) State: {'HIGH (3.3V)' if scl_state == 1 else 'LOW (0V)'}")

is_shorted = False
if sda_state == 0:
    print("[CRITICAL] SDA line is stuck at 0V! This indicates a short circuit to Ground (GND) or crossed wires.")
    is_shorted = True
if scl_state == 0:
    print("[CRITICAL] SCL line is stuck at 0V! This indicates a short circuit to Ground (GND) or crossed wires.")
    is_shorted = True

if is_shorted:
    print("\n[!] DIAGNOSIS: High probability of a hardware short circuit.")
    print("    Unplug your PCA9685 completely and run this script again.")
    print("    If the pins return to HIGH, your PCA9685 is miswired or damaged.")
    pi.stop()
    exit()
else:
    print("[SUCCESS] Both lines are idling at 3.3V. Pull-up resistors are healthy.")

# --- TEST 2: RAW I2C PING ATTEMPT ---
print("\n[TEST 2] Attempting manual low-level register ping...")
print("--------------------------------------------------")
print(f"Sending raw start/stop handshake to address 0x{TARGET_ADDRESS:02X}...")

try:
    # Try to open a low-level I2C handle using bus 1
    # This directly triggers the Broadcom hardware I2C controller
    handle = pi.i2c_open(1, TARGET_ADDRESS, 0)
    
    # Send a quick probe (requesting a read of register 0)
    print(f"I2C Handle opened successfully. Sending handshake packet...")
    pi.i2c_read_device(handle, 1) # Read 1 byte
    
    print(f"\n>>> [WOW!] SUCCESS! Received ACK from device at address 0x{TARGET_ADDRESS:02X}!")
    print("    Your wiring is structurally perfect and the chip is responding.")
    pi.i2c_close(handle)

except pigpio.error as e:
    # Handle low-level system error responses
    err_num = e.value
    print(f"I2C Handshake failed with pigpio error code: {err_num}")
    
    if err_num == -82: # PI_BAD_I2C_WHL
        print(" -> ERROR -82: No ACK returned from address 0x40. The physical board didn't reply.")
        print("    Possible causes:")
        print("    1. VCC (side pin) is completely unpowered. The chip's transceiver is offline.")
        print("    2. SCL & SDA are flipped (clock going to data, data to clock).")
        print("    3. The PCA9685 address is not 0x40 (Check A0-A5 solder pads).")
    elif err_num == -81: # PI_BAD_I2C_BUS
        print(" -> ERROR -81: The I2C kernel module is busy or blocked by another program.")
        print("    Try closing any other Python scripts running in VSC.")
    else:
        print(f" -> Unexpected hardware error: {e}")

# --- TEST 3: AUTO SCAN BUS FOR ANY HIDDEN ADDRESSES ---
print("\n[TEST 3] Running full manual software scan...")
print("--------------------------------------------------")
print("Scanning addresses 0x03 to 0x77...")

found_devices = []
for addr in range(0x03, 0x78):
    try:
        h = pi.i2c_open(1, addr, 0)
        # Quick read to see if device is present and responds
        pi.i2c_read_device(h, 1)
        found_devices.append(f"0x{addr:02X}")
        pi.i2c_close(h)
    except pigpio.error:
        # Ignore errors (failed ACKs) as we scan empty slots
        pass

if found_devices:
    if len(found_devices) > 100:
        print("\n" + "!" * 50)
        print(" [CRITICAL WARNING] 'GHOST BUS' / 'SDA STUCK LOW' DETECTED!")
        print("!" * 50)
        print(f"The scan returned {len(found_devices)} responding addresses (virtually the entire bus!).")
        print("--------------------------------------------------")
        print("Why is this happening?")
        print("In I2C communication, an Acknowledgement (ACK) is triggered when a slave device pulls")
        print("the SDA (data) line physically LOW (0V) during the 9th clock cycle.")
        print("")
        print("If your SDA wire gets shorted to Ground (GND) during transmission, the Pi's hardware controller")
        print("will read a constant 0V on SDA and mistake it as a successful ACK on literally every address scanned.")
        print("")
        print("This is why Test 1 read 'HIGH' at static idle, but Test 3 found devices everywhere!")
        print("")
        print("HOW TO FIX THIS PHYSICALLY:")
        print("1. UNPLUG the SDA (Pin 3) and SCL (Pin 5) wires from your Pi completely. Run this diagnostics script again.")
        print("   -> If the scan still shows devices everywhere, your Pi's hardware I2C pin driver is damaged.")
        print("   -> If the scan correctly shows '0 devices detected', your Pi is healthy! The short is on your PCA9685.")
        print("2. Check the PCA9685 board for physical solder bridges between SDA and SCL or GND.")
        print("3. Ensure SCL and SDA are not swapped. If SCL is plugged into SDA, it will pull the data")
        print("   line low dynamically during transfer clock cycles.")
        print("4. Verify the GND pin next to VCC on the PCA9685 header is connected to a Pi Ground pin.")
        print("   Without a common ground reference, the signal voltage collapses when the clock begins ticking.")
    else:
        print(f"[SUCCESS] Scanner found active device(s) at: {', '.join(found_devices)}")
        if "0x40" not in found_devices:
            print("Warning: Address 0x40 was not found. If another address appeared, update your script to that number!")
else:
    print("[FAILED] Scan complete. 0 devices detected on the bus.")

pi.stop()
print("\nDiagnostics complete.")