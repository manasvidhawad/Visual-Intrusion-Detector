import cv2
try:
    print(f"OpenCV Version: {cv2.__version__}")
    print(f"Has RQDecomposeMatrix: {hasattr(cv2, 'RQDecomposeMatrix')}")
except Exception as e:
    print(f"Error: {e}")
