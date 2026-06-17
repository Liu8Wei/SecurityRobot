import time
import threading
import socket
import config
import pigpio
import shared_state as robot
from sensors import proximity
from drivers import motors
from sensors import vision
from adafruit_servokit import ServoKit
import cv2
import subprocess

# =============================================================================
# PCA9685 SERVO CHANNELS
# CH0=Shoulder CH3=Gripper CH4=Base(rotation) CH15=Elbow
# Base is continuous rotation - stop angle = 95
# =============================================================================
_kit = ServoKit(channels=16)
CH_BASE     = 4
CH_SHOULDER = 0
CH_ELBOW    = 15
CH_GRIPPER  = 3
BASE_STOP   = 95

for ch in [CH_BASE, CH_SHOULDER, CH_ELBOW, CH_GRIPPER]:
    _kit.servo[ch].set_pulse_width_range(500, 2500)

# =============================================================================
# BLYNK - runs in main loop (threading causes handler issues with BlynkLib)
# =============================================================================
socket.setdefaulttimeout(5)
BLYNK_AVAILABLE = False
blynk = None
try:
    import BlynkLib
    blynk = BlynkLib.Blynk(config.BLYNK_AUTH)
    BLYNK_AVAILABLE = True
    print("[BLYNK] Connected OK")
except Exception as e:
    print("[WARN] Blynk unavailable: " + str(e))
    print("[INFO] Running on Flask dashboard only.")

def blynk_write(pin, value):
    if BLYNK_AVAILABLE and blynk:
        try:
            blynk.virtual_write(pin, value)
        except:
            pass

# =============================================================================
# INA219
# =============================================================================
try:
    from ina219 import INA219
    _ina = INA219(shunt_ohms=0.1, address=config.INA219_ADDRESS)
    _ina.configure()
    INA219_AVAILABLE = True
    print("[INA219] Connected OK")
except Exception as e:
    print("[WARN] INA219 not available: " + str(e))
    INA219_AVAILABLE = False

# =============================================================================
# PIGPIO (motors and IR sensors only)
# =============================================================================
_pi = pigpio.pi()
if not _pi.connected:
    raise RuntimeError("pigpio not running. Run: sudo pigpiod")

# =============================================================================
# GLOBAL STATE
# =============================================================================
is_auto_mode   = True
mission_active = False
current_x      = 0
current_y      = 0
master_speed   = 200

# =============================================================================
# LOG
# =============================================================================
def log(message):
    ts = time.strftime("%H:%M:%S")
    line = "[" + ts + "] " + str(message)
    print("LOG: " + line, flush=True)
    blynk_write(config.V_LOG, line + "\n")

# =============================================================================
# DASHBOARD BRIDGE
# =============================================================================
def push_to_dashboard():
    robot.state["nav_status"] = "Moving" if mission_active else "Idle"
    robot.state["ir_array"]   = str(read_ir_sensors())
    robot.state["mode"]       = "Autonomous" if is_auto_mode else "Manual Override"
    if INA219_AVAILABLE:
        try:
            robot.state["bus_voltage"] = round(_ina.voltage(), 1)
            robot.state["current_mA"]  = round(_ina.current(), 0)
        except:
            pass
    else:
        robot.state["bus_voltage"] = 11.8
        robot.state["current_mA"]  = 0

def handle_dashboard_commands():
    global is_auto_mode, mission_active
    cmd = robot.state.get("command")
    if cmd is None:
        return
    robot.state["command"] = None
    if   cmd == "forward":     motors.forward(master_speed)
    elif cmd == "reverse":     motors.reverse(master_speed)
    elif cmd == "left":        motors.turn_left(master_speed)
    elif cmd == "right":       motors.turn_right(master_speed)
    elif cmd == "stop":        motors.stop()
    elif cmd == "mode_auto":
        is_auto_mode = True
        log("MODE: AUTO (dashboard)")
    elif cmd == "mode_manual":
        is_auto_mode = False
        motors.stop()
        log("MODE: MANUAL (dashboard)")
    elif cmd == "pick":
        execute_pick_sequence()

