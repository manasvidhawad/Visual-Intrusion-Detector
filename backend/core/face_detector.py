
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Model path relative to this file
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_DETECTOR_MODEL = os.path.join(MODEL_DIR, "blaze_face_short_range.tflite")


class FaceDetector:
    """Fast multi-face detector with bbox smoothing."""

    def __init__(self, min_confidence: float = 0.5):
        try:
            base_options = python.BaseOptions(
                model_asset_path=FACE_DETECTOR_MODEL
            )
            options = vision.FaceDetectorOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                min_detection_confidence=min_confidence,
            )
            self.detector = vision.FaceDetector.create_from_options(options)
        except Exception as e:
            print(f"[FaceDetector] Init error: {e}")
            self.detector = None

        # Smoothing parameters
        self._smooth_alpha = 0.4
        self._tracked_faces = []
        self._max_missed = 8
        self._match_threshold = 150

    def detect(self, frame: np.ndarray) -> list:
        """
        Detect faces in a BGR frame.

        Returns:
            list of dicts: [{"bbox": [x, y, w, h], "confidence": float}, ...]
        """
        if self.detector is None or frame is None:
            return []

        try:
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            result = self.detector.detect(mp_image)

            raw_faces = []
            if result and result.detections:
                for det in result.detections:
                    bb = det.bounding_box
                    x = max(0, bb.origin_x)
                    y = max(0, bb.origin_y)
                    bw = min(bb.width, w - x)
                    bh = min(bb.height, h - y)
                    conf = det.categories[0].score if det.categories else 0.5
                    raw_faces.append({
                        "bbox": [int(x), int(y), int(bw), int(bh)],
                        "confidence": round(float(conf), 3),
                    })

            return self._smooth_faces(raw_faces)

        except Exception as e:
            print(f"[FaceDetector] Detection error: {e}")
            return []

    # Smoothing internals 

    def _bbox_center(self, bbox):
        return (bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2)

    def _bbox_distance(self, bbox1, bbox2):
        c1 = self._bbox_center(bbox1)
        c2 = self._bbox_center(bbox2)
        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5

    def _smooth_faces(self, raw_faces: list) -> list:
        """Apply EMA smoothing with distance-based tracking."""
        alpha = self._smooth_alpha
        used_raw = set()
        used_track = set()

        matches = []
        for ti, track in enumerate(self._tracked_faces):
            best_dist = self._match_threshold
            best_ri = -1
            for ri, raw in enumerate(raw_faces):
                if ri in used_raw:
                    continue
                dist = self._bbox_distance(track["bbox"], raw["bbox"])
                if dist < best_dist:
                    best_dist = dist
                    best_ri = ri
            if best_ri >= 0:
                matches.append((ti, best_ri))
                used_raw.add(best_ri)
                used_track.add(ti)

        for ti, ri in matches:
            track = self._tracked_faces[ti]
            rb = raw_faces[ri]["bbox"]
            sb = track["bbox"]
            track["bbox"] = [
                int(sb[0] + alpha * (rb[0] - sb[0])),
                int(sb[1] + alpha * (rb[1] - sb[1])),
                int(sb[2] + alpha * (rb[2] - sb[2])),
                int(sb[3] + alpha * (rb[3] - sb[3])),
            ]
            track["confidence"] = raw_faces[ri]["confidence"]
            track["missed"] = 0
            track["age"] += 1

        for ti, track in enumerate(self._tracked_faces):
            if ti not in used_track:
                track["missed"] += 1

        for ri, raw in enumerate(raw_faces):
            if ri not in used_raw:
                self._tracked_faces.append({
                    "bbox": list(raw["bbox"]),
                    "confidence": raw["confidence"],
                    "missed": 0,
                    "age": 1,
                })

        self._tracked_faces = [
            t for t in self._tracked_faces if t["missed"] <= self._max_missed
        ]

        return [
            {"bbox": list(t["bbox"]), "confidence": t["confidence"]}
            for t in self._tracked_faces
            if t["missed"] == 0
        ]

    def close(self):
        if self.detector:
            try:
                self.detector.close()
            except Exception:
                pass
