import os
import cv2
import shutil

src_dir = r"C:\Users\ASUS\.gemini\antigravity-ide\brain\963d5f6b-23bc-45f1-a16f-da6cab70ad70\.user_uploaded"
out_dir = r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates"
os.makedirs(out_dir, exist_ok=True)

# 1. Copy full images for reference
shutil.copy(os.path.join(src_dir, "media_1790852832140.png"), os.path.join(out_dir, "sample_bosses.png"))
shutil.copy(os.path.join(src_dir, "media_1790852954949.png"), os.path.join(out_dir, "sample_backpack.png"))

# 2. Inspect Backpack image
backpack = cv2.imread(os.path.join(out_dir, "sample_backpack.png"))
bh, bw = backpack.shape[:2]
print(f"Backpack image shape: {bw}x{bh}")

# Crop the Lock button at the top header (next to Search for items)
# In 1024x512 approx, header is top ~80px, lock is around x=580..620
# Let's crop the top toolbar area to find lock button
top_tools = backpack[0:70, int(bw*0.55):int(bw*0.75)]
cv2.imwrite(os.path.join(out_dir, "crop_top_tools.png"), top_tools)

# Crop the blue padlock badge on the locked fish (Fish 1: Dragon Koi, Fish 2: Kun Version 2)
# First fish icon is around x=70..180, y=90..230
fish1_crop = backpack[80:230, 60:190]
cv2.imwrite(os.path.join(out_dir, "crop_fish1.png"), fish1_crop)

# Let's extract the blue padlock badge:
# The padlock badge is centered on the locked fish
# In fish1_crop (150x130), padlock is roughly at y=40..100, x=35..95
padlock_crop = fish1_crop[35:105, 35:95]
cv2.imwrite(os.path.join(out_dir, "lock_badge.png"), padlock_crop)

# 3. Inspect Bosses image
bosses = cv2.imread(os.path.join(out_dir, "sample_bosses.png"))
bosh, bosw = bosses.shape[:2]
print(f"Bosses image shape: {bosw}x{bosh}")

# Crop Islands list (left side: x: 10..270, y: 30..450)
islands_crop = bosses[30:450, 10:270]
cv2.imwrite(os.path.join(out_dir, "crop_islands.png"), islands_crop)

print("Extraction of boss and backpack components finished.")
