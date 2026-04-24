import asyncio
import base64
import json
import time
import sys
import os
import cv2
import numpy as np
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer
from core.gaze_detector import GazeDetector
from core.monitor_engine import MonitorEngine
from background_monitor import BackgroundMonitor
from desktop_notifier import DesktopNotifier

# App Setup

desktop_notifier_instance: DesktopNotifier = None


@asynccontextmanager
async def lifespan(application):
    """Initialize the desktop notifier on server startup."""
    global desktop_notifier_instance
    desktop_notifier_instance = DesktopNotifier()
    desktop_notifier_instance.start()
    print("[Privacy Guard] Desktop notifier ready — system-wide alerts enabled.")
    yield
    # Shutdown
    if desktop_notifier_instance:
        desktop_notifier_instance.stop()
    if bg_monitor and bg_monitor.running:
        bg_monitor.stop()


app = FastAPI(title="AI Screen Privacy Guard API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


face_detector: FaceDetector = None
face_recognizer: FaceRecognizer = None
gaze_detector: GazeDetector = None
monitor_engine: MonitorEngine = None
bg_monitor: BackgroundMonitor = None
monitoring_active = False


def init_ai_modules():
    """Initialize AI modules on first use to save startup time."""
    global face_detector, face_recognizer, gaze_detector, monitor_engine, bg_monitor

    if face_detector is None:
        print("[Privacy Guard] Initializing AI modules...")
        settings = db.get_settings()
        sensitivity = float(settings.get("sensitivity", "0.5"))

        face_detector = FaceDetector(min_confidence=sensitivity)
        face_recognizer = FaceRecognizer(tolerance=0.75)
        gaze_detector = GazeDetector()
        monitor_engine = MonitorEngine()
        print("[Privacy Guard] AI modules initialized.")

    if bg_monitor is None:
        bg_monitor = BackgroundMonitor(
            face_detector=face_detector,
            face_recognizer=face_recognizer,
            gaze_detector=gaze_detector,
            monitor_engine=monitor_engine,
            desktop_notifier=desktop_notifier_instance,
        )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Streams detection results and camera frames FROM backend TO frontend.
    Backend owns the webcam — frontend just displays what it receives.

    Uses two concurrent tasks:
      - sender: pushes frame + result payloads at ~10 fps
      - receiver: listens for control messages (stop, ping) at all times
    Both tasks run simultaneously so Stop Monitoring always works.
    """
    global monitoring_active
    await ws.accept()
    init_ai_modules()

    stop_event = asyncio.Event()

    async def sender():
        """Push detection frame + result to frontend."""
        while not stop_event.is_set():
            try:
                if monitoring_active and bg_monitor and bg_monitor.running:
                    frame_b64 = bg_monitor.get_latest_frame_base64()
                    result    = bg_monitor.get_latest_result()

                    payload = {
                        "type": "detection_result",
                        "faces": [],
                        "status": "safe",
                        "total_faces": 0,
                        "authorized_count": 0,
                        "unauthorized_count": 0,
                        "countdown": 0,
                        "action": None,
                    }
                    if result:
                        payload = result.copy()
                        payload["type"] = "detection_result"
                    if frame_b64:
                        payload["frame"] = frame_b64

                    await ws.send_text(json.dumps(payload))

                await asyncio.sleep(0.1)   
            except Exception:
                stop_event.set()
                break

    async def receiver():
        """Listen for control messages from frontend."""
        while not stop_event.is_set():
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                message = json.loads(data)

                if message.get("type") == "stop":
                    global monitoring_active  # 
                    monitoring_active = False
                    if bg_monitor and bg_monitor.running:
                        bg_monitor.stop()
                    if monitor_engine:
                        monitor_engine.reset()
                    if desktop_notifier_instance:
                        desktop_notifier_instance.hide_alert()
                    stop_event.set()

            except asyncio.TimeoutError:
                continue
            except Exception:
                stop_event.set()
                break

    try:
        await asyncio.gather(sender(), receiver())
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected. Monitoring: {monitoring_active}")
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        stop_event.set()


# Auth Models

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str


# REST APIs 

# Auth

@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    """Create a new application account."""
    try:
        if len(req.username) < 3:
            return JSONResponse({"error": "Username must be at least 3 characters"}, status_code=400)
        if len(req.password) < 6:
            return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)
        if "@" not in req.email:
            return JSONResponse({"error": "Invalid email address"}, status_code=400)

        user = db.create_web_user(req.username, req.email, req.password)
        return {"success": True, "user": user, "message": "Account created successfully"}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Authenticate and login."""
    try:
        user = db.authenticate_web_user(req.username, req.password)
        if user is None:
            return JSONResponse({"error": "Invalid username or password"}, status_code=401)
        return {"success": True, "user": user, "message": "Login successful"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/auth/check")
async def auth_check():
    """Check if any accounts exist (for first-time setup flow)."""
    try:
        count = db.get_web_user_count()
        return {"has_accounts": count > 0, "account_count": count}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Health Check 

@app.get("/api/health")
@app.get("/health")
async def health_check():
    """Service health check."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "3.0.0",
        "ai_modules": {
            "detector": "active" if face_detector else "lazy",
            "recognizer": "active" if face_recognizer else "lazy",
            "gaze": "active" if gaze_detector else "lazy",
        },
        "background_monitor": "running" if (bg_monitor and bg_monitor.running) else "stopped",
        "desktop_notifier": "active" if desktop_notifier_instance else "inactive",
        "recognizer_tolerance": face_recognizer.tolerance if face_recognizer else None,
        "registered_users": len(face_recognizer.known_names) if face_recognizer else 0,
    }


@app.post("/api/test/shield")
async def test_shield():
    """Test the full-screen privacy shield for 4 seconds (debug endpoint)."""
    if not desktop_notifier_instance:
        return JSONResponse({"error": "Desktop notifier not running"}, status_code=503)
    desktop_notifier_instance.show_alert("TEST: Privacy Shield Active!", countdown=4)

    async def _auto_dismiss():
        await asyncio.sleep(4)
        desktop_notifier_instance.hide_alert()

    asyncio.create_task(_auto_dismiss())
    return {"message": "Shield triggered — will auto-dismiss in 4s"}


@app.post("/api/test/recognition")
async def test_recognition(image: str = Form(...)):
    """
    Debug: return similarity scores of an image against all registered users.
    Helps calibrate the tolerance threshold.
    """
    init_ai_modules()
    try:
        img_data = image
        if "," in img_data:
            img_data = img_data.split(",")[1]
        frame = cv2.imdecode(np.frombuffer(base64.b64decode(img_data), np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return JSONResponse({"error": "Bad image"}, status_code=400)

        from core.face_recognizer import _cosine_similarity
        sig = face_recognizer.encode_face(frame)
        if sig is None:
            return {"detected": False, "scores": []}

        scores = [
            {
                "user": face_recognizer.known_names[i],
                "similarity": round(_cosine_similarity(sig, ks), 4),
                "would_match": _cosine_similarity(sig, ks) >= face_recognizer.tolerance,
            }
            for i, ks in enumerate(face_recognizer.known_signatures)
        ]
        return {"detected": True, "tolerance": face_recognizer.tolerance, "scores": scores}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Users 

@app.post("/api/users")
async def register_user(name: str = Form(...), image: str = Form(...)):
    """
    Register a new authorized user.
    Expects name and a base64-encoded face image.
    """
    try:
        init_ai_modules()

        img_data = image
        if "," in img_data:
            img_data = img_data.split(",")[1]

        img_bytes = base64.b64decode(img_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return JSONResponse(
                {"error": "Invalid image: Could not decode"}, status_code=400
            )

        encoding = face_recognizer.encode_face(frame)
        if encoding is None:
            return JSONResponse(
                {"error": "No face detected. Ensure your face is clearly visible."},
                status_code=400,
            )

        user_id = db.add_user(name, encoding, avatar_base64=image[:500])
        face_recognizer.reload_users()

        return {
            "id": user_id,
            "name": name,
            "success": True,
            "message": "User registered successfully",
        }
    except Exception as e:
        print(f"[Registration] Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/users")
async def list_users():
    """List all registered authorized users."""
    try:
        users = db.get_all_users()
        return {"users": users}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    """Delete an authorized user."""
    try:
        deleted = db.delete_user(user_id)
        if face_recognizer:
            face_recognizer.reload_users()
        if deleted:
            return {"message": "User deleted successfully"}
        return JSONResponse({"error": "User not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Status

@app.get("/api/status")
async def get_status():
    """Get current monitoring status."""
    try:
        state = "safe"
        if monitor_engine:
            state = monitor_engine.state
        return {
            "monitoring": monitoring_active,
            "background_monitor_running": bg_monitor.running if bg_monitor else False,
            "state": state,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Monitoring Control 

@app.post("/api/monitoring/start")
async def start_monitoring():
    """Start background monitoring (backend-owned webcam + desktop alerts)."""
    try:
        global monitoring_active
        init_ai_modules()
        monitoring_active = True
        monitor_engine.reload_settings()

        if bg_monitor and not bg_monitor.running:
            bg_monitor.start()

        return {"message": "Background monitoring started", "mode": "backend_camera"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/monitoring/stop")
async def stop_monitoring():
    """Stop background monitoring."""
    try:
        global monitoring_active, bg_monitor
        monitoring_active = False

        if bg_monitor and bg_monitor.running:
            bg_monitor.stop()

        # Reset bg_monitor so start_monitoring() recreates it fresh.
        bg_monitor = None

        if monitor_engine:
            monitor_engine.reset()

        if desktop_notifier_instance:
            desktop_notifier_instance.hide_alert()

        return {"message": "Monitoring stopped"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Logs
@app.get("/api/logs")
async def get_logs():
    """Get intrusion logs."""
    try:
        logs = db.get_logs()
        return {"logs": logs}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/logs")
async def clear_logs():
    """Clear all intrusion logs."""
    try:
        db.clear_logs()
        return {"message": "Logs cleared"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Settings

@app.get("/api/settings")
async def get_settings():
    """Get all settings."""
    try:
        settings = db.get_settings()
        return {"settings": settings}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.put("/api/settings")
async def update_settings(updates: dict):
    """Update settings."""
    try:
        global face_detector
        db.update_settings(updates)
        if monitor_engine:
            monitor_engine.reload_settings()
        if face_detector and "sensitivity" in updates:
            face_detector = FaceDetector(min_confidence=float(updates["sensitivity"]))
        return {"message": "Settings updated"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Entry Point

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  AI SCREEN PRIVACY GUARD — Backend Server")
    print("  Version 3.0.0")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=5000)
