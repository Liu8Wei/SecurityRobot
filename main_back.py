import time
import threading
import pigpio
import cv2
import sys
import board
import busio

# --- 1. Import Your Modules ---
try:
    import config
    from drivers import motors
    from drivers import servos
    import dashboard
    try:
        from sensors import vision
    except ImportError:
        import vision
except ImportError as e:
    exit(f"[FATAL] Missing a file! Check your folder structure. Error: {e}")

# --- 2. System Boot & Hardware Init ---
print("========================================")
print("       PATROLBOT CORE INITIALIZING      ")
print("========================================")

# -> I2C Auto-Scan
try:
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    while not i2c_bus.try_lock(): pass
    found_addrs = i2c_bus.scan()
    i2c_bus.unlock()
    if 0x41 in found_addrs: config.PCA_ADDRESS = 0x41
    elif 0x40 in found_addrs: config.PCA_ADDRESS = 0x40
except Exception as e:
    print(f"[WARN] I2C Scan failed: {e}")

pi = pigpio.pi()
if not pi.connected: exit("[FATAL] pigpiod not running.")

motors.init()
servos.init()

pi.set_mode(config.TRIG_PIN, pigpio.OUTPUT)
pi.set_mode(config.ECHO_PIN, pigpio.INPUT)
pi.write(config.TRIG_PIN, 0)

IR_PINS = [config.IR_SENSOR_1, config.IR_SENSOR_2, config.IR_SENSOR_3, config.IR_SENSOR_4, config.IR_SENSOR_5]
for pin in IR_PINS:
    pi.set_mode(pin, pigpio.INPUT)
    pi.set_pull_up_down(pin, pigpio.PUD_UP) # Force internal pull-up

# --- 3. Camera & Dashboard ---
camera = None
try:
    from picamera2 import Picamera2
    camera = Picamera2()
    config_cam = camera.create_preview_configuration(main={"size": (320, 240)})
    camera.configure(config_cam)
    camera.start()
except: print("[WARN] Camera failed.")

threading.Thread(target=lambda: dashboard.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

# --- 4. Main Loop ---
dashboard.state["nav_status"] = "Idle"
try:
    while True:
        # A. Vision
        if camera:
            try:
                frame = cv2.flip(cv2.cvtColor(camera.capture_array(), cv2.COLOR_RGB2BGR), -1)
                if hasattr(vision, 'process_frame'):
                    v_status, frame = vision.process_frame(frame)
                    dashboard.state["vision_status"] = v_status
                dashboard.set_frame(frame)
            except: pass

        # B. Sensors
        ir_readings = [1 - pi.read(p) for p in IR_PINS] # Inverted if sensor triggers low
        dashboard.state["ir_array"] = str(ir_readings)

        # C. Command Processing
        cmd = dashboard.state.get("command")
        current_mode = dashboard.state.get("mode")

        if cmd:
            print(f"[DEBUG] Executing Command: {cmd}")
            if cmd == "pick":
                threading.Thread(target=servos.execute_pick, args=(None,), daemon=True).start()
            elif cmd == "stop": motors.stop()
            elif cmd == "forward": motors.forward()
            elif cmd == "reverse": motors.reverse()
            elif cmd == "left": motors.turn_left()
            elif cmd == "right": motors.turn_right()
            dashboard.state["command"] = None # Clear command after execution

        # D. Auto Logic
        if current_mode == "Autonomous":
            if sum(ir_readings) == 5: motors.stop() # Marker
            elif ir_readings[2] == 1: motors.forward()
            elif ir_readings[1] == 1: motors.turn_left()
            elif ir_readings[3] == 1: motors.turn_right()
            else: motors.stop()

        time.sleep(0.05)
except KeyboardInterrupt:
    motors.cleanup()
    pi.stop()