import BlynkLib
import time
import config
from sensors import proximity
from drivers import motors

blynk = BlynkLib.Blynk(config.BLYNK_AUTH, server='blynk.cloud', port=80)

# 2. Global State Variables (The Robot's Memory)
is_auto_mode = False
current_x = 0       # Stores Left/Right value
current_y = 0       # Stores Forward/Backward value
master_speed = 255  # The "Throttle" set by your Web Slider

# --- THE MOTOR MIXING ENGINE ---
# This is the "Math Room". It takes X and Y and decides how fast wheels spin.
def process_motors():
    global current_x, current_y, master_speed
    
    # Apply Deadzone: ignore tiny values so motors don't "hum" at rest
    x = current_x if abs(current_x) > 50 else 0
    y = current_y if abs(current_y) > 50 else 0
    
    # Differential Steering Math: Mixing X and Y
    left_raw = y + x
    right_raw = y - x
    
    # Clamp: Ensure we never send more than 255 to the motors
    left_clamped = max(min(left_raw, master_speed), -master_speed)
    right_clamped = max(min(right_raw, master_speed), -master_speed)
    
    # Calculation: Convert raw numbers to 0-100% for the terminal
    l_speed = round((abs(left_clamped) / 255) * 100, 1)
    r_speed = round((abs(right_clamped) / 255) * 100, 1)
    
    if left_clamped == 0 and right_clamped == 0:
        print("| IDLE: Motors Off |")
    else:
        l_dir = "FWD" if left_clamped > 0 else "REV"
        r_dir = "FWD" if right_clamped > 0 else "REV"
        print(f"MOTORS -> L: {l_speed}% ({l_dir}) | R: {r_speed}% ({r_dir})")

# --- BLYNK EVENT HANDLERS (The "Ears" of the robot) ---

def handle_master_speed(value):
    global master_speed
    master_speed = int(value[0])
    print(f"--- Throttle set to: {round((master_speed/255)*100)}% ---")

def handle_navigation_x(value):
    global current_x
    if not is_auto_mode:
        current_x = int(value[0])
        process_motors()

def handle_navigation_y(value):
    global current_y, master_speed
    if not is_auto_mode:
        # WEB BUTTON LOGIC: If value is 1 or -1, multiply by master_speed
        raw = int(value[0])
        if raw == 1 or raw == -1:
            current_y = raw * master_speed
        else:
            current_y = raw # Handles the phone joystick normally
        process_motors()

def handle_op_mode(value):
    global is_auto_mode, current_x, current_y
    # Toggle logic: 0 = AUTO, 1 = MANUAL (as we discussed)
    is_auto_mode = True if int(value[0]) == 0 else False
    
    if is_auto_mode:
        print("--- MODE: AUTO (Line Following Active) ---")
    else:
        current_x, current_y = 0, 0
        print("--- MODE: MANUAL (Remote Control Active) ---")
        process_motors()

# --- REGISTRATION ---
blynk.on("V1", handle_navigation_x) 
blynk.on("V5", handle_navigation_y) 
blynk.on("V2", handle_op_mode)      
blynk.on("V9", handle_master_speed) 

print("SYSTEM READY: Listening for commands...")

while True:
    blynk.run()
    if not proximity.is_path_clear():
        # Force a stop if something is in the way
        if current_y > 0 or is_auto_mode:
            print("!!! AUTO-BRAKE: Object detected by Ultrasonic !!!")
            motors.emergency_stop() 
            # Reset our memory so it doesn't try to move again immediately
            current_y = 0
    if is_auto_mode:
        time.sleep(0.1)
