import time
import config
from sensors import proximity
from drivers import motors
from sensors import vision
#from blynklib import Blynk
import BlynkLib
import cv2
import subprocess 

blynk = BlynkLib.Blynk(config.BLYNK_AUTH)

# 2. Global State Variables (The Robot's Memory)
is_auto_mode = True
mission_active = False
current_x = 0       # Stores Left/Right value
current_y = 0       # Stores Forward/Backward value
master_speed = 255  # The "Throttle" set by your Web Slider

@blynk.on("connected")
def blynk_connected():
    """Forces a Clean Boot: Resets Python logic AND the phone screen."""
    global is_auto_mode, mission_active
    
    # 1. Reset the Python variables to your desired defaults
    is_auto_mode = True 
    mission_active = False
    
    # 2. Force the phone app to visually match our defaults
    # V2 is your Auto/Manual button (assuming 1 is Auto, 0 is Manual)
    blynk.virtual_write(2, 1) 
    
    # V8 is your new Start/Pause button
    blynk.virtual_write(8, 0) 
    
    print("SYS: Connected to Blynk Cloud. Clean Boot initialized. Defaults set.")

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

@blynk.on("V9")
def handle_master_speed(value):
    global master_speed
    master_speed = int(value[0])
    print(f"--- Throttle set to: {round((master_speed/255)*100)}% ---")

# @blynk.on("V1")
# def handle_navigation_x(value):
#     global current_x, mission_active
#     if not mission_active:
#         return
#     if not is_auto_mode:
#         current_x = int(value[0])
#         process_motors()

# @blynk.on("V5")
# def handle_navigation_y(value):
#     global current_y, master_speed, mission_active
#     if not mission_active:
#         return
#     if not is_auto_mode:
#         # WEB BUTTON LOGIC: If value is 1 or -1, multiply by master_speed
#         raw = int(value[0])
#         if raw == 1 or raw == -1:
#             current_y = raw * master_speed
#         else:
#             current_y = raw # Handles the phone joystick normally
#         process_motors()
@blynk.on("V1")
def handle_navigation_x(value):
    global current_x
    
    # If we are in Auto mode, ignore the joystick so it doesn't fight the camera
    if is_auto_mode:
        return
        
    current_x = int(value[0])
    process_motors()

@blynk.on("V5")
def handle_navigation_y(value):
    global current_y, master_speed
    
    # If we are in Auto mode, ignore the joystick
    if is_auto_mode:
        return
        
    # WEB BUTTON LOGIC: If value is 1 or -1, multiply by master_speed
    raw = int(value[0])
    if raw == 1 or raw == -1:
        current_y = raw * master_speed
    else:
        current_y = raw # Handles the phone joystick normally
        
    process_motors()

@blynk.on("V2")
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
    """Bypasses OpenCV memory limits by using the proven rpicam command."""
    subprocess.run(
        ["rpicam-jpeg", "-o", "temp.jpg", "--width", "320", "--height", "240", "--nopreview", "-t", "1"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    # OpenCV reads the photo from the folder
    return cv2.imread("temp.jpg")

def run_mission_test():
    global mission_active

    print("-" * 30)
    print("ROBOT SYSTEM: STANDBY. Waiting for GUI 'Start' signal...")
    print("-" * 30)

    while True:
        # We must call blynk.run() constantly inside the while loop
        # so the Pi never stops listening to your phone.
        blynk.run() 

        # Only scan if the operator pressed 'Start' (V8)
        if mission_active:
            frame = capture_pi_frame() 
            
            if frame is None:
                continue # Skip and try again if camera lags
            
            shape = vision.identify_shape(frame)
            cx = vision.get_centroid(frame)
            
            if cx:
                print(f"\n[ALERT] Target Acquired! {shape} at X={cx}")
                vision.draw_debug_info(frame, cx, shape)
                
                # --- TURRET AIMING ---
                print("TURRET: Aligning to object...")
                while abs(cx - TARGET_X) > TOLERANCE:
                    blynk.run() # Keep listening during movement!
                    
                    if not mission_active: 
                        print("\nGUI: E-STOP TRIGGERED. Aborting Turn!")
                        break # Immediately stops turning if you hit pause
                        
                    frame = capture_pi_frame() 
                    cx = vision.get_centroid(frame)
                    
                    if cx:
                        print(f"TURRET: Current X={cx} | Error={cx - TARGET_X}", end="\r")
                    else:
                        print("\nWARNING: Target lost!")
                        break 
                
                if cx and abs(cx - TARGET_X) <= TOLERANCE:
                    print("\nTURRET: Centroid Locked. Target Centered.")
                    print("DECISION: Starting Arm Sequence.")
                    # servos.execute_pick()
                    
                    # Optional: Auto-pause the mission after a successful grab
                    # so it doesn't instantly start grabbing again.
                   
                    mission_active = False
                    blynk.virtual_write(8, 0) # Flip the switch on your phone to 'Off'

        else:
            # If the mission is paused, just chill out.
            time.sleep(0.1)

@blynk.on("V8")
def toggle_mission(value):
    """The Mission Control Switch for Active Scanning."""
    global mission_active
    
    if int(value[0]) == 1:
        mission_active = True
        print("GUI: Mission STARTED by operator. Active Scan Engaged.")
    else:
        mission_active = False
        print("GUI: Mission PAUSED by operator. Turret holding.")

# --- REGISTRATION ---
#blynk.on("V1", handle_navigation_x) 
#blynk.on("V5", handle_navigation_y) 
#blynk.on("V2", handle_op_mode)      
#blynk.on("V9", handle_master_speed) 

print("SYSTEM READY: Listening for commands...")

#while True:
    #blynk.run()

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

  #  time.sleep(0.05)

if __name__ == "__main__":
    print("SYSTEM READY: Booting Mission Protocol...")
    run_mission_test()