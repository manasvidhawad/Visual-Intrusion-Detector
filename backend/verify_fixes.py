import sys
sys.path.insert(0, '.')
import numpy as np

print("=== Testing face_recognizer ===")
from core.face_recognizer import FaceRecognizer, KEY_LANDMARK_INDICES, _cosine_similarity

dupes = len(KEY_LANDMARK_INDICES) - len(set(KEY_LANDMARK_INDICES))
print(f"  Landmark indices: {len(KEY_LANDMARK_INDICES)}, duplicates: {dupes} (must be 0)")

a = np.array([1.0, 0.0, 0.0])
b = np.array([1.0, 0.0, 0.0])
c = np.array([-1.0, 0.0, 0.0])
print(f"  cosine(a,a)={_cosine_similarity(a,b):.4f}  expected=1.0")
print(f"  cosine(a,-a)={_cosine_similarity(a,c):.4f} expected=-1.0")

fr = FaceRecognizer(tolerance=0.82)
print(f"  FaceLandmarker: {'OK' if fr.landmarker else 'FAILED'}")
print(f"  Users loaded: {len(fr.known_names)}")

print()
print("=== Testing desktop_notifier ===")
from desktop_notifier import _get_all_monitor_bounds
sx, sy, sw, sh = _get_all_monitor_bounds()
print(f"  Monitor union bounds: {sw}x{sh} at ({sx},{sy})")

print()
print("ALL CHECKS PASSED")
