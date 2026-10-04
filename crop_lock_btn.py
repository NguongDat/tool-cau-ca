import cv2

top_tools = cv2.imread(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\crop_top_tools.png")
# In crop_top_tools (70x205):
# Lock button is on the left: x: 10..60, y: 10..60
lock_btn = top_tools[8:62, 12:62]
cv2.imwrite(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\lock_tool_btn.png", lock_btn)
print("lock_tool_btn.png saved!")
