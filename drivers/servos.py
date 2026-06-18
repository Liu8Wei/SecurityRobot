import time
import threading
import pigpio
import cv2
import numpy as np
import sys

# --- 1. Import Your Modules ---
try:
    import config
    from drivers import motors
    from drivers import servos
    import dashboard
except ImportError as e:
    sys.exit(f"[FATAL] Missing a file! Check your folder structure. Error: {e}")

# --- 2. System Boot & Hardware Init ---
print("========================================")
print("       PATROLBOT CORE INITIALIZING      ")
print("========================================")

pi = pigpio.pi()
if not pi.connected:
    sys.exit("[FATAL] pigpio daemon not running. Run: sudo pigpiod")

# Init Drive Motors & Arm Servos
motors.init()
servos.init()

# Setup Ultrasonic Pins
pi.set_mode(config.TRIG_PIN, pigpio.OUTPUT)
pi.set_mode(config.ECHO_PIN, pigpio.INPUT)
pi.write(config.TRIG_PIN, 0)

# Setup IR Line Sensor Pins
IR_PINS = [config.IR_SENSOR_1, config.IR_SENSOR_2, config.IR_SENSOR_3, config.IR_SENSOR_4, config.IR_SENSOR_5]
for pin in IR_PINS:
    pi.set_mode(pin, pigpio.INPUT)

# --- 3. Optional Hardware (INA & Camera) ---
ina219 = None
try:
    import board, busio
    from adafruit_ina219 import INA219
    ina219 = INA219(busio.I2C(board.SCL, board.SDA), addr=config.INA219_ADDRESS)
    print("[SYSTEM] INA219 Power Monitor: Connected")
except Exception as e: 
    print(f"[WARN] INA219 Power Monitor not found: {e}")

camera = None
try:
    from picamera2 import Picamera2
    camera = Picamera2()
    camera.configure(camera.create_preview_configuration(main={"size": (320, 240)}))
    camera.start()
    print("[SYSTEM] Camera Feed: Connected")
except Exception as e: 
    print(f"[WARN] Camera not found: {e}")

