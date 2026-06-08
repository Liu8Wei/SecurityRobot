# =============================================================================
# main.py - IDP Patrol Robot Full Code
# Robot: 4-DOF Pick-and-Grab Towing Robot
# Controller: Raspberry Pi Zero 2W
#
# PIN ASSIGNMENTS:
#   A4950 Left:   IN1=GPIO17(Pin11), IN2=GPIO24(Pin18)
#   A4950 Right:  IN1=GPIO25(Pin22), IN2=GPIO23(Pin16)
#   HC-SR04:      TRIG=GPIO22(Pin15), ECHO=GPIO27(Pin13)
#   IR Sensors:   GPIO5,6,12,16,20
#   Servos:       GPIO19,21,26,14
#   INA219:       SDA=GPIO2, SCL=GPIO3
#
# BLYNK VIRTUAL PINS:
#   V1 = Joystick X (manual left/right)
#   V2 = Auto(1)/Manual(0) toggle
#   V3 = Ultrasonic distance (cm)
#   V4 = Battery percentage
#   V5 = Joystick Y (manual forward/backward)
#   V6 = Terminal log
#   V7 = IR sensor status
#   V8 = Start(1)/Pause(0) mission
#   V9 = Master speed throttle (0-255)
# =============================================================================

import time
import config
from sensors import proximity
from drivers import motors
import BlynkLib
import pigpio

# =============================================================================
# INA219 POWER MONITOR
# =============================================================================
try:
    from ina219 import INA219
    _ina = INA219(shunt_ohms=0.1, address=config.INA219_ADDRESS)
    _ina.configure()
    INA219_AVAILABLE = True
    print("[INA219] Connected OK")
except Exception as e:
    print(f"[WARN] INA219 not available: {e}. Using simulated battery.")
    INA219_AVAILABLE = False

# =============================================================================
# PIGPIO SETUP
# =============================================================================
_pi = pigpio.pi()
if not _pi.connected:
    print("[WARN] pigpio not running. Run: sudo pigpiod")

# =============================================================================
# SERVO SETUP via pigpio hardware PWM
# Wire: Brown=GND, Red=V+(5V), Yellow/Orange=Signal
# =============================================================================
def servo_move(gpio_pin, angle):
    angle = max(0, min(180, angle))
    pulse = config.SERVO_MIN_US + (angle / 180.0) * (config.SERVO_MAX_US - config.SERVO_MIN_US)
    _pi.set_servo_pulsewidth(gpio_pin, pulse)
    print(f"[SERVO] GPIO{gpio_pin} to {angle} degrees")

def servo_home():
    if _pi.connected:
        servo_move(config.SERVO_BASE,     90)
        servo_move(config.SERVO_SHOULDER, 90)
        servo_move(config.SERVO_ELBOW,    90)
        servo_move(config.SERVO_GRIPPER,  90)
        print("[SERVO] All servos at home position")

def servo_stop_all():
    if _pi.connected:
        for pin in [config.SERVO_BASE, config.SERVO_SHOULDER,
                    config.SERVO_ELBOW, config.SERVO_GRIPPER]:
            _pi.set_servo_pulsewidth(pin, 0)

# =============================================================================
# IR LINE SENSORS via pigpio
# 0 = black line, 1 = white surface
# =============================================================================
IR_PINS = [
    config.IR_SENSOR_1,   # GPIO5  - Far left
    config.IR_SENSOR_2,   # GPIO6  - Centre left
    config.IR_SENSOR_3,   # GPIO12 - Centre
    config.IR_SENSOR_4,   # GPIO16 - Centre right
    config.IR_SENSOR_5,   # GPIO20 - Far right
]

def ir_setup():
    if _pi.connected:
        for pin in IR_PINS:
            _pi.set_mode(pin, pigpio.INPUT)
        print("[IR] 5x IR sensors initialized")

def read_ir_sensors():
    if not _pi.connected:
        return [0, 0, 0, 0, 0]
    return [_pi.read(pin) for pin in IR_PINS]

# =============================================================================
# BLYNK SETUP
# =============================================================================
blynk = BlynkLib.Blynk(config.BLYNK_AUTH)

# =============================================================================
# GLOBAL STATE
# =============================================================================
is_auto_mode   = True
mission_active = False
current_x      = 0
current_y      = 0
master_speed   = 255

# =============================================================================
# LOG HELPER
# =============================================================================
def log(message):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}\n"
    blynk.virtual_write(config.V_LOG, formatted)
    print(f"LOG: {formatted}", end="")

# =============================================================================
# BATTERY UPDATE - always every 10 seconds
# =============================================================================
def update_battery():
    if INA219_AVAILABLE:
        try:
            voltage = _ina.voltage()
            print(f"[BATTERY] INA219 raw = {voltage}V")
        except Exception as e:
            print(f"[WARN] INA219 read error: {e}")
            voltage = 11.8
    else:
        voltage = 11.8

    # Safety check
    if voltage < 1.0:
        print(f"[BATTERY] Voltage {voltage}V too low - using fallback 11.8V")
        voltage = 11.8

    min_v = config.BATTERY_MIN_V
    max_v = config.BATTERY_MAX_V

    voltage_clamped = max(min_v, min(max_v, voltage))
    pct = int(((voltage_clamped - min_v) / (max_v - min_v)) * 100.0)
    pct = max(0, min(100, pct))

    print(f"[BATTERY] {voltage:.2f}V = {pct}% -> V4")

    blynk.virtual_write(config.V_BATTERY_PCT, pct)
    log(f"Battery: {voltage:.2f}V = {pct}%")

    if pct < config.BATTERY_LOW_PCT:
        log(f"[WARN] LOW BATTERY {pct}%! Stopping motors.")
        motors.stop()

    return pct

