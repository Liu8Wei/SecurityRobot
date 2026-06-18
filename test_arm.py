import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# --- 1. I2C Setup ---
print("Initializing I2C bus...")
try:
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c_bus, address=0x41)
    pca.frequency = 50
except ValueError as e:
    exit(f"[!] I2C Error. Details: {e}")

# --- 2. EXACT SERVO CHANNEL CONFIGURATION ---
SERVO_BASE_CHAN     = 0
SERVO_SHOULDER_CHAN = 8
SERVO_ELBOW_CHAN    = 12
SERVO_GRIPPER_CHAN  = 3

SERVO_MIN_US = 500
SERVO_MAX_US = 2500

servos = {
    # Treat it as a normal servo, but define the larger range!
    "BASE"     : servo.Servo(pca.channels[SERVO_BASE_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US, actuation_range=360),
    "SHOULDER" : servo.Servo(pca.channels[SERVO_SHOULDER_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
    "ELBOW"    : servo.Servo(pca.channels[SERVO_ELBOW_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
    "GRIPPER"  : servo.Servo(pca.channels[SERVO_GRIPPER_CHAN], min_pulse=SERVO_MIN_US, max_pulse=SERVO_MAX_US),
}

# Start with all angles labeled as OFF
angles = { "BASE": "STOPPED", "SHOULDER": "OFF", "ELBOW": "OFF", "GRIPPER": "OFF" }

def print_status():
    print("\n" + "="*50)
    print("      PCA9685 ROBOTIC ARM - INTERACTIVE DEBUGGER")
    print("="*50)
    print(f" [1] BASE      (Channel {SERVO_BASE_CHAN:02d}) -> Status: {angles['BASE']} (360° Mode)")
    print(f" [2] SHOULDER  (Channel {SERVO_SHOULDER_CHAN:02d}) -> Current Angle: {angles['SHOULDER']}")
    print(f" [3] ELBOW     (Channel {SERVO_ELBOW_CHAN:02d}) -> Current Angle: {angles['ELBOW']}")
    print(f" [4] GRIPPER   (Channel {SERVO_GRIPPER_CHAN:02d}) -> Current Angle: {angles['GRIPPER']}")
    print("--------------------------------------------------")
    print(" [R] Relax/Release All Servos (Deactivates Hold)")
    print(" [E] Exit Debugger")
    print("="*50)

print("\n[!] Skipping automatic startup sweep to prevent power supply crashes.")
print("Servos will remain completely relaxed until you manually type a command.")

# Ensure the base is stopped right away
servos["BASE"].throttle = 0.0

try:
    while True:
        print_status()
        choice = input("Select an option (1-4, R, E): ").strip().upper()
        
        if choice == 'E':
            break
        elif choice == 'R':
            print("\nRelaxing all servos. You can now turn them by hand safely.")
            servos["BASE"].throttle = 0.0
            angles["BASE"] = "STOPPED"
            
            for name in ["SHOULDER", "ELBOW", "GRIPPER"]:
                servos[name].angle = None
                angles[name] = "OFF"
            time.sleep(1)
            
        elif choice == '1':
            print("\n[!] BASE is a 360 Continuous Servo.")
            direction = input("Direction (L for Left, R for Right): ").strip().upper()
            if direction not in ['L', 'R']:
                print("[!] Invalid direction. Use L or R.")
                continue
                
            try:
                duration = float(input("Time to rotate (in seconds, e.g., 0.5): ").strip())
                if duration <= 0:
                    print("[!] Time must be greater than 0.")
                    continue
                    
                print(f"Spinning base for {duration} seconds...")
                # 1.0 is full speed one way, -1.0 is full speed the other way
                if direction == 'L':
                    servos["BASE"].throttle = 1.0
                else:
                    servos["BASE"].throttle = -1.0
                
                angles["BASE"] = "SPINNING"
                time.sleep(duration)
                
                # Immediately apply the brakes
                servos["BASE"].throttle = 0.0
                angles["BASE"] = "STOPPED"
                print("Base stopped.")
                
            except ValueError:
                print("[!] Invalid time. Please enter a number like 1.5 or 0.2")
                
        elif choice in ['2', '3', '4']:
            joint_map = { '2': 'SHOULDER', '3': 'ELBOW', '4': 'GRIPPER' }
            joint_name = joint_map[choice]
            
            try:
                angle_input = input(f"Enter new angle for {joint_name} (0 to 180 degrees): ").strip()
                target_angle = int(angle_input)
                
                if 0 <= target_angle <= 180:
                    print(f"Moving {joint_name} to {target_angle}°...")
                    servos[joint_name].angle = target_angle
                    angles[joint_name] = f"{target_angle}°"
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
    servos["BASE"].throttle = 0.0
    for name in ["SHOULDER", "ELBOW", "GRIPPER"]:
        servos[name].angle = None
    pca.deinit()
    print("Hardware released safely.")