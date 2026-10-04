"""
Roblox Fishing Master Automation Tool
Main Entry Point
"""
import sys
import os

# Ensure current folder is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import FishingBotGUI

def main():
    print("==================================================")
    print("  Roblox Fishing Master Auto Pro Starting...     ")
    print("  Hotkeys:                                       ")
    print("    [ F6 ] : Bật / Tắt Tự Động Câu               ")
    print("    [ F7 ] : Ném Cần & Sạc Lực (Auto Cast)       ")
    print("==================================================")
    
    app = FishingBotGUI()
    app.mainloop()

if __name__ == '__main__':
    main()
