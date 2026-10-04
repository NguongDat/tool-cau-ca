import cv2
import numpy as np

badge = cv2.imread(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\lock_badge.png")
# badge shape: 70x60
# Padlock has silver/cyan metallic color:
# H: 90..120, S: 20..100, V: 150..255 (grayish blue)
# Or let's crop just the center shackle and body
pure_lock = badge[10:60, 10:52]
cv2.imwrite(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\lock_pure.png", pure_lock)

backpack = cv2.imread(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\sample_backpack.png")
res = cv2.matchTemplate(backpack, pure_lock, cv2.TM_CCOEFF_NORMED)
loc = np.where(res >= 0.65)
pts = []
for pt in zip(*loc[::-1]):
    if not any(abs(pt[0] - p[0]) < 25 and abs(pt[1] - p[1]) < 25 for p in pts):
        pts.append(pt)

print(f"Found {len(pts)} locked fish with pure lock: {pts}")
