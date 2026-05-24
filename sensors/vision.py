# =============================================================================
# sensors/vision.py — Camera Target Identification (Corrected)
# FIX: Original sampled a single pixel at the centroid for color detection.
#      One noise/shadow pixel was enough to cause false negatives.
#      Now samples a 10x10 pixel region and uses the median hue.
# =============================================================================

import cv2
import numpy as np


def identify_target(frame):
    """
    Scans a frame for the largest colored circular object and classifies it.

    Steps:
      1. Convert to HSV and threshold on Saturation to isolate colored objects.
      2. Clean up noise with morphological opening.
      3. Find the largest contour. Ignore if area < 500px (too small / noise).
      4. Classify shape: >7 polygon corners = circular.
      5. FIX: Sample a 10x10 region around the centroid (not a single pixel)
         and use the median hue for reliable color classification.

    Returns:
        ("BLUE_CIRCULAR",  cx)  — blue circle found, cx = horizontal center
        ("OTHER_CIRCULAR", cx)  — circle found but wrong color
        ("NON_CIRCULAR",  None) — largest object is not circular
        ("NONE",          None) — nothing detected or frame is empty
    """
    if frame is None:
        return "NONE", None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, w = frame.shape[:2]

    # --- Step 1: Isolate any colored (non-grey) area via saturation ---
    _, sat_mask = cv2.threshold(hsv[:, :, 1], 70, 255, cv2.THRESH_BINARY)

    # --- Step 2: Morphological cleanup (removes single-pixel noise) ---
    kernel = np.ones((5, 5), np.uint8)
    sat_mask = cv2.morphologyEx(sat_mask, cv2.MORPH_OPEN, kernel)

    # --- Step 3: Find contours ---
    contours, _ = cv2.findContours(
        sat_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return "NONE", None

    biggest_blob = max(contours, key=cv2.contourArea)

    if cv2.contourArea(biggest_blob) < 500:
        return "NONE", None

    # --- Step 4: Shape classification ---
    epsilon = 0.02 * cv2.arcLength(biggest_blob, True)
    approx = cv2.approxPolyDP(biggest_blob, epsilon, True)

    if len(approx) <= 7:
        return "NON_CIRCULAR", None

    # --- Step 5: Get centroid ---
    M = cv2.moments(biggest_blob)
    if M["m00"] == 0:
        return "NONE", None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    # Clamp centroid to frame bounds
    cx = max(0, min(cx, w - 1))
    cy = max(0, min(cy, h - 1))

    # --- FIX: Sample 10x10 region, use MEDIAN hue (robust against noise) ---
    region_r = 10
    x1 = max(0, cx - region_r)
    x2 = min(w, cx + region_r)
    y1 = max(0, cy - region_r)
    y2 = min(h, cy + region_r)

    region_hsv = hsv[y1:y2, x1:x2]

    # Only use pixels that are actually saturated (part of the object, not bg)
    sat_region = region_hsv[:, :, 1]
    colored_pixels = region_hsv[sat_region > 70]

    if len(colored_pixels) == 0:
        return "OTHER_CIRCULAR", cx

    median_hue = int(np.median(colored_pixels[:, 0]))

    # Blue in OpenCV HSV: hue range 100–140
    if 100 <= median_hue <= 140:
        return "BLUE_CIRCULAR", cx
    else:
        return "OTHER_CIRCULAR", cx