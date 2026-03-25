import time

# Thresholds (in centimeters)
STOP_DISTANCE = 20.0  # Stop if something is closer than 20cm
WARNING_DISTANCE = 50.0 # Slow down if something is closer than 50cm

def get_distance():
    """
    Simulates reading the Ultrasonic Sensor.
    Once you have the RP02W, we will put the real GPIO code here.
    """
    # For now, we 'fake' a safe distance
    return 100.0 

def is_path_clear():
    dist = get_distance()
    if dist < STOP_DISTANCE:
        return False
    return True

def check_pir():
    """
    Simulates the PIR motion sensor.
    Returns True if motion is detected.
    """
    # Fake: No motion detected
    return False