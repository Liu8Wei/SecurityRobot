# =============================================================================
# main_backup.py — CAMERA & DASHBOARD INTEGRATION
# =============================================================================

import cv2
import time
import threading
from picamera2 import Picamera2
import dashboard as robot 
from sensors import vision

print("=" * 45)
print("  INTEGRATION TEST: Camera + Web UI")
print("=" * 45)

# 1. Start Web Dashboard in the background
threading.Thread(target=lambda: robot.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

# 2. Turn on the Camera Hardware
try:
    print("[SYSTEM] Warming up camera...")
    camera = Picamera2()
    config = camera.create_preview_configuration(main={"size": (320, 240)})
    camera.configure(config)
    camera.start()
    time.sleep(2)
except Exception as e:
    print(f"[FATAL] Camera failed to start. Error: {e}")
    exit()

print(f"\n>>> DASHBOARD LIVE AT: http://{robot.PI_IP}:5000 <<<\n")

frame_count = 0

try:
    while True:
        # 3. Grab picture & push to website
        buf = camera.capture_array()
        frame = cv2.cvtColor(buf, cv2.COLOR_RGB2BGR)
        robot.set_frame(frame)
        
        # 4. Run Vision Logic
        # 4. Run Vision Logic
        frame_count += 1
        shape, cx = vision.identify_target(frame)
        if shape == "BLACK_CIRCULAR":
            robot.state["vision_status"] = "BLACK CIRCLE DETECTED"
        else:
            robot.state["vision_status"] = "Scanning for targets..."
            
        time.sleep(0.05) 
        
except KeyboardInterrupt:
    print("\n[SYSTEM] Safely shutting down camera...")
    camera.stop()
    print("[SYSTEM] Sleeping time.")