# =============================================================================
# SERVO via PCA9685
# Shoulder: reversed (135=down, 45=up)
# Elbow: reversed (60=extend, 90=home)
# Base: continuous rotation (95=stop, <95=CW, >95=CCW)
# =============================================================================
def servo_move(ch, angle):
    angle = max(0, min(180, angle))
    _kit.servo[ch].angle = angle
    names = {CH_BASE: "BASE", CH_SHOULDER: "SHOULDER", CH_ELBOW: "ELBOW", CH_GRIPPER: "GRIPPER"}
    print("SERVO: CH" + str(ch) + "(" + names.get(ch, "?") + ") -> " + str(angle) + "deg", flush=True)

def servo_home():
    servo_move(CH_BASE,     BASE_STOP)
    servo_move(CH_SHOULDER, 90)
    servo_move(CH_ELBOW,    90)
    servo_move(CH_GRIPPER,  90)
    log("SERVO: All HOME")

def servo_stop_all():
    for ch in [CH_SHOULDER, CH_ELBOW, CH_GRIPPER]:
        try:
            _kit.servo[ch].angle = 90
        except:
            pass
    try:
        _kit.servo[CH_BASE].angle = BASE_STOP
    except:
        pass

def execute_pick_sequence():
    robot.state["arm_status"] = "Executing..."
    log("ARM: Pick sequence start")
    # Rotate base to face target
    servo_move(CH_BASE, 45);      time.sleep(0.8)
    servo_move(CH_BASE, BASE_STOP); time.sleep(0.5)
    # Lower shoulder to reach
    servo_move(CH_SHOULDER, 135); time.sleep(1.0)
    # Extend elbow
    servo_move(CH_ELBOW, 60);     time.sleep(1.0)
    # Close gripper to grab
    servo_move(CH_GRIPPER, 30);   time.sleep(0.8)
    # Lift shoulder up
    servo_move(CH_SHOULDER, 90);  time.sleep(1.0)
    # Rotate base to drop zone
    servo_move(CH_BASE, 135);     time.sleep(0.8)
    servo_move(CH_BASE, BASE_STOP); time.sleep(0.5)
    # Open gripper to release
    servo_move(CH_GRIPPER, 90);   time.sleep(0.8)
    # Return all to home
    servo_move(CH_BASE, BASE_STOP); time.sleep(0.3)
    servo_move(CH_SHOULDER, 90); time.sleep(1.0)
    servo_move(CH_ELBOW, 90);    time.sleep(1.0)
    robot.state["arm_status"] = "Stowed"
    log("ARM: Pick complete")

# =============================================================================
# IR SENSORS
# =============================================================================
IR_PINS = [
    config.IR_SENSOR_1,
    config.IR_SENSOR_2,
    config.IR_SENSOR_3,
    config.IR_SENSOR_4,
    config.IR_SENSOR_5,
]

def ir_setup():
    for pin in IR_PINS:
        _pi.set_mode(pin, pigpio.INPUT)
    print("[IR] Initialized on GPIO: " + str(IR_PINS), flush=True)

def read_ir_sensors():
    return [_pi.read(pin) for pin in IR_PINS]

# =============================================================================
# SENSOR UPDATE
# =============================================================================
def update_sensors():
    readings = []
    for _ in range(3):
        d = proximity.get_distance()
        if 0 < d < 400:
            readings.append(d)
        time.sleep(0.01)
    distance = round(sum(readings) / len(readings), 1) if readings else 999.0
    blynk_write(config.V_ULTRASONIC_CM, distance)
    robot.state["distance"] = distance
    ir_vals = read_ir_sensors()
    labels  = ["FL", "NL", "C ", "NR", "FR"]
    ir_str  = "  ".join(labels[i] + "=" + ("BLK" if v == 0 else "WHT") for i, v in enumerate(ir_vals))
    robot.state["ir_array"] = str(ir_vals)
    print("SENSOR [" + time.strftime("%H:%M:%S") + "]  ULTRA: " + str(distance) + "cm  |  IR: " + ir_str, flush=True)
    return distance, ir_vals

