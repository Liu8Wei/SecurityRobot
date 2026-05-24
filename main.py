# =============================================================================
# main.py — Robot Mission Control (Corrected)
#
# FIXES APPLIED:
#   1. blynk.virtual_write("V4", ...) → virtual_write(4, ...) [integer, not string]
#   2. V2 mode handler was inverted vs clean-boot reset: now consistent (1=AUTO)
#   3. Blynk polling was starved by time.sleep(0.5) in mission loop — fixed with
#      smaller sleeps and blynk.run() called at every iteration
#   4. update_battery() used hardcoded voltage — now reads from INA219 via I2C
# =============================================================================

import time
import config
from sensors import proximity
from drivers import motors
from sensors import vision
import BlynkLib
import cv2
import subprocess

try:
    from ina219 import INA219  # pip install pi-ina219
    _ina = INA219(shunt_ohms=0.1, address=config.INA219_ADDRESS)
    _ina.configure()
    INA219_AVAILABLE = True
except Exception as e:
    print(f"[WARN] INA219 not available: {e}. Battery will show simulated value.")
    INA219_AVAILABLE = False

blynk = BlynkLib.Blynk(config.BLYNK_AUTH)

# --- Global State ---
is_auto_mode   = True
mission_active = False
current_x      = 0
current_y      = 0
master_speed   = 255


# =============================================================================
# BLYNK: Clean Boot
# =============================================================================

@blynk.on("connected")
def blynk_connected():
    """Forces a clean boot: resets Python state AND syncs the phone screen."""
    global is_auto_mode, mission_active

    is_auto_mode   = True
    mission_active = False

    # FIX: V2 convention is now 1=AUTO, 0=MANUAL (consistent with handle_op_mode)
    blynk.virtual_write(config.V_OP_MODE, 1)      # Show AUTO on phone  ← was "V2", wrong int
    blynk.virtual_write(config.V_MISSION, 0)       # Show Paused on phone ← was "V8"

    print("SYS: Connected to Blynk. Clean boot complete. Defaults: AUTO / PAUSED.")


# =============================================================================
# MOTOR MIXING ENGINE
# =============================================================================

def process_motors():
    """Differential steering: converts joystick X/Y to left/right motor speeds."""
    global current_x, current_y, master_speed

    x = current_x if abs(current_x) > 50 else 0
    y = current_y if abs(current_y) > 50 else 0

    left_raw  = y + x
    right_raw = y - x

    left_clamped  = max(min(left_raw,  master_speed), -master_speed)
    right_clamped = max(min(right_raw, master_speed), -master_speed)

    l_speed = round((abs(left_clamped)  / 255) * 100, 1)
    r_speed = round((abs(right_clamped) / 255) * 100, 1)

    if left_clamped == 0 and right_clamped == 0:
        print("| IDLE: Motors Off |")
    else:
        l_dir = "FWD" if left_clamped > 0 else "REV"
        r_dir = "FWD" if right_clamped > 0 else "REV"
        print(f"MOTORS -> L: {l_speed}% ({l_dir}) | R: {r_speed}% ({r_dir})")

    # TODO: Pass left_clamped/right_clamped to drivers/motors.py when implemented
    # motors.set_speeds(left_clamped, right_clamped)


# =============================================================================
# BLYNK EVENT HANDLERS
# =============================================================================

@blynk.on("V{}".format(config.V_THROTTLE))
def handle_master_speed(value):
    global master_speed
    master_speed = int(value[0])
    print(f"--- Throttle set to: {round((master_speed / 255) * 100)}% ---")


@blynk.on("V{}".format(config.V_JOYSTICK_X))
def handle_navigation_x(value):
    global current_x
    if is_auto_mode:
        return  # Ignore joystick in auto mode
    current_x = int(value[0])
    process_motors()


@blynk.on("V{}".format(config.V_JOYSTICK_Y))
def handle_navigation_y(value):
    global current_y
    if is_auto_mode:
        return  # Ignore joystick in auto mode
    raw = int(value[0])
    # Web button sends -1 or 1 → scale by master_speed
    current_y = raw * master_speed if raw in (1, -1) else raw
    process_motors()


