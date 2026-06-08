# =============================================================================
# drivers/motors.py - A4950 Motor Driver
# Left motor:  IN1=GPIO17, IN2=GPIO24
# Right motor: IN1=GPIO25, IN2=GPIO23
#
# A4950 TRUTH TABLE:
#   IN1=HIGH, IN2=LOW  = forward
#   IN1=LOW,  IN2=HIGH = backward
#   IN1=LOW,  IN2=LOW  = stop
#
# Speed via PWM on IN1 or IN2 directly (no ENA/ENB needed)
# =============================================================================

import pigpio
import config

_pi = None

def init():
    global _pi
    _pi = pigpio.pi()

    if not _pi.connected:
        raise RuntimeError("pigpio daemon not running. Run: sudo pigpiod")

    _pi.set_mode(config.L_MOTOR_FWD, pigpio.OUTPUT)  # GPIO17
    _pi.set_mode(config.L_MOTOR_REV, pigpio.OUTPUT)  # GPIO24
    _pi.set_mode(config.R_MOTOR_FWD, pigpio.OUTPUT)  # GPIO25
    _pi.set_mode(config.R_MOTOR_REV, pigpio.OUTPUT)  # GPIO23

    _pi.set_PWM_frequency(config.L_MOTOR_FWD, 1000)
    _pi.set_PWM_frequency(config.L_MOTOR_REV, 1000)
    _pi.set_PWM_frequency(config.R_MOTOR_FWD, 1000)
    _pi.set_PWM_frequency(config.R_MOTOR_REV, 1000)

    _pi.set_PWM_dutycycle(config.L_MOTOR_FWD, 0)
    _pi.set_PWM_dutycycle(config.L_MOTOR_REV, 0)
    _pi.set_PWM_dutycycle(config.R_MOTOR_FWD, 0)
    _pi.set_PWM_dutycycle(config.R_MOTOR_REV, 0)

    print("[MOTORS] A4950 initialized OK")

def cleanup():
    global _pi
    if _pi and _pi.connected:
        stop()
        _pi.stop()
        _pi = None
    print("[MOTORS] Cleanup complete")

def _set_motor(fwd_pin, rev_pin, speed):
    speed = max(-255, min(255, speed))
    if speed > 0:
        _pi.set_PWM_dutycycle(fwd_pin, speed)
        _pi.set_PWM_dutycycle(rev_pin, 0)
    elif speed < 0:
        _pi.set_PWM_dutycycle(fwd_pin, 0)
        _pi.set_PWM_dutycycle(rev_pin, abs(speed))
    else:
        _pi.set_PWM_dutycycle(fwd_pin, 0)
        _pi.set_PWM_dutycycle(rev_pin, 0)

def set_speeds(left_speed, right_speed):
    _set_motor(config.L_MOTOR_FWD, config.L_MOTOR_REV, left_speed)
    _set_motor(config.R_MOTOR_FWD, config.R_MOTOR_REV, right_speed)

def forward(speed=200):
    set_speeds(speed, speed)
    print(f"[MOTORS] Forward {round(speed/255*100)}%")

def reverse(speed=200):
    set_speeds(-speed, -speed)
    print(f"[MOTORS] Reverse {round(speed/255*100)}%")

def turn_left(speed=180):
    set_speeds(-speed, speed)
    print(f"[MOTORS] Turn Left {round(speed/255*100)}%")

def turn_right(speed=180):
    set_speeds(speed, -speed)
    print(f"[MOTORS] Turn Right {round(speed/255*100)}%")

def stop():
    set_speeds(0, 0)
    print("[MOTORS] Stopped")