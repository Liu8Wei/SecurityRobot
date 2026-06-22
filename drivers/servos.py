import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import config

pca = None
joints = {}

def init():
    global pca, joints
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c, address=config.PCA_ADDRESS)
        pca.frequency = 50
        
        joints["BASE"] = servo.Servo(pca.channels[config.SERVO_BASE], min_pulse=config.SERVO_MIN_US, max_pulse=config.SERVO_MAX_US)
        joints["SHOULDER"] = servo.Servo(pca.channels[config.SERVO_SHOULDER], min_pulse=config.SERVO_MIN_US, max_pulse=config.SERVO_MAX_US)
        joints["ELBOW"] = servo.Servo(pca.channels[config.SERVO_ELBOW], min_pulse=config.SERVO_MIN_US, max_pulse=config.SERVO_MAX_US)
        joints["GRIPPER"] = servo.Servo(pca.channels[config.SERVO_GRIPPER], min_pulse=config.SERVO_MIN_US, max_pulse=config.SERVO_MAX_US)
        
        print("[SERVOS] Initialized with updated angles.")
    except Exception as e:
        print(f"[WARN] Servos disabled or not found: {e}")

def execute_pick(shape_target="Cube"):
    """New calibrated sequence based on your exact specs"""
    print(f"[SERVOS] Executing safe pick routine for {shape_target}...")
    if not pca: return
    
    try:
        # 1. Open Gripper
        joints["GRIPPER"].angle = 60
        time.sleep(0.3)
        
        # 2. Platform Rotation (Left or Right depending on shape)
        if "Pentagon" in shape_target:
            joints["BASE"].angle = 120 # Turn Left for Pentagon
        else:
            joints["BASE"].angle = 60  # Turn Right for Cube
        time.sleep(0.2)
        
        # 3. Reach Out and Down
        joints["ELBOW"].angle = 0     # Front
        time.sleep(0.2)
        joints["SHOULDER"].angle = 20 # DOWN (Updated to 20)
        time.sleep(0.5)
        
        # 4. Grip Object
        joints["GRIPPER"].angle = 37  # GRIP (Updated to 37)
        time.sleep(0.5)
        
        # 5. Lift and Retract
        joints["SHOULDER"].angle = 45 # STRAIGHT/UP (Updated to 45)
        time.sleep(0.2)
        joints["ELBOW"].angle = 180   # Back
        time.sleep(0.5)
        
        # 6. Reset Base to Center
        joints["BASE"].angle = 90
        time.sleep(0.3)
        
        print("[SERVOS] Pick complete.")
    except Exception as e:
        print(f"[SERVOS] Sequence error: {e}")

def cleanup():
    global pca
    if pca:
        for s in joints.values():
            s.angle = None
        pca.deinit()