# =============================================================================
# MOTOR MIXING
# =============================================================================
def process_motors():
    global current_x, current_y, master_speed

    if not mission_active:
        motors.stop()
        return

    x = current_x if abs(current_x) > 50 else 0
    y = current_y if abs(current_y) > 50 else 0

    left_raw  = y + x
    right_raw = y - x

    left  = max(min(left_raw,  master_speed), -master_speed)
    right = max(min(right_raw, master_speed), -master_speed)

    motors.set_speeds(left, right)

    if left == 0 and right == 0:
        print("[MOTORS] Idle")
    else:
        l_pct = round((abs(left)  / 255) * 100, 1)
        r_pct = round((abs(right) / 255) * 100, 1)
        l_dir = "FWD" if left  > 0 else "REV"
        r_dir = "FWD" if right > 0 else "REV"
        print(f"[MOTORS] L:{l_pct}% ({l_dir}) R:{r_pct}% ({r_dir})")

# =============================================================================
# SENSOR UPDATE
# =============================================================================
def update_sensors():
    # Read ultrasonic 3 times and average
    readings = []
    for i in range(3):
        d = proximity.get_distance()
        if d < 999:
            readings.append(d)
        time.sleep(0.01)

    distance = round(sum(readings) / len(readings), 1) if readings else 999.0
    blynk.virtual_write(config.V_ULTRASONIC_CM, distance)

    ir_vals = read_ir_sensors()
    ir_str  = f"L:{ir_vals[0]} CL:{ir_vals[1]} C:{ir_vals[2]} CR:{ir_vals[3]} R:{ir_vals[4]}"
    blynk.virtual_write(config.V_IR_STATUS, ir_str)

    log(f"ULTRA:{distance}cm | IR:[{ir_str}]")

    return distance, ir_vals

# =============================================================================
# AUTO LINE FOLLOWING
# =============================================================================
def auto_line_follow():
    if not mission_active:
        motors.stop()
        return

    distance, ir_vals = update_sensors()

    if distance < config.STOP_DISTANCE_CM:
        motors.stop()
        log(f"[STOP] Object at {distance}cm!")
        return

    far_left   = ir_vals[0]
    near_left  = ir_vals[1]
    center     = ir_vals[2]
    near_right = ir_vals[3]
    far_right  = ir_vals[4]

    spd = master_speed

    if center == 0 and near_left == 1 and near_right == 1:
        motors.forward(spd)
    elif near_left == 0 or far_left == 0:
        motors.turn_left(round(spd * 0.7))
    elif near_right == 0 or far_right == 0:
        motors.turn_right(round(spd * 0.7))
    elif center == 1 and near_left == 1 and near_right == 1:
        motors.stop()
        log("[STOP] Line lost!")
    else:
        motors.forward(spd)

# =============================================================================
# BLYNK CONNECTED
# =============================================================================
@blynk.on("connected")
def blynk_connected():
    global is_auto_mode, mission_active
    is_auto_mode   = True
    mission_active = False

    blynk.virtual_write(config.V_OP_MODE, 1)
    blynk.virtual_write(config.V_MISSION,  0)
    blynk.virtual_write(config.V_LOG, "[SYSTEM] Connected! Press Start to begin.\n")

    update_battery()

    print("SYS: Connected to Blynk. Defaults: AUTO / PAUSED.")

# =============================================================================
# BLYNK HANDLERS
# =============================================================================
@blynk.on("V{}".format(config.V_JOYSTICK_X))
def handle_x(value):
    global current_x
    if is_auto_mode or not mission_active:
        return
    current_x = int(value[0])
    process_motors()

@blynk.on("V{}".format(config.V_OP_MODE))
def handle_op_mode(value):
    global is_auto_mode, current_x, current_y
    is_auto_mode = (int(value[0]) == 1)
    if is_auto_mode:
        log("MODE: AUTO - Line following active")
    else:
        current_x = 0
        current_y = 0
        motors.stop()
        log("MODE: MANUAL - Use joystick to drive")

@blynk.on("V{}".format(config.V_JOYSTICK_Y))
def handle_y(value):
    global current_y
    if is_auto_mode or not mission_active:
        return
    raw = int(value[0])
    current_y = raw * master_speed if raw in (1, -1) else raw
    process_motors()

@blynk.on("V{}".format(config.V_MISSION))
def toggle_mission(value):
    global mission_active
    mission_active = (int(value[0]) == 1)
    state = "STARTED" if mission_active else "PAUSED"
    log(f"Mission {state} by operator.")
    if not mission_active:
        motors.stop()

@blynk.on("V{}".format(config.V_THROTTLE))
def handle_speed(value):
    global master_speed
    master_speed = int(value[0])
    pct = round((master_speed / 255) * 100)
    log(f"Speed set to {pct}%")

# =============================================================================
# MAIN LOOP
# =============================================================================
def run_robot():
    print("-" * 40)
    print("ROBOT SYSTEM: STANDBY. Waiting for GUI Start signal...")
    print("-" * 40)

    motors.init()
    ir_setup()
    servo_home()

    battery_last = time.time()
    sensor_last  = time.time()

    while True:
        blynk.run()
        now = time.time()

        if mission_active:
            if is_auto_mode:
                auto_line_follow()
            else:
                if now - sensor_last > 1.0:
                    update_sensors()
                    sensor_last = now

        # Battery always updates every 10 seconds
        if now - battery_last > 10.0:
            update_battery()
            battery_last = now

        time.sleep(0.05)

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    print("SYSTEM READY: Booting Mission Protocol...")
    try:
        run_robot()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down...")
        motors.stop()
        motors.cleanup()
        servo_stop_all()
        if _pi.connected:
            _pi.stop()
        print("[SYSTEM] Shutdown complete")