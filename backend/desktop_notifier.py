import ctypes
import ctypes.wintypes
import threading
import time
import tkinter as tk

HWND_TOPMOST  = -1
SWP_NOMOVE    = 0x0002
SWP_NOSIZE    = 0x0001
SWP_SHOWWINDOW = 0x0040
SWP_NOACTIVATE = 0x0010

GWL_EXSTYLE   = -20
WS_EX_LAYERED  = 0x00080000
WS_EX_TRANSPARENT = 0x00000020   # NOT used — shield should block clicks
WS_EX_TOOLWINDOW  = 0x00000080   # hide from Alt+Tab
WS_EX_TOPMOST     = 0x00000008


def _set_topmost_no_focus(hwnd):
    """Force window to topmost via Win32 without stealing keyboard focus."""
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE,
    )


def _get_all_monitor_bounds():
    """
    Return the union bounding rect of ALL connected monitors.
    Falls back to primary screen size on error.
    """
    try:
        monitors = []

        def _callback(hmon, hdc, lprect, lparam):
            r = lprect.contents
            monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
            return 1

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_ulong, ctypes.c_ulong,
            ctypes.POINTER(ctypes.wintypes.RECT),
            ctypes.c_double,
        )
        cb = MonitorEnumProc(_callback)
        ctypes.windll.user32.EnumDisplayMonitors(None, None, cb, 0)

        if monitors:
            min_x = min(m[0] for m in monitors)
            min_y = min(m[1] for m in monitors)
            max_x = max(m[0] + m[2] for m in monitors)
            max_y = max(m[1] + m[3] for m in monitors)
            return min_x, min_y, max_x - min_x, max_y - min_y
    except Exception:
        pass

    # fallback
    user32 = ctypes.windll.user32
    w = user32.GetSystemMetrics(78) 
    h = user32.GetSystemMetrics(79)   
    x = user32.GetSystemMetrics(76)  
    y = user32.GetSystemMetrics(77)   
    return x, y, w, h


