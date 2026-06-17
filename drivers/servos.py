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
        
        print("[SERVOS] Initialized. Arm is relaxed.")
    except Exception as e:
        print(f"[WARN] Servos disabled or not found: {e}")

def _slow_move(joint_name, start, end, delay=0.015):
    """Moves servos extremely slowly to prevent power crashes."""
    if joint_name not in joints: return
    s = joints[joint_name]
    step = 1 if start < end else -1
    for angle in range(start, end + step, step):
        s.angle = angle
        time.sleep(delay)

def execute_pick():
    """A highly controlled, safe pick-up routine."""
    print("[SERVOS] Executing safe pick routine...")
    try:
        # Move to safe start position first
        _slow_move("ELBOW", 90, 40)
        _slow_move("SHOULDER", 90, 110)
        
        # Action
        _slow_move("GRIPPER", 90, 60)   # Open claws
        _slow_move("SHOULDER", 110, 80) # Reach forward
        _slow_move("GRIPPER", 60, 120)  # Close claws
        time.sleep(0.5)
        _slow_move("SHOULDER", 80, 110) # Lift up and tuck in
        
        print("[SERVOS] Pick complete.")
    except Exception as e:
        print(f"[SERVOS] Sequence error: {e}")

def cleanup():
    global pca
    if pca:
        for s in joints.values():
            s.angle = None  # Relax all motors
        pca.deinit()
