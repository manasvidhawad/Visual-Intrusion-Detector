import time
import threading
from database import get_settings, add_log


# Tunable constants 
SAFE_HYSTERESIS_SECONDS  = 1.5   # consecutive threat-free time needed to clear
DEBOUNCE_SECONDS         = 1.5   # continuous threat time before countdown starts


class MonitorEngine:
    """
    Wall-clock–driven threat state machine.  Thread-safe.

    Public methods
    --------------
    process(recognition_results, gaze_results) -> dict
        Call once per AI frame.  Returns the current status payload.

    reset()
        Immediately force back to safe.  Call this when stopping monitoring.

    reload_settings()
        Re-read alert_timer / protection_mode from DB.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Persistent config 
        self.alert_timer      = 7       # seconds for countdown
        self.protection_mode  = "blur"

        # State 
        self._state = "safe"           

        # Threat clock — set ONCE, never reset while threat continues ──
        self._threat_first_seen: float = 0.0   # wall time when threat appeared
        self._threat_active: bool      = False  # is a threat currently detected?

        # Safe clock — reset to now whenever we SEE a threat frame 
        self._last_threat_time: float  = 0.0   # last frame that had a threat

        # Locked
        self._locked_logged: bool = False

        self.reload_settings()

    # Public 

    def reload_settings(self):
        try:
            settings = get_settings()
            self.alert_timer     = int(settings.get("alert_timer", "7"))
            self.protection_mode = settings.get("protection_mode", "blur")
        except Exception:
            pass

    def reset(self):
        """Immediately reset to safe — called by Stop Monitoring."""
        with self._lock:
            self._state          = "safe"
            self._threat_active  = False
            self._threat_first_seen = 0.0
            self._last_threat_time  = 0.0
            self._locked_logged  = False

    def process(self, recognition_results: list, gaze_results: list) -> dict:
        """
        Evaluate one AI frame and return the current status payload.

        This is the ONLY place state is mutated (except reset()).
        """
        with self._lock:
            now = time.monotonic()

            # Classify this frame
            faces, is_threat_frame = self._classify_frame(
                recognition_results, gaze_results
            )

            total_faces       = len(faces)
            authorized_count  = sum(1 for f in faces if f["authorized"])
            unauthorized_count = total_faces - authorized_count

            # Update threat
            if is_threat_frame:
                self._last_threat_time = now
                if not self._threat_active:
                    # First frame of a new threat — start the clock
                    self._threat_active     = True
                    self._threat_first_seen = now
                    self._locked_logged     = False
            else:
                # How long since we last saw a threat?
                gap = now - self._last_threat_time
                if self._threat_active and gap >= SAFE_HYSTERESIS_SECONDS:
                    # Threat has been gone long enough → truly cleared
                    self._clear_threat(now)

            # Compute countdown 
            countdown = 0
            if self._threat_active:
                elapsed = now - self._threat_first_seen
                if elapsed < DEBOUNCE_SECONDS:
                    countdown = self.alert_timer          # full value during debounce
                else:
                    remaining = self.alert_timer - (elapsed - DEBOUNCE_SECONDS)
                    countdown = max(0, int(remaining))    # monotonically decreasing

            # Drive state machine 
            if not self._threat_active:
                # Threat cleared
                self._state = "safe" if total_faces == 0 else "monitoring"

            else:
                # Threat active — determine phase by elapsed time
                elapsed = now - self._threat_first_seen

                if elapsed < DEBOUNCE_SECONDS:
                    # Still in debounce window — show warning but no countdown yet
                    self._state = "warning"

                elif elapsed < DEBOUNCE_SECONDS + self.alert_timer:
                    # Countdown phase
                    self._state = "countdown"

                else:
                    # Countdown expired locked
                    if self._state != "locked":
                        self._state = "locked"
                        if not self._locked_logged:
                            self._locked_logged = True
                            duration = elapsed
                            try:
                                add_log(
                                    person="Unknown Viewer",
                                    action=f"Screen {self.protection_mode}",
                                    duration=round(duration, 1),
                                    severity="critical",
                                )
                            except Exception:
                                pass

            # Build payload
            result = {
                "status":             self._state,
                "total_faces":        total_faces,
                "authorized_count":   authorized_count,
                "unauthorized_count": unauthorized_count,
                "faces":              faces,
                "countdown":          countdown,
                "action": self.protection_mode if self._state == "locked" else None,
            }

        return result

    # Internal helpers

    def _classify_frame(self, recognition_results, gaze_results):
        """
        Returns (faces_list, is_threat_frame).
        is_threat_frame = True if at least one unauthorized person is present
        (regardless of gaze direction — conservative mode).
        """
        faces = []
        is_threat = False

        for i, rec in enumerate(recognition_results):
            bbox = rec.get("bbox", [0, 0, 0, 0])
            if isinstance(bbox, dict):
                bbox = [bbox.get("x", 0), bbox.get("y", 0),
                        bbox.get("w", 0), bbox.get("h", 0)]

            gaze_info = (
                gaze_results[i]
                if i < len(gaze_results)
                else {"gaze": "unknown", "head_pose": [0, 0, 0]}
            )
            gaze_dir = (
                gaze_info.get("gaze", "unknown")
                if isinstance(gaze_info, dict) else "unknown"
            )

            authorized = rec.get("authorized", False)

            faces.append({
                "bbox":       bbox,
                "name":       rec.get("name", "Unknown"),
                "authorized": authorized,
                "gaze":       gaze_dir,
            })

            if not authorized:
                is_threat = True

        return faces, is_threat

    def _clear_threat(self, now: float):
        """Clear threat state and log restoration if we were locked."""
        if self._state == "locked":
            try:
                elapsed = now - self._threat_first_seen
                add_log(
                    person="Unknown Viewer",
                    action="Screen restored",
                    duration=round(elapsed, 1),
                    severity="info",
                )
            except Exception:
                pass

        self._threat_active     = False
        self._threat_first_seen = 0.0
        self._locked_logged     = False

   

    @property
    def state(self):
        return self._state
