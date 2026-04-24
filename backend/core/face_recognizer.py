import os
import cv2
import numpy as np
import mediapipe as mp
from collections import deque
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_LANDMARKER_MODEL = os.path.join(MODEL_DIR, "face_landmarker.task")


KEY_LANDMARK_INDICES = [
    # Nose
    1, 2, 4, 6, 168, 197, 195, 5,
    # Left eye outer/inner
    33, 133, 159, 145, 153, 144, 163, 7,
    # Right eye outer/inner
    362, 263, 386, 374, 380, 373, 390, 249,
    # Lips
    61, 291, 0, 17, 37, 267, 84, 314,
    # Jaw
    234, 454, 172, 397, 152, 148, 377,
    # Left brow
    70, 63, 105, 66, 107,
    # Right brow
    336, 296, 334, 293, 300,
    # Cheeks
    116, 345, 36, 266, 123, 352,
    # Extra nose bridge
    168, 9, 10,
]
# Deduplicate while preserving order
_seen = set()
KEY_LANDMARK_INDICES = [
    x for x in KEY_LANDMARK_INDICES if not (x in _seen or _seen.add(x))
]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors. Returns value in [0, 1]."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class FaceRecognizer:
    """
    Face recognition using geometric face signatures + cosine similarity.

    Key parameters:
      tolerance: cosine similarity threshold (0 to 1).
                 Higher = stricter match required.
                 0.82 is the sweet-spot: rarely mismatches strangers,
                 reliably recognizes the registered user.
    """

    def __init__(self, tolerance: float = 0.82):
        self.tolerance = tolerance

        try:
            base_options = python.BaseOptions(
                model_asset_path=FACE_LANDMARKER_MODEL
            )
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=5,
                min_face_detection_confidence=0.45,
                min_face_presence_confidence=0.45,
                min_tracking_confidence=0.45,
            )
            self.landmarker = vision.FaceLandmarker.create_from_options(options)
            print("[FaceRecognizer] FaceLandmarker initialized OK")
        except Exception as e:
            print(f"[FaceRecognizer] Init error: {e}")
            self.landmarker = None

        self.known_signatures = []
        self.known_names = []
        self.reload_users()

        # Temporal smoothing: track last N results per face (center-based tracking)

        self._face_history = {}
        self._history_window = 4         # how many frames to keep per face
        self._confirm_unknown_after = 3  # consecutive Unknown frames needed to flip

    #  Database 

    def reload_users(self):
        """Reload authorized user signatures from database."""
        try:
            from database import get_user_encodings
            users = get_user_encodings()
            self.known_signatures = [u["encoding"] for u in users]
            self.known_names = [u["name"] for u in users]
            print(f"[FaceRecognizer] Loaded {len(self.known_names)} authorized user(s)")
            for i, name in enumerate(self.known_names):
                print(f"  User {i}: {name}  sig_shape={self.known_signatures[i].shape}  "
                      f"sig_norm={np.linalg.norm(self.known_signatures[i]):.4f}")
        except Exception as e:
            print(f"[FaceRecognizer] Failed to reload users: {e}")

    # Signature computation

    def _compute_signature(self, landmarks) -> np.ndarray:
        """
        Compute a face signature vector from FaceLandmarker landmarks.

        Steps:
          1. Extract [x, y] for all 478 landmarks (skip Z — it's noisy)
          2. Translate so nose-tip (landmark 1) is origin
          3. Scale by inter-eye distance (landmarks 33 ↔ 263)
          4. Select key landmarks and flatten
          5. L2-normalize the final vector

        Returns:
          Unit-normalised 1D numpy array of shape (N*2,), or None on failure.
        """
        try:
            # Only use x, y
            points = np.array([[lm.x, lm.y] for lm in landmarks], dtype=np.float32)  # (478, 2)

            # Translate: nose tip as origin
            nose_tip = points[1].copy()
            points -= nose_tip

            # Scale: inter-eye distance
            eye_dist = np.linalg.norm(points[33] - points[263])
            if eye_dist < 1e-6:
                return None
            points /= eye_dist

            # Select key landmarks
            selected = points[KEY_LANDMARK_INDICES].flatten()  # (N*2,)

            # L2 normalize → cosine similarity works correctly
            norm = np.linalg.norm(selected)
            if norm < 1e-9:
                return None

            return (selected / norm).astype(np.float64)

        except Exception as e:
            print(f"[FaceRecognizer] _compute_signature error: {e}")
            return None

    # Registration (encode_face)

    def encode_face(self, frame: np.ndarray, bbox=None) -> np.ndarray:
        """
        Generate a robust face signature from a single frame.

        Runs the landmarker up to 5 times on slightly varied crops
        and averages the signatures for a stable embedding.

        Returns:
            Averaged, L2-normalised signature vector, or None if no face found.
        """
        if frame is None or self.landmarker is None:
            return None

        signatures = []

        for attempt in range(5):
            try:
                # Slight random brightness jitter for robustness
                jitter = frame.copy()
                if attempt > 0:
                    delta = np.random.randint(-10, 10)
                    jitter = np.clip(jitter.astype(np.int16) + delta, 0, 255).astype(np.uint8)

                rgb = cv2.cvtColor(jitter, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = self.landmarker.detect(mp_image)

                if not result.face_landmarks:
                    continue

                sig = self._compute_signature(result.face_landmarks[0])
                if sig is not None:
                    signatures.append(sig)

            except Exception as e:
                print(f"[FaceRecognizer] encode_face attempt {attempt} error: {e}")

        if not signatures:
            print("[FaceRecognizer] encode_face: no face detected in frame")
            return None

        # Average signatures and re-normalize
        avg_sig = np.mean(signatures, axis=0)
        norm = np.linalg.norm(avg_sig)
        if norm < 1e-9:
            return None

        final = (avg_sig / norm).astype(np.float64)
        print(f"[FaceRecognizer] encode_face: computed from {len(signatures)} samples, "
              f"shape={final.shape}, norm={np.linalg.norm(final):.4f}")
        return final

    # Live Recognition

    def recognize(self, frame: np.ndarray, bboxes: list) -> list:
        """
        Recognize all faces detected in a frame.

        For each face bbox, finds the matching FaceLandmarker detection,
        computes its signature, and compares against all known users
        using COSINE SIMILARITY.

        Returns:
            list of {"bbox", "name", "authorized", "similarity", "user_id"}
        """
        if not bboxes or self.landmarker is None:
            return []

        try:
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.landmarker.detect(mp_image)

            signatures = []
            landmark_centers = []

            if result.face_landmarks:
                for face_lms in result.face_landmarks:
                    sig = self._compute_signature(face_lms)
                    if sig is not None:
                        signatures.append(sig)
                        nose = face_lms[1]
                        landmark_centers.append([nose.x * w, nose.y * h])

            results = []
            for bbox_dict in bboxes:
                # Normalize bbox input format
                if isinstance(bbox_dict, dict):
                    bbox = bbox_dict.get("bbox", [0, 0, 0, 0])
                else:
                    bbox = bbox_dict
                if isinstance(bbox, dict):
                    bbox = [bbox.get("x", 0), bbox.get("y", 0),
                            bbox.get("w", 0), bbox.get("h", 0)]

                bx, by, bw, bh = bbox
                bc = np.array([bx + bw / 2.0, by + bh / 2.0])

                name = "Unknown"
                authorized = False
                best_similarity = 0.0

                # Step 1: Find closest landmark face to this bbox
                best_sig = None
                min_center_dist = float("inf")
                search_radius = max(bw, bh, 80) * 1.5  # generous match radius

                for i, lc in enumerate(landmark_centers):
                    dist = np.linalg.norm(bc - np.array(lc))
                    if dist < min_center_dist and dist < search_radius:
                        min_center_dist = dist
                        best_sig = signatures[i]

                # Step 2: Compare against enrolled users 
                if best_sig is not None and self.known_signatures:
                    similarities = [
                        _cosine_similarity(best_sig, ks)
                        for ks in self.known_signatures
                    ]
                    max_sim = max(similarities)
                    best_similarity = max_sim

                    print(f"[FaceRecognizer] Face at {bc}: "
                          f"best_similarity={max_sim:.4f} threshold={self.tolerance}")

                    if max_sim >= self.tolerance:
                        idx = similarities.index(max_sim)
                        name = self.known_names[idx]
                        authorized = True

                results.append({
                    "bbox": bbox,
                    "name": name,
                    "authorized": authorized,
                    "similarity": round(best_similarity, 4),
                    "user_id": None,
                })

            
            active_track_ids = set()
            for r in results:
                bx, by, bw, bh = r["bbox"]
                face_center = np.array([bx + bw / 2.0, by + bh / 2.0])

                # Find the closest existing track by center distance
                best_track_id = None
                best_dist = float("inf")
                merge_radius = max(bw, bh, 80) * 0.8
                for tid, tdata in self._face_history.items():
                    dist = np.linalg.norm(face_center - tdata["center"])
                    if dist < best_dist and dist < merge_radius:
                        best_dist = dist
                        best_track_id = tid

                if best_track_id is None:
                    # New track
                    best_track_id = id(r)  # unique ID for this result
                    self._face_history[best_track_id] = {
                        "center": face_center,
                        "history": deque(maxlen=self._history_window),
                    }

                track = self._face_history[best_track_id]
                track["center"] = face_center  # update position
                track["history"].append(r["authorized"])
                active_track_ids.add(best_track_id)

                history = track["history"]

                if not r["authorized"] and len(history) >= 2:
                    # Count how many of the PREVIOUS frames
                    # were authorized. Only suppress the Unknown if the face was
                    # consistently authorized before (i.e., this is likely a
                    # single-frame recognition glitch, not a new person).
                    prev_frames = list(history)[:-1]  # everything except current
                    prev_authorized_count = sum(1 for v in prev_frames if v)

                    if prev_authorized_count == len(prev_frames):
                        # ALL previous frames were authorized → likely a glitch
                        consecutive_unknown = sum(
                            1 for v in history if not v
                        )
                        if consecutive_unknown < self._confirm_unknown_after:
                            r["authorized"] = True
                            r["name"] = (
                                self.known_names[0]
                                if self.known_names
                                else "Unknown"
                            )
                    # else: previous frames had Unknown → this is genuinely unknown

            # Prune tracks for faces no longer in the frame
            stale = [k for k in self._face_history if k not in active_track_ids]
            for k in stale:
                del self._face_history[k]

            return results

        except Exception as e:
            print(f"[FaceRecognizer] Recognition error: {e}")
            return [
                {
                    "bbox": (b if isinstance(b, list) else b.get("bbox", [0, 0, 0, 0])),
                    "name": "Unknown",
                    "authorized": False,
                    "similarity": 0.0,
                    "user_id": None,
                }
                for b in bboxes
            ]

    def __del__(self):
        if hasattr(self, "landmarker") and self.landmarker:
            try:
                self.landmarker.close()
            except Exception:
                pass
