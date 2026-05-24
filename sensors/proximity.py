# =============================================================================
# sensors/proximity.py — HC-SR04 Ultrasonic Sensor (Corrected)
# Uses pigpio for accurate microsecond timing.
# FIX: Original file returned hardcoded 25.0 and never read real hardware.
# =============================================================================

import time
import pigpio
import config

_pi = None

def _get_pi():
    """Returns a shared pigpio connection. Raises if daemon is not running."""
    global _pi
    if _pi is None or not _pi.connected:
        _pi = pigpio.pi()
        if not _pi.connected:
            raise RuntimeError(
                "pigpio daemon not running. Start it with: sudo pigpiod"
            )
        # Set TRIG as output, ECHO as input
        _pi.set_mode(config.TRIG_PIN, pigpio.OUTPUT)
        _pi.set_mode(config.ECHO_PIN, pigpio.INPUT)
    return _pi


def get_distance() -> float:
    """
    Fires the HC-SR04 and returns measured distance in cm.
    Returns 999.0 if no echo is received (object out of range or wiring issue).

    WIRING REMINDER: ECHO pin outputs 5V. A 1kΩ + 2kΩ voltage divider
    is required to drop it to 3.3V before connecting to the Pi GPIO.
    """
    try:
        pi = _get_pi()

        # Send a clean 10µs trigger pulse
        pi.gpio_trigger(config.TRIG_PIN, 10, 1)

        # Wait for ECHO to go HIGH (start of pulse)
        timeout = time.time() + 0.05  # 50ms max wait
        while pi.read(config.ECHO_PIN) == 0:
            if time.time() > timeout:
                return 999.0
        pulse_start = time.time()

        # Wait for ECHO to go LOW (end of pulse)
        timeout = time.time() + 0.05
        while pi.read(config.ECHO_PIN) == 1:
            if time.time() > timeout:
                return 999.0
        pulse_end = time.time()

        # Distance = (time × speed of sound) / 2
        # Speed of sound ≈ 34300 cm/s at room temperature
        duration = pulse_end - pulse_start
        distance = (duration * 34300) / 2
        return round(distance, 1)

    except Exception as e:
        print(f"[PROXIMITY] Sensor read error: {e}")
        return 999.0


def get_status() -> str:
    """Returns DANGER / WARNING / CLEAR based on distance thresholds in config."""
    dist = get_distance()
    if dist < config.STOP_DISTANCE_CM:
        return "DANGER"
    elif dist < config.WARNING_DISTANCE_CM:
        return "WARNING"
    else:
        return "CLEAR"


def is_path_clear() -> bool:
    """Returns True if no obstacle within STOP_DISTANCE_CM."""
    return get_distance() > config.STOP_DISTANCE_CM


def cleanup():
    """Release pigpio resources. Call on shutdown."""
    global _pi
    if _pi and _pi.connected:
        _pi.stop()
        _pi = None