import cv2
import numpy as np

def identify_target(frame):
    """Finds ANY colored object, checks if it's a circle, then checks if it's blue."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # TRICK: Instead of a blue mask, we look at 'Saturation' (how colorful something is).
    # White, black, and gray backgrounds have low saturation. Colored objects have high saturation.
    _, sat_mask = cv2.threshold(hsv[:, :, 1], 70, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(sat_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return "NONE", None

    # Find the biggest colored blob on the screen
    biggest_blob = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest_blob) > 500:
        
        # Figure out the Shape
        epsilon = 0.02 * cv2.arcLength(biggest_blob, True)
        approx = cv2.approxPolyDP(biggest_blob, epsilon, True)
        corners = len(approx)

        # If it has more than 7 corners, OpenCV considers it circular
        if corners > 7:
            # Find the exact center (Centroid)
            M = cv2.moments(biggest_blob)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Look at the exact pixel in the center of the circle to get its Hue (color)
                # Ensure we don't accidentally check a pixel off the screen
                cy = min(max(cy, 0), frame.shape[0]-1)
                cx = min(max(cx, 0), frame.shape[1]-1)
                
                hue = hsv[cy, cx][0]
                
                # In OpenCV, Blue is a Hue between 100 and 140
                if 100 <= hue <= 140:
                    return "BLUE_CIRCULAR", cx
                else:
                    return "OTHER_CIRCULAR", cx
                    
        return "NON_CIRCULAR", None
        
    return "NONE", None
