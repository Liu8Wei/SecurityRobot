import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# --- 1. I2C Bus Scan & PCA9685 Setup ---
print("Initializing I2C bus...")
try:
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    
    while not i2c_bus.try_lock():
        pass
    found_addrs = i2c_bus.scan()
    i2c_bus.unlock()
    
    pca_address = 0x40
    if 0x41 in found_addrs:
        pca_address = 0x41
    elif 0x40 in found_addrs:
        pca_address = 0x40
    else:
        exit("\n[!] No devices found. Check wiring!")

    print(f"\nConnecting to PCA9685 at address {hex(pca_address)}...")
    pca = PCA9685(i2c_bus, address=pca_address)
    pca.frequency = 50

except ValueError as e:
    exit(f"[!] I2C Error: Could not setup PCA9685. \nDetails: {e}")

# --- 2. EXACT SERVO CHANNEL CONFIGURATION ---
# Updated to match your physical wiring exactly!
SERVO_BASE_CHAN     = 0
SERVO_SHOULDER_CHAN = 8
SERVO_ELBOW_CHAN    = 12
SERVO_WRIST_CHAN    = 7
SERVO_GRIPPER_CHAN  = 3

SERVO_MIN_US = 500
SERVO_MAX_US = 2500

servos = {
    "BASE"     : servo.Servo(pca.channels[SERVO_BASE_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
    "SHOULDER" : servo.Servo(pca.channels[SERVO_SHOULDER_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
    "ELBOW"    : servo.Servo(pca.channels[SERVO_ELBOW_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
    "WRIST"    : servo.Servo(pca.channels[SERVO_WRIST_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
    "GRIPPER"  : servo.Servo(pca.channels[SERVO_GRIPPER_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
}

angles = { "BASE": 90, "SHOULDER": 90, "ELBOW": 90, "WRIST": 90, "GRIPPER": 90 }

def print_status():
    print("\n" + "="*50)
    print("      PCA9685 ROBOTIC ARM - INTERACTIVE DEBUGGER")
    print("="*50)
    print(f" [1] BASE      (Channel {SERVO_BASE_CHAN:02d}) -> Current Angle: {angles['BASE']}°")
    print(f" [2] SHOULDER  (Channel {SERVO_SHOULDER_CHAN:02d}) -> Current Angle: {angles['SHOULDER']}°")
    print(f" [3] ELBOW     (Channel {SERVO_ELBOW_CHAN:02d}) -> Current Angle: {angles['ELBOW']}°")
    print(f" [4] WRIST     (Channel {SERVO_WRIST_CHAN:02d}) -> Current Angle: {angles['WRIST']}°")
    print(f" [5] GRIPPER   (Channel {SERVO_GRIPPER_CHAN:02d}) -> Current Angle: {angles['GRIPPER']}°")
    print("--------------------------------------------------")
    print(" [H] Send All to Home (90°)")
    print(" [R] Relax/Release All Servos (Deactivates Hold)")
    print(" [E] Exit Debugger")
    print("="*50)

print("\n[!] Skipping automatic startup sweep to prevent power supply crashes.")
print("Servos will remain relaxed until you manually send a command.")

try:
    while True:
        print_status()
        choice = input("Select an option (1-5, H, R, E): ").strip().upper()
        
        if choice == 'E':
            break
        elif choice == 'H':
            print("\nHoming all joints ONE BY ONE...")
            for name, s in servos.items():
                s.angle = 90
                angles[name] = 90
                time.sleep(0.5)
        elif choice == 'R':
            print("\nRelaxing all servos. You can now turn them by hand safely.")
            for name, s in servos.items():
                s.angle = None
            time.sleep(1)
        elif choice in ['1', '2', '3', '4', '5']:
            joint_map = { '1': 'BASE', '2': 'SHOULDER', '3': 'ELBOW', '4': 'WRIST', '5': 'GRIPPER' }
            joint_name = joint_map[choice]
            
            try:
                angle_input = input(f"Enter new angle for {joint_name} (0 to 180 degrees): ").strip()
                target_angle = int(angle_input)
                
                if 0 <= target_angle <= 180:
                    print(f"Moving {joint_name} to {target_angle}°...")
                    servos[joint_name].angle = target_angle
                    angles[joint_name] = target_angle
                else:
                    print("[!] Angle must be between 0 and 180 degrees.")
            except ValueError:
                print("[!] Invalid number. Please enter a whole integer.")
            time.sleep(1)
        else:
            print("[!] Invalid choice.")

except KeyboardInterrupt:
    print("\n[!] Exiting debugger.")
finally:
    print("\nRelaxing servos and deinitializing PCA9685...")
    for name, s in servos.items():
        s.angle = None
    pca.deinit()
    print("Hardware released safely.")