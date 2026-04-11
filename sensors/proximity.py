# sensors/proximity.py
import time
# Note: You'll need to add your GPIO library here later (e.g., from gpiozero import DistanceSensor)

STOP_DISTANCE = 20.0 
WARNING_DISTANCE = 50.0

def get_distance():
    # Placeholder: In the real world, this reads the GPIO pins
    # For testing, we return a fixed value
    return 25.0 

def get_status():
    dist = get_distance()
    if dist < STOP_DISTANCE:
        return "DANGER"
    elif dist < WARNING_DISTANCE:
        return "WARNING"
    else:
        return "CLEAR"

def is_path_clear():
    return get_distance() > STOP_DISTANCE