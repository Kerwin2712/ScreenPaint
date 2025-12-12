
try:
    import cv2
    print("cv2: OK")
except ImportError:
    print("cv2: MISSING")

try:
    import numpy
    print("numpy: OK")
except ImportError:
    print("numpy: MISSING")

try:
    import mss
    print("mss: OK")
except ImportError:
    print("mss: MISSING")

try:
    import pyautogui
    print("pyautogui: OK")
except ImportError:
    print("pyautogui: MISSING")
