# =============================================================================
# main_backup.py — TRUE ISOLATED VISION TEST
# Tests object detection. Does NOT use the dashboard.
# =============================================================================

import cv2
import time
from picamera2 import Picamera2
from sensors import vision

print("=" * 45)
print("  STANDALONE VISION TEST")
print("  Make sure NOTHING else is running!")
print("=" * 45)

# 1. Initialize the Camera Hardware directly
try:
    print("[SYSTEM] Warming up camera...")
    camera = Picamera2()
    config = camera.create_preview_configuration(main={"size": (320, 240)})
    camera.configure(config)
    camera.start()
    time.sleep(2) # Crucial for auto-exposure to adjust to room light
except Exception as e:
    print(f"[FATAL] Camera failed to start. Is the dashboard running? Kill it first!\nError: {e}")
    exit()

frame_count = 0

try:
    while True:
        # 2. Grab the raw picture
        buf = camera.capture_array()
        frame = cv2.cvtColor(buf, cv2.COLOR_RGB2BGR)
        
        # 3. Hand it to your newly updated vision file
        frame_count += 1
        shape, cx = vision.identify_target(frame)
        timestamp = time.strftime("%H:%M:%S")
        
        # 4. Print the exact results
        if shape == "BLACK_CIRCULAR":
            print(f"[{timestamp}] Frame#{frame_count:04d} | >>> BLACK TARGET LOCKED | CX: {cx}")
            cv2.imwrite("shadow_ghost.jpg", frame)
        elif shape == "NON_CIRCULAR":
            print(f"[{timestamp}] Frame#{frame_count:04d} | NON_CIRCULAR (Dark object, not round) | CX: {cx}")
            
        time.sleep(0.2) # 5 FPS is plenty for testing
        
except KeyboardInterrupt:
    print("\n[SYSTEM] Safely shutting down camera...")
    camera.stop()
    print("[SYSTEM] Test Complete.")