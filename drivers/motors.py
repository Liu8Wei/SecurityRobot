# =============================================================================
# drivers/motors.py
# Controls the two DC geared motors via the L298N motor driver.
#
# HOW THE L298N WORKS:
#   Each motor needs 3 signals from the Pi:
#     IN1 + IN2  →  Direction (which way the motor spins)
#     ENA        →  Speed, sent as a PWM signal (0–255)
#
#   Direction truth table:
#     IN1=HIGH, IN2=LOW  → motor spins FORWARD
#     IN1=LOW, IN2=HIGH  → motor spins BACKWARD (REVERSE)
#     IN1=LOW, IN2=LOW   → motor STOPS (coasts)
#     IN1=HIGH, IN2=HIGH → motor BRAKES (locked, not recommended for long)
#
# WHY pigpio INSTEAD OF RPi.GPIO?
#   RPi.GPIO uses "software PWM" which is handled by Python timing.
#   If Python is busy (e.g. processing a camera frame), the PWM stutters
#   and the motor hums or jerks.
#   pigpio uses the Pi's hardware clock — it runs in the background
#   regardless of what Python is doing. Result: smooth, rock-solid speed.
#
# BEFORE RUNNING: Start the pigpio daemon first:
#   sudo pigpiod
# =============================================================================

import pigpio
import config

# This variable holds the connection to the pigpio daemon.
# It's set to None here and only created when init() is called.
_pi = None


# =============================================================================
# SETUP & TEARDOWN
# =============================================================================

def init():
    """
    Connects to the pigpio daemon and sets up all motor GPIO pins.
    Must be called ONCE before any other function in this file.
    """
    global _pi

    # Connect to the pigpio background service
    _pi = pigpio.pi()

    # Check the connection worked
    if not _pi.connected:
        raise RuntimeError("pigpio daemon is not running. Run: sudo pigpiod")

    # Tell pigpio which pins are OUTPUTS (the Pi sends signals out on these)
    # The direction pins (IN1-IN4)
    _pi.set_mode(config.L_MOTOR_FWD, pigpio.OUTPUT)  # Left IN1
    _pi.set_mode(config.L_MOTOR_REV, pigpio.OUTPUT)  # Left IN2
    _pi.set_mode(config.R_MOTOR_FWD, pigpio.OUTPUT)  # Right IN3
    _pi.set_mode(config.R_MOTOR_REV, pigpio.OUTPUT)  # Right IN4

    # The speed pins (ENA, ENB) — these will carry PWM signals
    _pi.set_mode(config.L_MOTOR_ENA, pigpio.OUTPUT)
    _pi.set_mode(config.R_MOTOR_ENB, pigpio.OUTPUT)

    # Start with everything OFF (LOW = 0 volts on that pin)
    _pi.write(config.L_MOTOR_FWD, 0)
    _pi.write(config.L_MOTOR_REV, 0)
    _pi.write(config.R_MOTOR_FWD, 0)
    _pi.write(config.R_MOTOR_REV, 0)

    # Set PWM frequency to 1000 Hz on the enable pins.
    # 1000 Hz is a good balance: smooth enough for motors, not too fast for L298N.
    _pi.set_PWM_frequency(config.L_MOTOR_ENA, 1000)
    _pi.set_PWM_frequency(config.R_MOTOR_ENB, 1000)

    # Set both motors to 0 speed (dutycycle 0 out of 255)
    _pi.set_PWM_dutycycle(config.L_MOTOR_ENA, 0)
    _pi.set_PWM_dutycycle(config.R_MOTOR_ENB, 0)

    print("[MOTORS] Initialized. All pins set. pigpio connected.")


def cleanup():
    """
    Stops all motors and releases GPIO pins.
    Call this when the program is shutting down.
    """
    global _pi
    if _pi and _pi.connected:
        stop()                         # Cut motor power first
        _pi.set_PWM_dutycycle(config.L_MOTOR_ENA, 0)
        _pi.set_PWM_dutycycle(config.R_MOTOR_ENB, 0)
        _pi.stop()                     # Disconnect from pigpio daemon
        _pi = None
    print("[MOTORS] Cleanup complete. GPIO released.")


# =============================================================================
# PRIVATE HELPER — controls one motor
# =============================================================================

def _set_motor(fwd_pin, rev_pin, ena_pin, speed):
    """
    Sets one motor's direction and speed.

    speed: an integer from -255 to +255
        positive = forward
        negative = reverse
        0        = stop

    This is a private function (starts with _) meaning it's meant to be
    used only inside this file. External code calls forward(), reverse(), etc.
    """
    # Clamp speed to valid range, just in case
    speed = max(-255, min(255, speed))

    if speed > 0:
        # FORWARD: IN1=HIGH, IN2=LOW
        _pi.write(fwd_pin, 1)          # HIGH (3.3V)
        _pi.write(rev_pin, 0)          # LOW  (0V)
        _pi.set_PWM_dutycycle(ena_pin, speed)

    elif speed < 0:
        # REVERSE: IN1=LOW, IN2=HIGH
        _pi.write(fwd_pin, 0)
        _pi.write(rev_pin, 1)
        _pi.set_PWM_dutycycle(ena_pin, abs(speed))  # abs() makes negative positive

    else:
        # STOP: IN1=LOW, IN2=LOW, speed=0
        _pi.write(fwd_pin, 0)
        _pi.write(rev_pin, 0)
        _pi.set_PWM_dutycycle(ena_pin, 0)


# =============================================================================
# PUBLIC API — call these from main.py or your test script
# =============================================================================

def set_speeds(left_speed, right_speed):
    """
    The main control function. Sets both motors independently.

    left_speed:  -255 to +255
    right_speed: -255 to +255
    positive = forward, negative = reverse, 0 = stop

    Example: set_speeds(200, 200)   → drive forward at ~78% speed
             set_speeds(200, -200)  → spin clockwise on the spot
             set_speeds(0, 0)       → stop
    """
    _set_motor(config.L_MOTOR_FWD, config.L_MOTOR_REV, config.L_MOTOR_ENA, left_speed)
    _set_motor(config.R_MOTOR_FWD, config.R_MOTOR_REV, config.R_MOTOR_ENB, right_speed)


def forward(speed=200):
    """Drive both motors forward. speed: 0–255 (default 200 ≈ 78%)"""
    set_speeds(speed, speed)
    print(f"[MOTORS] Forward @ {round(speed/255*100)}%")


def reverse(speed=200):
    """Drive both motors backward. speed: 0–255"""
    set_speeds(-speed, -speed)
    print(f"[MOTORS] Reverse @ {round(speed/255*100)}%")


def turn_left(speed=180):
    """
    Spin left: left motor reverses, right motor goes forward.
    This turns the robot on the spot (tank turn).
    """
    set_speeds(-speed, speed)
    print(f"[MOTORS] Turn Left @ {round(speed/255*100)}%")


def turn_right(speed=180):
    """
    Spin right: left motor goes forward, right motor reverses.
    """
    set_speeds(speed, -speed)
    print(f"[MOTORS] Turn Right @ {round(speed/255*100)}%")


def stop():
    """Stop both motors immediately."""
    set_speeds(0, 0)
    print("[MOTORS] Stop")