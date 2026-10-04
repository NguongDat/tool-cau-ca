import cv2
import numpy as np

img = cv2.imread(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\sample_backpack.png")
tpl_lock = cv2.imread(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\lock_badge.png")

# Template matching for lock badges
res = cv2.matchTemplate(img, tpl_lock, cv2.TM_CCOEFF_NORMED)
threshold = 0.70
loc = np.where(res >= threshold)

locked_points = []
for pt in zip(*loc[::-1]):
    # Check if close to an existing point
    if not any(abs(pt[0] - p[0]) < 20 and abs(pt[1] - p[1]) < 20 for p in locked_points):
        locked_points.append(pt)

print(f"Found {len(locked_points)} locked fish in backpack at coordinates: {locked_points}")