class DesktopNotifier:
    """
    Manages system-wide intrusion alerts + full-screen privacy shield.
    Runs entirely on a dedicated Tkinter daemon thread.
    """

    def __init__(self):
        self._root = None
        self._popup = None           # small alert banner
        self._shield = None          # full-screen privacy overlay
        self._thread = None
        self._running = False
        self._lock = threading.Lock()
        self._ready = threading.Event()

        # Cooldown timestamps
        self._last_toast_time = 0.0
        self.cooldown_seconds = 5.0
        self.escalation_seconds = 10.0

        self._threat_start_time = None
        self._threat_active = False
        self._escalated = False

        self.sound_enabled = True
        self._last_sound_time = 0.0
        self._sound_cooldown = 3.0

        # Thread-safe flags 
        self._pending_show   = False
        self._pending_hide   = False
        self._pending_message    = ""
        self._pending_countdown  = 0

        self._popup_is_visible  = False
        self._shield_is_visible = False

        # Tk widget refs
        self._msg_label       = None
        self._countdown_label = None
        self._pulse_state     = 0

    # Lifecycle 

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._tk_loop, daemon=True, name="DesktopNotifier"
        )
        self._thread.start()
        self._ready.wait(timeout=5.0)
        print("[DesktopNotifier] Started — full-screen shield + popup alerts enabled.")

    def stop(self):
        self._running = False
        try:
            if self._root:
                self._root.quit()
        except Exception:
            pass

    # Public API — called from monitoring thread 

    def show_alert(self, message: str = "Unauthorized Viewer Detected!", countdown: int = 0):
        """Show (or refresh) the alert banner AND the full-screen shield."""
        now = time.time()

        with self._lock:
            if not self._threat_active:
                self._threat_active = True
                self._threat_start_time = now
                self._escalated = False

            self._pending_message   = message
            self._pending_countdown = countdown

        self._pending_show = True

        # Sound 
        if self.sound_enabled and (now - self._last_sound_time >= self._sound_cooldown):
            self._last_sound_time = now
            self._play_alert_sound()

    def hide_alert(self):
        """Dismiss both the alert banner and the full-screen shield."""
        with self._lock:
            self._threat_active     = False
            self._threat_start_time = None
            self._escalated         = False
        self._pending_hide = True

    def check_escalation(self) -> bool:
        with self._lock:
            if not self._threat_active or self._escalated:
                return False
            if self._threat_start_time is None:
                return False
            if time.time() - self._threat_start_time >= self.escalation_seconds:
                self._escalated = True
                return True
        return False

    def lock_workstation(self):
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"[DesktopNotifier] Lock error: {e}")

    def send_toast(self, title: str, message: str):
        now = time.time()
        with self._lock:
            if now - self._last_toast_time < self.cooldown_seconds:
                return
            self._last_toast_time = now

        def _toast():
            try:
                from winotify import Notification, audio
                toast = Notification(
                    app_id="Privacy Guard AI",
                    title=title,
                    msg=message,
                    duration="short",
                )
                toast.set_audio(audio.Mail, loop=False)
                toast.show()
            except ImportError:
                try:
                    from plyer import notification
                    notification.notify(title=title, message=message,
                                        timeout=5, app_name="Privacy Guard AI")
                except Exception:
                    pass
            except Exception as e:
                print(f"[DesktopNotifier] Toast error: {e}")

        threading.Thread(target=_toast, daemon=True).start()

    # Sound 

    def _play_alert_sound(self):
        def _sound():
            try:
                import winsound
                winsound.PlaySound("SystemExclamation",
                                   winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass
        threading.Thread(target=_sound, daemon=True).start()

    # Tkinter thread

    def _tk_loop(self):
        try:
            self._root = tk.Tk()
            self._root.withdraw()
            self._root.overrideredirect(True)
            self._root.attributes("-alpha", 0)

            self._ready.set()
            self._poll()
            self._root.mainloop()
        except Exception as e:
            print(f"[DesktopNotifier] Tk loop error: {e}")
        finally:
            self._ready.set()

    def _poll(self):
        """Called every 150 ms from the Tk event loop to process flags."""
        if not self._running:
            self._do_hide_all()
            return

        try:
            if self._pending_hide:
                self._pending_hide = False
                self._pending_show = False
                self._do_hide_all()

            elif self._pending_show:
                self._pending_show = False
                self._do_show_shield(self._pending_message)
                self._do_show_popup(self._pending_message, self._pending_countdown)

            # Live-update text while visible
            if self._popup_is_visible and self._popup:
                msg = self._pending_message
                cd  = self._pending_countdown
                try:
                    if self._msg_label:
                        self._msg_label.config(text=msg)
                    if self._countdown_label:
                        self._countdown_label.config(
                            text=f"Screen will protect in {cd}s" if cd > 0
                            else "Threat active — protecting screen..."
                        )
                except Exception:
                    pass

        except Exception as e:
            print(f"[DesktopNotifier] Poll error: {e}")

        if self._root and self._running:
            self._root.after(150, self._poll)

    # Full-Screen Privacy Shield

    def _do_show_shield(self, message: str):
        """Create or update the full-screen privacy overlay on ALL monitors."""
        if self._shield_is_visible and self._shield:
            return  
        try:
            sx, sy, sw, sh = _get_all_monitor_bounds()

            shield = tk.Toplevel(self._root)
            shield.overrideredirect(True)
            shield.attributes("-topmost", True)

            # Semi-transparent dark overlay (alpha 0.88)
            shield.attributes("-alpha", 0.88)
            shield.configure(bg="#06060e")
            shield.geometry(f"{sw}x{sh}+{sx}+{sy}")

            # Shield content 
            container = tk.Frame(shield, bg="#06060e")
            container.place(relx=0.5, rely=0.5, anchor="center")

            # Big warning icon
            tk.Label(
                container, text="⚠",
                font=("Segoe UI Emoji", 72), bg="#06060e", fg="#ef4444",
            ).pack(pady=(0, 16))

            # Title
            tk.Label(
                container,
                text="PRIVACY SHIELD ACTIVE",
                font=("Segoe UI", 32, "bold"),
                bg="#06060e", fg="#ef4444",
            ).pack(pady=(0, 12))

            # Red divider
            tk.Frame(container, bg="#ef4444", height=2, width=480).pack(pady=(0, 16))

            # Sub-message
            tk.Label(
                container,
                text="Unauthorized viewer detected.\nYour screen is protected.",
                font=("Segoe UI", 16),
                bg="#06060e", fg="#ccccdd",
                justify="center",
            ).pack(pady=(0, 20))

            # Hint
            tk.Label(
                container,
                text="Shield removes automatically when threat is gone.",
                font=("Segoe UI", 11),
                bg="#06060e", fg="#555577",
            ).pack()

            self._shield = shield
            self._shield_is_visible = True

            shield.update_idletasks()
            try:
                hwnd = shield.winfo_id()
                _set_topmost_no_focus(hwnd)

                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE,
                    style | WS_EX_LAYERED | WS_EX_TOOLWINDOW,
                )
            except Exception:
                pass

            self._keep_shield_on_top()
            print(f"[DesktopNotifier] Privacy shield UP — covering {sw}x{sh} at ({sx},{sy})")

        except Exception as e:
            print(f"[DesktopNotifier] Shield creation error: {e}")

    def _keep_shield_on_top(self):
        """Re-raise the shield every 1.5 s so it stays above new windows."""
        if not self._shield_is_visible or not self._shield or not self._running:
            return
        try:
            self._shield.lift()
            self._shield.attributes("-topmost", True)
            hwnd = self._shield.winfo_id()
            _set_topmost_no_focus(hwnd)
        except Exception:
            pass
        if self._root and self._running and self._shield_is_visible:
            self._root.after(1500, self._keep_shield_on_top)

    def _do_hide_shield(self):
        if self._shield:
            try:
                self._shield.destroy()
            except Exception:
                pass
            self._shield = None
        self._shield_is_visible = False
        print("[DesktopNotifier] Privacy shield removed.")

    # Alert Banner Popup

    def _do_show_popup(self, message: str, countdown: int):
        """Create the small top-center alert banner."""
        if self._popup_is_visible and self._popup:
            try:
                if self._msg_label:
                    self._msg_label.config(text=message)
            except Exception:
                pass
            return

        try:
            popup = tk.Toplevel(self._root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.attributes("-alpha", 0.97)
            popup.configure(bg="#0d0d1a")

            screen_w = popup.winfo_screenwidth()
            pw, ph = 600, 220
            x = (screen_w - pw) // 2
            y = 20
            popup.geometry(f"{pw}x{ph}+{x}+{y}")

            # Outer red border frame
            border = tk.Frame(popup, bg="#e74c3c", padx=3, pady=3)
            border.pack(fill="both", expand=True, padx=2, pady=2)

            inner = tk.Frame(border, bg="#0d0d1a")
            inner.pack(fill="both", expand=True)

            # Top red accent bar
            tk.Frame(inner, bg="#e74c3c", height=5).pack(fill="x", side="top")

            # Header row
            hdr = tk.Frame(inner, bg="#0d0d1a")
            hdr.pack(pady=(14, 4))

            tk.Label(
                hdr, text="⚠", font=("Segoe UI Emoji", 22),
                bg="#0d0d1a", fg="#e74c3c",
            ).pack(side="left", padx=(0, 10))

            tk.Label(
                hdr, text="SECURITY ALERT — UNAUTHORIZED VIEWER",
                font=("Segoe UI", 14, "bold"),
                bg="#0d0d1a", fg="#e74c3c",
            ).pack(side="left")

            tk.Frame(inner, bg="#2a2a4a", height=1).pack(fill="x", padx=20, pady=(6, 4))

            self._msg_label = tk.Label(
                inner, text=message,
                font=("Segoe UI", 11), bg="#0d0d1a", fg="#ffffff",
                wraplength=550,
            )
            self._msg_label.pack(pady=(6, 2))

            cd_text = (f"Screen will protect in {countdown}s"
                       if countdown > 0 else "Threat active — protecting screen...")
            self._countdown_label = tk.Label(
                inner, text=cd_text,
                font=("Segoe UI", 10, "bold"), bg="#0d0d1a", fg="#f39c12",
            )
            self._countdown_label.pack(pady=(2, 4))

            tk.Label(
                inner,
                text="Privacy shield is covering all displays.",
                font=("Segoe UI", 9), bg="#0d0d1a", fg="#555577",
            ).pack(pady=(0, 10))

            self._popup = popup
            self._popup_is_visible = True

            popup.update_idletasks()
            try:
                hwnd = popup.winfo_id()
                _set_topmost_no_focus(hwnd)
            except Exception:
                pass

            self._keep_popup_on_top()
            self._pulse_border()

            print("[DesktopNotifier] Alert popup shown.")

        except Exception as e:
            print(f"[DesktopNotifier] Popup creation error: {e}")

    def _keep_popup_on_top(self):
        if not self._popup_is_visible or not self._popup or not self._running:
            return
        try:
            self._popup.lift()
            self._popup.attributes("-topmost", True)
            _set_topmost_no_focus(self._popup.winfo_id())
        except Exception:
            pass
        if self._root and self._running and self._popup_is_visible:
            self._root.after(1500, self._keep_popup_on_top)

    def _pulse_border(self):
        if not self._popup_is_visible or not self._popup or not self._running:
            return
        try:
            self._pulse_state = (self._pulse_state + 1) % 2
            color = "#ff2222" if self._pulse_state == 0 else "#990000"
            for child in self._popup.winfo_children():
                if isinstance(child, tk.Frame):
                    child.config(bg=color)
                    break
        except Exception:
            pass
        if self._root and self._running and self._popup_is_visible:
            self._root.after(700, self._pulse_border)

    def _do_hide_popup(self):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None
        self._popup_is_visible = False
        self._msg_label = None
        self._countdown_label = None
        print("[DesktopNotifier] Alert popup dismissed.")

    def _do_hide_all(self):
        """Destroy both the popup and the full-screen shield."""
        self._do_hide_popup()
        self._do_hide_shield()
