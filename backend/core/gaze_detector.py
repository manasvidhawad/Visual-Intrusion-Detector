import math
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_LANDMARKER_MODEL = os.path.join(MODEL_DIR, "face_landmarker.task")

# Key facial landmark indices for head pose estimation
POSE_LANDMARKS = [1, 33, 263, 61, 291, 199]


def _safe_rq_decompose(rmat):
    """
    Extract Euler angles from a 3×3 rotation matrix.
    Uses cv2.RQDecomposeMatrix when available and working,
    falls back to manual Euler extraction otherwise.

    Returns (x_rot_degrees, y_rot_degrees).
    """
    try:
        angles, _, _, _, _, _ = cv2.RQDecomposeMatrix(rmat)
        return angles[0] * 360, angles[1] * 360
    except (cv2.error, AttributeError, Exception):
        pass

    try:
        sy = math.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
        if sy > 1e-6:
            x = math.atan2(rmat[2, 1], rmat[2, 2])
            y = math.atan2(-rmat[2, 0], sy)
        else:
            x = math.atan2(-rmat[1, 2], rmat[1, 1])
            y = math.atan2(-rmat[2, 0], sy)
        return math.degrees(x), math.degrees(y)
    except Exception:
        return 0.0, 0.0


class GazeDetector:
    """Detects gaze direction using head pose estimation."""

    def __init__(self):
        try:
            base_options = python.BaseOptions(
                model_asset_path=FACE_LANDMARKER_MODEL
            )
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=5,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[GazeDetector] Init error: {e}")
            self.landmarker = None

    def detect_gaze(self, frame: np.ndarray, bboxes: list = None) -> list:
        """
        Detect gaze for all faces in the frame.

        Returns:
            list of {"gaze": "at_screen"|"looking_away"|"unknown",
                      "head_pose": [x_rot, y_rot, 0]}
        """
        if frame is None or self.landmarker is None:
            return []

        try:
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.landmarker.detect(mp_image)

            gaze_results = []

            if result.face_landmarks:
                for face_lms in result.face_landmarks:
                    face_2d = []
                    face_3d = []

                    for idx in POSE_LANDMARKS:
                        lm = face_lms[idx]
                        x_px = int(lm.x * w)
                        y_px = int(lm.y * h)
                        face_2d.append([x_px, y_px])
                        face_3d.append([x_px, y_px, lm.z])

                    face_2d = np.array(face_2d, dtype=np.float64)
                    face_3d = np.array(face_3d, dtype=np.float64)

                    focal_length = w
                    cam_matrix = np.array([
                        [focal_length, 0, w / 2],
                        [0, focal_length, h / 2],
                        [0, 0, 1],
                    ], dtype=np.float64)
                    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

                    success, rot_vec, trans_vec = cv2.solvePnP(
                        face_3d, face_2d, cam_matrix, dist_coeffs
                    )

                    if not success:
                        gaze_results.append({
                            "gaze": "unknown",
                            "head_pose": [0, 0, 0],
                        })
                        continue

                    rmat, _ = cv2.Rodrigues(rot_vec)
                    x_rot, y_rot = _safe_rq_decompose(rmat)

                    if -20 < x_rot < 20 and -20 < y_rot < 20:
                        status = "at_screen"
                    else:
                        status = "looking_away"

                    gaze_results.append({
                        "gaze": status,
                        "head_pose": [round(x_rot, 1), round(y_rot, 1), 0],
                    })

            # Map to bboxes
            if bboxes:
                mapped = []
                for i, bbox in enumerate(bboxes):
                    if i < len(gaze_results):
                        mapped.append(gaze_results[i])
                    else:
                        mapped.append({"gaze": "unknown", "head_pose": [0, 0, 0]})
                return mapped

            return gaze_results

        except Exception as e:
            print(f"[GazeDetector] Error: {e}")
            return []

    def __del__(self):
        if hasattr(self, "landmarker") and self.landmarker:
            try:
                self.landmarker.close()
            except Exception:
                pass
