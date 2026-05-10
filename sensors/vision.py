import cv2
import numpy as np

def identify_shape(frame):
    # 1. Convert to HSV and Mask (Example for Green)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([90, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # 2. Find Contours
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500: # Ignore tiny noise
            # 3. Approximate the Shape
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            corners = len(approx)

            # 4. Logic by Corner Count
            if corners == 4:
                return "CUBOID"
            elif 8 <= corners <= 12: # Stars can be messy, look for a range
                return "STAR"
            else:
                return "CIRCULAR"
    return "NONE"

# Add this to the bottom of sensors/vision.py

def draw_debug_info(frame, cx, shape):
    """Draws targeting lines and saves the image."""
    # Draw a vertical line exactly where the robot thinks the center is
    cv2.line(frame, (cx, 0), (cx, 240), (0, 255, 0), 2)
    
    # Write the shape name on the screen
    cv2.putText(frame, f"ID: {shape}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    # Save the picture
    cv2.imwrite('captures/current_view.jpg', frame)