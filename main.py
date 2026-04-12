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
is_recording = False
is_lockdown = False

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

# --- SECURITY HANDLERS ---

def handle_snapshot(value):
    if int(value[0]) == 1:
        timestamp = time.strftime("%H:%M:%S")
        filename = f"snap_{timestamp}.jpg"
        
        # 1. Update the EXISTING V6 System Status
        log_msg = f"📸 [{timestamp}] SNAPSHOT SAVED"
        blynk.virtual_write("V6", log_msg)
        print(f"Log sent to V6: {log_msg}")
        img_url = "https://placehold.co/600x400?text=Intruder+Captured" # Test URL
        blynk.virtual_write("V11", 1, img_url)
        print("Gallery updated at index 1")

       
def handle_recording(value):
    global is_recording
    is_recording = True if int(value[0]) == 1 else False
    
    timestamp = time.strftime("%H:%M:%S")
    status_text = "📹 RECORDING: ON" if is_recording else "📹 RECORDING: OFF"
    print(status_text)
    # Update the EXISTING V6 System Status
    blynk.virtual_write("V6", status_text)
    print(f"Log sent to V6: {status_text}")

def update_battery():
    # Simulated Battery Math: Read voltage from ADC
    # V_max = 12.6V, V_min = 9.0V
    current_voltage = 11.8 # This would come from your ADC sensor
    percentage = round(((current_voltage - 9.0) / (12.6 - 9.0)) * 100)
    blynk.virtual_write("V4", percentage)
    
    # Critical Alert if battery is low
    if percentage < 20:
        blynk.log_event("low_battery_alert", f"Robot needs charging! {percentage}%")

def handle_alarm_mode(value):
    global is_lockdown, current_x, current_y
    
    # Toggle Logic: 1 = Alarm Triggered, 0 = False Alarm/All Clear
    if int(value[0]) == 1:
        is_lockdown = True
        print("🚨 LOCKDOWN: Starting Evidence Collection...")
        
        # 1. Stop Motors immediately for clear photos
        current_x, current_y = 0, 0
        # motors.emergency_stop() 
        blynk.virtual_write("V10", 255)
        
        # 2. Update Status Log
        timestamp = time.strftime("%H:%M:%S")
        blynk.virtual_write("V6", f"🚨 [{timestamp}] ALARM: Investigating...")
        
        # 3. Trigger Evidence (Call your functions)
        handle_snapshot([1]) # Manually trigger snapshot
        # handle_recording([1]) # Start recording
        
    else:
        is_lockdown = False
        print("🛡️ RESET: Returning to normal operation.")
        blynk.virtual_write("V6", f"✅ [{time.strftime('%H:%M:%S')}] ALL CLEAR")
        # handle_recording([0]) # Stop recording
        blynk.virtual_write("V10", 0) # Turn off alert LED

# --- REGISTRATION ---
blynk.on("V1", handle_navigation_x) 
blynk.on("V5", handle_navigation_y) 
blynk.on("V2", handle_op_mode)      
blynk.on("V9", handle_master_speed) 
blynk.on("V7", handle_snapshot)  # Push button for Snapshot
blynk.on("V8", handle_recording) # Switch for Recording
blynk.on("V3", handle_alarm_mode)

print("SYSTEM READY: Listening for commands...")

while True:
    blynk.run()
   # Get the status from the sensor file
    current_status = proximity.get_status()
    
    if current_status == "DANGER":
        blynk.virtual_write("V10", 255) # Red LED ON
        if is_auto_mode:
            motors.emergency_stop()
            # logic for Telegram goes here
            
    elif current_status == "WARNING":
        blynk.virtual_write("V10", 255) # Warning LED ON
        # In Manual Mode, we do nothing else (allows the "Chase")
        
    else:
        blynk.virtual_write("V10", 0) # Path clear, LED OFF

    if is_auto_mode:
        time.sleep(0.1)

    if is_lockdown:
        # Optional: Add code here to rotate the robot 
        # or sweep the sensors for better PIR coverage
        pass
  