@blynk.on("V{}".format(config.V_OP_MODE))
def handle_op_mode(value):
    """
    FIX: Original had inverted logic vs clean-boot.
    Convention: 1 = AUTO (line following), 0 = MANUAL (remote control).
    """
    global is_auto_mode, current_x, current_y
    is_auto_mode = (int(value[0]) == 1)  # ← was (int(value[0]) == 0), inverted

    if is_auto_mode:
        print("--- MODE: AUTO (Line Following Active) ---")
    else:
        current_x = 0
        current_y = 0
        process_motors()
        print("--- MODE: MANUAL (Remote Control Active) ---")


@blynk.on("V{}".format(config.V_MISSION))
def toggle_mission(value):
    """Start/Pause the active scanning mission."""
    global mission_active
    mission_active = (int(value[0]) == 1)
    state = "STARTED" if mission_active else "PAUSED"
    print(f"GUI: Mission {state} by operator.")


# =============================================================================
# TELEMETRY
# =============================================================================

def update_battery():
    """
    FIX: Original used hardcoded current_voltage = 11.8 (never read INA219).
    Now reads real voltage from INA219 over I2C.
    Falls back to a simulated value if INA219 is unavailable.
    """
    if INA219_AVAILABLE:
        try:
            current_voltage = _ina.voltage()
        except Exception as e:
            print(f"[WARN] INA219 read failed: {e}. Using fallback.")
            current_voltage = 11.8
    else:
        current_voltage = 11.8  # Simulation fallback

    percentage = round(
        ((current_voltage - config.BATTERY_MIN_V) /
         (config.BATTERY_MAX_V - config.BATTERY_MIN_V)) * 100
    )
    percentage = max(0, min(100, percentage))  # Clamp to 0–100

    blynk.virtual_write(config.V_BATTERY_PCT, percentage)  # FIX: integer, not "V4"

    if percentage < config.BATTERY_LOW_PCT:
        blynk.log_event("low_battery_alert", f"Battery critical: {percentage}%")

    return percentage


def update_log(message):
    """Send a timestamped message to the Blynk terminal widget."""
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}\n"
    blynk.virtual_write(config.V_LOG, formatted)  # FIX: integer, not "V6"
    print(f"Log: {formatted}", end="")


# =============================================================================
# CAMERA
# =============================================================================

def capture_pi_frame():
    """Captures a frame using rpicam-jpeg, bypassing OpenCV's camera limits."""
    subprocess.run(
        ["rpicam-jpeg", "-o", "temp.jpg",
         "--width", "320", "--height", "240",
         "--nopreview", "-t", "1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return cv2.imread("temp.jpg")


# =============================================================================
# MISSION LOOP
# =============================================================================

def run_mission_test():
    global mission_active, is_auto_mode

    print("-" * 40)
    print("ROBOT SYSTEM: STANDBY. Waiting for GUI 'Start' signal...")
    print("-" * 40)

    telemetry_timer = time.time()

    while True:
        # FIX: blynk.run() is now called on EVERY loop iteration.
        # Original starved it with time.sleep(0.5) inside the mission branch,
        # causing Blynk to disconnect after ~5 seconds of inactivity.
        blynk.run()

        # --- Telemetry update every 10 seconds ---
        if time.time() - telemetry_timer > 10:
            update_battery()
            telemetry_timer = time.time()

        if mission_active and is_auto_mode:
            frame = capture_pi_frame()
            if frame is None:
                time.sleep(0.05)  # Short sleep, still allows blynk.run() next iteration
                continue

            shape, cx = vision.identify_target(frame)

            if shape == "OTHER_CIRCULAR":
                print("Circular object detected (wrong color). Ignoring.         ", end="\r")

            elif shape == "BLUE_CIRCULAR":
                print(f"\n[ALERT] BLUE CIRCULAR object confirmed at X={cx}")
                print("DECISION: PICK")
                update_log(f"Blue target acquired at X={cx}. Executing pick.")

                # TODO: Replace with actual arm sequence from drivers/servos.py
                # Example: servos.execute_pick_sequence()
                print("ACTION: Arm sequence placeholder (implement servos.py)")
                time.sleep(0.5)  # FIX: Reduced from 2s so Blynk stays alive

                mission_active = False
                blynk.virtual_write(config.V_MISSION, 0)  # Reflect pause on phone
                print("ACTION: Pick complete. Mission paused.")

            else:
                print("Scanning... No circular targets visible.                    ", end="\r")

            # FIX: Reduced from 0.5s. blynk.run() runs on next iteration ~50ms later.
            time.sleep(0.05)

        else:
            time.sleep(0.05)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("SYSTEM READY: Booting Mission Protocol...")
    run_mission_test()