import time
import config
from sensors import proximity
from drivers import motors
from sensors import vision
from blynklib import Blynk
import cv2
import subprocess 

blynk = Blynk(config.BLYNK_AUTH, server='blynk.cloud', port=80)

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

@blynk.handle_event('write V9')
def handle_master_speed(value):
    global master_speed
    master_speed = int(value[0])
    print(f"--- Throttle set to: {round((master_speed/255)*100)}% ---")

@blynk.handle_event('write V1')
def handle_navigation_x(value):
    global current_x
    if not is_auto_mode:
        current_x = int(value[0])
        process_motors()

@blynk.handle_event('write V5')
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

@blynk.handle_event('write V2')
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


def update_battery():
    # Simulated Battery Math: Read voltage from ADC
    # V_max = 12.6V, V_min = 9.0V
    current_voltage = 11.8 # This would come from your ADC sensor
    percentage = round(((current_voltage - 9.0) / (12.6 - 9.0)) * 100)
    blynk.virtual_write("V4", percentage)
    
    # Critical Alert if battery is low
    if percentage < 20:
        blynk.log_event("low_battery_alert", f"Robot needs charging! {percentage}%")


def update_log(message):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}\n"
    
    # This sends the text TO the phone
    blynk.virtual_write("V6", formatted_msg)
    print(f"Log: {formatted_msg}")

def capture_pi_frame():
    """Bypasses OpenCV memory limits by using the native Pi camera command."""
    # Takes a fast, low-res photo and saves it quietly
    subprocess.run(
        ["libcamera-jpeg", "-o", "temp.jpg", "--width", "320", "--height", "240", "--nopreview", "-t", "1"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    # OpenCV reads the photo from the folder
    return cv2.imread("temp.jpg")

def run_mission_test():
    print("-" * 30)
    print("ROBOT SYSTEM: STANDBY")
    print("-" * 30)

    # 1. Capture what the robot sees
    frame = capture_pi_frame()
    
    if frame is None:
        print("ERROR: Camera is unplugged or failed to turn on!")
        return # This stops the test immediately so it doesn't crash
    
    # 2. Vision Identification
    shape = vision.identify_shape(frame)
    cx = vision.get_centroid(frame)
    
    # PRINT TO GUI TERMINAL
    print(f"STATUS: Station Reached")
    print(f"VISION: Shape Identified as [{shape}]")
    
    # --- LEVEL 1 (4 spaces): This belongs to the function ---
    if cx:
        # --- LEVEL 2 (8 spaces): This belongs to the 'if' ---
        print(f"VISION: Object Centroid found at X={cx}")
        
        # 3. Platform Alignment (Aiming)
        print("TURRET: Aligning to object...")
        
        while abs(cx - TARGET_X) > TOLERANCE:
            # --- LEVEL 3 (12 spaces): This belongs to the 'while' loop ---
            cx = vision.get_centroid(camera.get_frame())
            print(f"TURRET: Current X={cx} | Error={cx - TARGET_X}")
        
        # Back to LEVEL 2 (8 spaces) because the while loop is done
        print("TURRET: Centroid Locked.")

        # 4. EXECUTE PICK
        print("DECISION: Alignment confirmed. Starting Arm Sequence.")
        # servos.execute_pick()
        
    # --- LEVEL 1 (4 spaces): This lines up perfectly with 'if cx:' ---
    else:
        # --- LEVEL 2 (8 spaces): This belongs to the 'else' ---
        print("ERROR: Target lost from view!")

if __name__ == "__main__":
    run_mission_test()

# --- REGISTRATION ---
#blynk.on("V1", handle_navigation_x) 
#blynk.on("V5", handle_navigation_y) 
#blynk.on("V2", handle_op_mode)      
#blynk.on("V9", handle_master_speed) 

print("SYSTEM READY: Listening for commands...")

while True:
    blynk.run()

    # # STEP 6: SAFETY CHECK (Continuous)
    # if proximity.is_blocked(threshold=15):
    #     motors.stop()
    #     print("Obstacle Detected - Safety Halt")
    #     continue 

    # if current_state == "DRIVE":
    #     # Follow line... 
    #     pass

    # elif current_state == "ROTATE":
    #     # Get live distance for fine-tuning if needed
    #     current_dist = proximity.get_distance()
    #     # ... (Camera alignment logic) ...
    #     pass
        
    # elif current_state == "PICK":
    #     # Execute arm sequence using drivers/servos.py
    #     pass

    time.sleep(0.05)