# =============================================================================
# BATTERY
# =============================================================================
def update_battery():
    voltage = 11.8
    if INA219_AVAILABLE:
        try:
            v = _ina.voltage()
            if v > 1.0:
                voltage = v
        except:
            pass
    pct = int(((max(config.BATTERY_MIN_V, min(config.BATTERY_MAX_V, voltage)) - config.BATTERY_MIN_V) / (config.BATTERY_MAX_V - config.BATTERY_MIN_V)) * 100)
    pct = max(0, min(100, pct))
    blynk_write(config.V_BATTERY_PCT, pct)
    print("BATTERY [" + time.strftime("%H:%M:%S") + "]  " + str(round(voltage, 2)) + "V = " + str(pct) + "%", flush=True)
    if pct < config.BATTERY_LOW_PCT:
        log("BATTERY LOW " + str(pct) + "% - Stopping!")
        motors.stop()
    return pct

# =============================================================================
# MOTOR WRAPPERS
# =============================================================================
def motor_forward(speed):
    motors.forward(speed)
    print("MOTOR: FWD " + str(round(speed / 255 * 100)) + "%", flush=True)

def motor_reverse(speed):
    motors.reverse(speed)
    print("MOTOR: REV " + str(round(speed / 255 * 100)) + "%", flush=True)

def motor_turn_left(speed):
    motors.turn_left(speed)
    print("MOTOR: LEFT " + str(round(speed / 255 * 100)) + "%", flush=True)

def motor_turn_right(speed):
    motors.turn_right(speed)
    print("MOTOR: RIGHT " + str(round(speed / 255 * 100)) + "%", flush=True)

def motor_stop():
    motors.stop()
    print("MOTOR: STOP", flush=True)

def process_motors():
    if not mission_active:
        motor_stop()
        return
    x = current_x if abs(current_x) > 50 else 0
    y = current_y if abs(current_y) > 50 else 0
    motors.set_speeds(
        max(min(y + x, master_speed), -master_speed),
        max(min(y - x, master_speed), -master_speed)
    )