# --- 4. Start Web Dashboard ---
print("[SYSTEM] Starting Web Dashboard...")
threading.Thread(target=lambda: dashboard.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()
time.sleep(2)
print(f"\n>>> DASHBOARD LIVE AT: http://{dashboard.PI_IP}:5000 <<<")

# --- 5. Ultrasonic Helper Function ---
def read_ultrasonic():
    """Reads distance without blocking the camera thread"""
    pi.gpio_trigger(config.TRIG_PIN, 10, 1)
    timeout = pi.get_current_tick()
    
    # Wait for echo to go high (Timeout safely)
    while pi.read(config.ECHO_PIN) == 0:
        if pigpio.tickDiff(timeout, pi.get_current_tick()) > 30000: 
            return dashboard.state["distance"]
            
    start_tick = pi.get_current_tick()
    
    # Wait for echo to go low
    while pi.read(config.ECHO_PIN) == 1:
        end_tick = pi.get_current_tick()
        if pigpio.tickDiff(start_tick, end_tick) > 30000: 
            return dashboard.state["distance"]
    
    # Calculate distance
    dist = (pigpio.tickDiff(start_tick, end_tick) / 1000000.0) * 17150
    if 2.0 <= dist <= 400.0:
        return round(dist, 1) 
    return dashboard.state["distance"]

# --- 6. Vision Processing Logic ---
def process_vision(frame):
    """
    Analyzes the camera frame to detect the 4 stations:
    Black Cube, White Cube, Pentagon Pattern A, Pentagon Pattern B
    """
    if frame is None:
        return "NO SIGNAL", None

    # Convert to HSV for color checking, Gray for shape detection
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Blur and detect edges
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # Connect broken edges
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    result_frame = frame.copy()
    status = "Scanning for targets..."

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 500: # Ignore tiny noise
            continue

        # Approximate the polygon to count corners
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        sides = len(approx)

        # Check if it has 4 sides (Cube) or 5 sides (Pentagon)
        if sides in [4, 5]:
            x, y, w, h = cv2.boundingRect(approx)
            cx, cy = x + w // 2, y + h // 2
            
            # Boundary check
            if cy >= frame.shape[0] or cx >= frame.shape[1]:
                continue

            # Sample the center pixel in HSV to determine Black vs White
            h_val, s_val, v_val = hsv[cy, cx]

            shape_name = ""
            if sides == 4:
                # Check if it's roughly a square (Cube)
                aspect_ratio = float(w) / h
                if 0.75 <= aspect_ratio <= 1.3:
                    if v_val < 80:
                        shape_name = "Black Cube"
                    elif v_val > 150 and s_val < 60:
                        shape_name = "White Cube"
            elif sides == 5:
                # Pentagon
                if v_val < 100:
                    shape_name = "Pentagon Pattern A (Dark)"
                else:
                    shape_name = "Pentagon Pattern B (Light)"

            if shape_name:
                status = f"VISION LOCK: {shape_name}"
                # Draw the bounding box and text
                cv2.drawContours(result_frame, [approx], -1, (0, 255, 0), 3)
                cv2.putText(result_frame, shape_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.circle(result_frame, (cx, cy), 5, (0, 0, 255), -1)
                break # Stop looking after finding the first valid target

    return status, result_frame

# --- 7. MAIN CONTROL LOOP ---
dashboard.state["nav_status"] = "Ready"
try:
    while True:
        # A. Vision Processing (Pushes frame to Dashboard)
        if camera:
            try:
                buf = cv2.cvtColor(camera.capture_array(), cv2.COLOR_RGB2BGR)
                v_status, out_frame = process_vision(buf)
                dashboard.state["vision_status"] = v_status
                dashboard.set_frame(out_frame)
            except: 
                pass

        # B. Update Sensor Data on Dashboard
        dist = read_ultrasonic()
        dashboard.state["distance"] = dist
        
        ir_readings = [pi.read(p) for p in IR_PINS]
        dashboard.state["ir_array"] = str(ir_readings)
        
        if ina219:
            dashboard.state["bus_voltage"] = round(ina219.bus_voltage, 2)
            dashboard.state["current_mA"] = round(ina219.current, 1)

        # C. Command Execution (from Dashboard Buttons)
        cmd = dashboard.state["command"]
        
        if cmd == "pick":
            dashboard.state["nav_status"] = "Executing Pick Routine..."
            motors.stop() # Stop driving while picking
            servos.execute_pick()
            dashboard.state["command"] = None # Clear command when done

        # D. Navigation & Driving Logic
        if dashboard.state["mode"] == "Manual Override":
            if cmd == "forward": 
                motors.forward(180)
                dashboard.state["nav_status"] = "Moving Forward"
            elif cmd == "reverse": 
                motors.reverse(180)
                dashboard.state["nav_status"] = "Reversing"
            elif cmd == "left": 
                motors.turn_left(160)
                dashboard.state["nav_status"] = "Turning Left"
            elif cmd == "right": 
                motors.turn_right(160)
                dashboard.state["nav_status"] = "Turning Right"
            elif cmd == "stop": 
                motors.stop()
                dashboard.state["nav_status"] = "Idle"
            
            # Clear movement commands immediately so it keeps driving until stop is pressed
            if cmd in ["forward", "reverse", "left", "right"]: 
                dashboard.state["command"] = None
            
        elif dashboard.state["mode"] == "Autonomous":
            # PROXIMITY STOP (Safety Override)
            if dist > 0 and dist < config.STOP_DISTANCE_CM:
                motors.stop()
                dashboard.state["nav_status"] = f"OBSTACLE ({dist}cm) - STOPPED"
            else:
                # --- FLOOR PATTERN / SHAPE DETECTION ---
                # Treating the 5 IR sensors like a barcode reader for floor markers
                if ir_readings == [1, 1, 1, 1, 1]:
                    motors.stop()
                    dashboard.state["nav_status"] = "MARKER DETECTED: Black Cube"
                elif ir_readings == [0, 0, 0, 0, 0]:
                    motors.stop()
                    dashboard.state["nav_status"] = "MARKER DETECTED: White Cube / End"
                elif ir_readings == [1, 0, 1, 0, 1]:
                    motors.stop()
                    dashboard.state["nav_status"] = "MARKER DETECTED: Pentagon Pattern A"
                elif ir_readings == [0, 1, 1, 1, 0]:
                    motors.stop()
                    dashboard.state["nav_status"] = "MARKER DETECTED: Pentagon Pattern B"
                else:
                    # --- NORMAL LINE FOLLOWING ---
                    dashboard.state["nav_status"] = "Line Following"
                    # IR LINE FOLLOWING [FarL, MidL, Center, MidR, FarR]
                    if ir_readings[2] == 1: 
                        motors.forward(140)
                    elif ir_readings[1] == 1: 
                        motors.turn_left(150)
                    elif ir_readings[3] == 1: 
                        motors.turn_right(150)
                    elif ir_readings[0] == 1: 
                        motors.turn_left(180)
                    elif ir_readings[4] == 1: 
                        motors.turn_right(180)
                    else: 
                        motors.stop() # Stop if line is lost

        # Loop runs 20 times a second
        time.sleep(0.05)

except KeyboardInterrupt: 
    print("\n[SYSTEM] Shutting down cleanly...")
finally:
    motors.cleanup()
    servos.cleanup()
    pi.stop()
    if camera: 
        camera.stop()
    print("[SYSTEM] Safely powered down. Good luck!")
    sys.exit(0)
