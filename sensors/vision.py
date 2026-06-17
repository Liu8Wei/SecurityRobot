# =============================================================================
# sensors/vision.py — Camera Target Identification
# Detects the largest DARK/BLACK circular object in a frame.
#
# HOW IT WORKS:
#   1. Convert BGR to HSV
#   2. Mask for BLACK pixels — low Value (brightness), any Hue
#   3. Morphological opening — removes noise
#   4. Find largest contour — ignores anything under 300px
#   5. Shape check — >5 polygon corners = circular
#   6. Return centroid CX for alignment
#
# RETURNS:
#   ("BLACK_CIRCULAR", cx)  — black circle found
#   ("NON_CIRCULAR",   cx)  — dark object found but not circular
#   ("NONE",          None) — nothing detected
# =============================================================================

import cv2
import numpy as np


def identify_target(frame):
    if frame is None:
        return "NONE", None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, w = frame.shape[:2]

    # --- STEP 1: Mask for BLACK pixels ---
    # Black = low Value (dark), Saturation can be anything
    # HSV: H=0-180, S=0-255, V=0-60 (very dark)
    lower_black = np.array([0,   0,   0  ])
    upper_black = np.array([180, 255, 80 ])

    black_mask = cv2.inRange(hsv, lower_black, upper_black)

    # --- STEP 2: Morphological cleanup ---
    kernel = np.ones((5, 5), np.uint8)
    black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
    black_mask = cv2.dilate(black_mask, kernel, iterations=1)

    # --- STEP 3: Find contours ---
    contours, _ = cv2.findContours(
        black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return "NONE", None

    biggest_blob = max(contours, key=cv2.contourArea)

    if cv2.contourArea(biggest_blob) < 300:
        return "NONE", None

    # --- STEP 4: Get centroid and Area ---
    M = cv2.moments(biggest_blob)
    if M["m00"] == 0:
        return "NONE", None

    cx = int(M["m10"] / M["m00"])
    cx = max(0, min(cx, w - 1))
    
    area = cv2.contourArea(biggest_blob)
    perimeter = cv2.arcLength(biggest_blob, True)
    
    if perimeter == 0:
        return "NONE", None

    # --- STEP 5: True Shape Classification (Circularity) ---
    # Formula: 4 * pi * (Area / Perimeter^2)
    # 1.0 = Perfect Circle. Shadows and wires will be < 0.5.
    circularity = 4 * np.pi * (area / (perimeter * perimeter))
    
    # Require an 80% match to a perfect circle
    if circularity > 0.60: 
        return "BLACK_CIRCULAR", cx
    else:
        return "NON_CIRCULAR", cx


def draw_debug(frame):
    """
    Draws contours and detection label onto frame for visual debugging.
    Usage:
        annotated = vision.draw_debug(frame)
        cv2.imwrite("debug.jpg", annotated)
    """
    if frame is None:
        return frame

    result = frame.copy()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, w = frame.shape[:2]

    lower_black = np.array([0,   0,   0  ])
    upper_black = np.array([180, 255, 80 ])
    black_mask  = cv2.inRange(hsv, lower_black, upper_black)
    kernel      = np.ones((5, 5), np.uint8)
    black_mask  = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(
        black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        cv2.putText(result, "NONE", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return result

    biggest_blob = max(contours, key=cv2.contourArea)
    cv2.drawContours(result, [biggest_blob], -1, (0, 255, 0), 2)

    shape, cx = identify_target(frame)
    label = f"{shape} cx={cx}"
    cv2.putText(result, label, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    if cx is not None:
        M = cv2.moments(biggest_blob)
        if M["m00"] != 0:
            cy_val = int(M["m01"] / M["m00"])
            cv2.circle(result, (cx, cy_val), 8, (0, 0, 255), -1)

    return result