# =============================================================================
# CAMERA
# =============================================================================
def capture_pi_frame():
    subprocess.run(
        ["rpicam-jpeg", "-o", "temp.jpg", "--width", "320", "--height", "240", "--nopreview", "-t", "1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return cv2.imread("temp.jpg")

# =============================================================================
# AUTO LINE FOLLOWING
# =============================================================================
def run_auto_mode():
    distance, ir_vals = update_sensors()
    if 0 < distance < config.STOP_DISTANCE_CM:
        motor_stop()
        log("AUTO: OBSTACLE " + str(distance) + "cm - STOP")
        return
    fl, nl, c, nr, fr = ir_vals
    if all(v == 1 for v in ir_vals):
        motor_forward(master_speed)
        print("AUTO: all IR WHITE - forward", flush=True)
        return
    if all(v == 0 for v in ir_vals):
        motor_stop()
        log("AUTO: STOP STRIP detected")
        return
    if c == 0 and nl == 1 and nr == 1:
        motor_forward(master_speed)
    elif nl == 0 or fl == 0:
        motor_turn_left(round(master_speed * 0.7))
    elif nr == 0 or fr == 0:
        motor_turn_right(round(master_speed * 0.7))
    else:
        motor_forward(master_speed)

# =============================================================================
# VISION
# =============================================================================
def run_vision():
    global mission_active
    frame = capture_pi_frame()
    if frame is None:
        return
    shape, cx = vision.identify_target(frame)
    if shape == "BLUE_CIRCULAR":
        log("VISION: BLUE target X=" + str(cx) + " - pick!")
        motor_stop()
        execute_pick_sequence()
        mission_active = False
        blynk_write(config.V_MISSION, 0)
        robot.state["mission_active"] = False
        log("MISSION: Complete - paused")
    elif shape == "OTHER_CIRCULAR":
        print("VISION: non-target, skip", flush=True)

# =============================================================================
# BLYNK HANDLERS
# V8  = Start/Pause mission
# V12 = Manual pick trigger
# =============================================================================
if BLYNK_AVAILABLE and blynk:

    @blynk.on("connected")
    def blynk_connected():
        global is_auto_mode, mission_active
        is_auto_mode = True
        mission_active = False
        blynk_write(config.V_OP_MODE, 1)
        blynk_write(config.V_MISSION, 0)
        log("BLYNK: Ready - press Start V8")
        update_battery()

    @blynk.on("V{}".format(config.V_THROTTLE))
    def h_speed(value):
        global master_speed
        master_speed = int(value[0])
        log("SPEED: " + str(round(master_speed / 255 * 100)) + "%")

    @blynk.on("V{}".format(config.V_JOYSTICK_X))
    def h_x(value):
        global current_x
        if is_auto_mode or not mission_active:
            return
        current_x = int(value[0])
        process_motors()

    @blynk.on("V{}".format(config.V_JOYSTICK_Y))
    def h_y(value):
        global current_y
        if is_auto_mode or not mission_active:
            return
        raw = int(value[0])
        current_y = raw * master_speed if raw in (1, -1) else raw
        process_motors()

    @blynk.on("V{}".format(config.V_OP_MODE))
    def h_mode(value):
        global is_auto_mode, current_x, current_y
        is_auto_mode = (int(value[0]) == 1)
        if is_auto_mode:
            log("MODE: AUTO")
        else:
            current_x = 0
            current_y = 0
            motor_stop()
            log("MODE: MANUAL")

    @blynk.on("V{}".format(config.V_MISSION))
    def h_mission(value):
        global mission_active
        mission_active = (int(value[0]) == 1)
        robot.state["mission_active"] = mission_active
        if mission_active:
            log("MISSION: START " + ("AUTO" if is_auto_mode else "MANUAL") + " " + str(round(master_speed / 255 * 100)) + "%")
        else:
            motor_stop()
            log("MISSION: PAUSED")

    @blynk.on("V12")
    def h_pick(value):
        if int(value[0]) == 1:
            log("V12: Pick triggered from Blynk")
            execute_pick_sequence()

# =============================================================================
# MAIN LOOP
# blynk.run() in main loop so handlers fire correctly
# sensor_last=0 fires immediately on boot
# =============================================================================
def run_mission_test():
    global mission_active, is_auto_mode

    print("=" * 55, flush=True)
    print("  PATROL ROBOT BOOT", flush=True)
    print("  BLYNK  : " + ("Online" if BLYNK_AVAILABLE else "Offline - Flask only"), flush=True)
    print("  INA219 : " + ("Online" if INA219_AVAILABLE else "Simulated 11.8V"), flush=True)
    print("  IR PINS: GPIO " + str(IR_PINS), flush=True)
    print("  SERVOS : BASE=CH4 SHOULDER=CH0 ELBOW=CH15 GRIPPER=CH3", flush=True)
    print("=" * 55, flush=True)

    motors.init()
    ir_setup()
    servo_home()

    battery_last = time.time()
    sensor_last  = 0
    vision_last  = time.time()

    print("Sensor readings every 5s - no Start needed:", flush=True)

    while True:
        now = time.time()

        if BLYNK_AVAILABLE and blynk:
            try:
                blynk.run()
            except:
                pass

        handle_dashboard_commands()

        if now - sensor_last >= 5.0:
            update_sensors()
            push_to_dashboard()
            sensor_last = now

        if mission_active and is_auto_mode:
            run_auto_mode()

        if mission_active and now - vision_last >= 2.0:
            run_vision()
            vision_last = now

        if now - battery_last >= 30.0:
            update_battery()
            battery_last = now

        time.sleep(0.05)

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    print("SYSTEM READY: Booting...", flush=True)
    try:
        # 1. Import your dashboard file
        import dashboard 
        
        # 2. Launch the dashboard inside main.py so they share memory!
        print("Starting Web Dashboard...")
        dash_thread = threading.Thread(target=lambda: dashboard.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True)
        dash_thread.start()
        
        # 3. Run your hardware loop
        run_mission_test()
        
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down...", flush=True)
    finally:
        motor_stop()
        motors.cleanup()
        servo_stop_all()
        _pi.stop()
        print("[SYSTEM] Done", flush=True)