import base64
import cv2
import threading
import time
from database import get_settings, add_log


class BackgroundMonitor:
    """Continuous background webcam monitoring with AI processing."""

    def __init__(
        self, face_detector, face_recognizer, gaze_detector,
        monitor_engine, desktop_notifier=None,
    ):
        self.face_detector   = face_detector
        self.face_recognizer = face_recognizer
        self.gaze_detector   = gaze_detector
        self.monitor_engine  = monitor_engine
        self.desktop_notifier = desktop_notifier

        self.cap  = None
        self.running = False
        self.thread  = None

        self._lock            = threading.Lock()
        self._latest_frame    = None
        self._latest_frame_b64 = None
        self._latest_result   = None

        # Fixed camera resolution
        self.FRAME_WIDTH  = 640
        self.FRAME_HEIGHT = 480

        self._process_every_n = 2

        self._warning_toast_sent = False

    # Lifecycle 

    def start(self):
        """Open the camera and start the monitoring thread."""
        if self.running:
            return

        settings = get_settings()
        camera_index = int(settings.get("camera_index", "0"))

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"[BackgroundMonitor] ERROR: Cannot open camera {camera_index}")
            return

        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_AUTOFOCUS,    0)
        cap.set(cv2.CAP_PROP_FOCUS,        0)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        cap.set(cv2.CAP_PROP_AUTO_WB,      0)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        # Discard warm-up frames
        for _ in range(5):
            cap.read()

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        print(f"[BackgroundMonitor] Camera: {w}x{h} @ {fps}fps")

        self.cap = cap
        self.running = True
        self.thread = threading.Thread(
            target=self._loop, daemon=True, name="BGMonitor"
        )
        self.thread.start()

    def stop(self):
        """
        Stop monitoring immediately.
        Resets engine state and hides all alerts synchronously.
        This must NEVER be blocked by the AI loop.
        """
        self.running = False

        # Give the loop thread up to 2 s to exit cleanly
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        if self.cap:
            self.cap.release()
            self.cap = None

        # Force-reset engine state 
        self.monitor_engine.reset()

        # Force-hide all alerts 
        if self.desktop_notifier:
            self.desktop_notifier.hide_alert()

        # Reset toast dedup flag so next session fires fresh
        self._warning_toast_sent = False

        # Clear cached results so the frontend goes back to idle
        with self._lock:
            self._latest_result = None

        print("[BackgroundMonitor] Stopped.")

    # Main Loop 

    def _loop(self):
        frame_count = 0

        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Ensure consistent frame dimensions
            fh, fw = frame.shape[:2]
            if fw != self.FRAME_WIDTH or fh != self.FRAME_HEIGHT:
                frame = cv2.resize(
                    frame, (self.FRAME_WIDTH, self.FRAME_HEIGHT),
                    interpolation=cv2.INTER_LINEAR,
                )

            frame_count += 1

            # Always encode the frame for streaming
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            b64 = base64.b64encode(buf).decode("utf-8")

            with self._lock:
                self._latest_frame     = frame
                self._latest_frame_b64 = b64

            if frame_count % self._process_every_n != 0:
                time.sleep(0.008)
                continue

            self._run_ai(frame)

    def _run_ai(self, frame):
        """Run the full AI pipeline and update alerts."""
        try:
            # 1. Face detection
            face_bboxes = self.face_detector.detect(frame)

            # 2. Recognition + gaze 
            if face_bboxes:
                recognition_results = self.face_recognizer.recognize(frame, face_bboxes)
                gaze_results        = self.gaze_detector.detect_gaze(frame, face_bboxes)
            else:
                recognition_results = []
                gaze_results        = []

            # 3. Feed into engine 
            result = self.monitor_engine.process(recognition_results, gaze_results)
            result["type"] = "detection_result"

            with self._lock:
                self._latest_result = result

            # 4. Trigger 
            self._handle_alerts(result)

        except Exception as e:
            import traceback
            print(f"[BackgroundMonitor] AI error: {e}")
            traceback.print_exc()

    def _handle_alerts(self, result: dict):
        """Drive the desktop notifier based on engine state."""
        if not self.desktop_notifier:
            return

        status    = result.get("status", "safe")
        countdown = result.get("countdown", 0)

        if status == "warning":
            msg = "Unauthorized Viewer Detected — monitoring threat..."
            self.desktop_notifier.show_alert(message=msg, countdown=countdown)
            # Only send toast once when first entering warning (not every frame)
            if not self._warning_toast_sent:
                self._warning_toast_sent = True
                self.desktop_notifier.send_toast(
                    "Privacy Guard Alert",
                    "An unauthorized person is viewing your screen!",
                )

        elif status == "countdown":
            msg = f"Unauthorized Viewer! Screen protection activates in {countdown}s"
            self.desktop_notifier.show_alert(message=msg, countdown=countdown)
            self._warning_toast_sent = True 

        elif status == "locked":
            msg = "SCREEN PROTECTED — Unauthorized viewer blocked your screen!"
            self.desktop_notifier.show_alert(message=msg, countdown=0)
            # Workstation lock escalation
            if self.desktop_notifier.check_escalation():
                action = result.get("action", "blur")
                if action == "lock":
                    print("[BackgroundMonitor] Locking workstation.")
                    self.desktop_notifier.lock_workstation()

        else:
            # safe or monitoring 
            self._warning_toast_sent = False
            self.desktop_notifier.hide_alert()

    # Thread-safe accessors 

    def get_latest_frame(self):
        with self._lock:
            return self._latest_frame

    def get_latest_frame_base64(self):
        with self._lock:
            return self._latest_frame_b64

    def get_latest_result(self):
        with self._lock:
            return self._latest_result
