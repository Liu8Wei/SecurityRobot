import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# Global variables
pca = None
arm = {}

def init():
    global pca, arm
    print("[SERVOS] Initializing Robotic Arm...")
    try:
        i2c_bus = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c_bus, address=0x41)
        pca.frequency = 50
        
        # Configure the 4 servos (Base has 360 range!)
        arm["BASE"]     = servo.Servo(pca.channels[0], min_pulse=500, max_pulse=2500, actuation_range=360)
        arm["SHOULDER"] = servo.Servo(pca.channels[8], min_pulse=500, max_pulse=2500)
        arm["ELBOW"]    = servo.Servo(pca.channels[12], min_pulse=500, max_pulse=2500)
        arm["GRIPPER"]  = servo.Servo(pca.channels[3], min_pulse=500, max_pulse=2500)
        
        print("[SERVOS] Arm Ready.")
    except Exception as e:
        print(f"[SERVOS] Error initializing arm: {e}")

def execute_pick():
    """ 
    This is called by main.py when you click 'Pick' on the dashboard.
    You will need to test_arm.py to find the exact angles and fill them in here!
    """
    print("[SERVOS] Running Pick Sequence...")
    if not arm: return
    
    # Example sequence (Replace these angles with your calibrated numbers)
    # arm["BASE"].angle = 180      # Center base
    # time.sleep(0.5)
    # arm["SHOULDER"].angle = 90   # Lower shoulder
    # time.sleep(0.5)
    # arm["GRIPPER"].angle = 120   # Close gripper
    # time.sleep(0.5)
    
    # Return to home
    # arm["SHOULDER"].angle = 150
    print("[SERVOS] Pick Sequence Complete.")

def cleanup():
    global pca
    if pca:
        for s in arm.values():
            s.angle = None # Relax servos
        pca.deinit()
