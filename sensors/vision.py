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