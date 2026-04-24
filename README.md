# 🛡️ Visual Intrusion Detector

Visual Intrusion Detector is an AI-powered privacy and desktop security system that detects unauthorized viewers near a computer screen using Computer Vision and Face Recognition. It helps protect confidential information by identifying trusted users, detecting suspicious presence, generating alerts, and taking automatic protective actions.

This system is useful for offices, libraries, work-from-home setups, laboratories, and confidential workspaces.

---

## Features

- Real-time Face Detection  
- Authorized User Recognition  
- Unauthorized Viewer Detection  
- Attention Monitoring  
- Multi-person Presence Detection  
- Automatic Screen Protection  
- Desktop Alerts / Notifications  
- Logs & Activity Dashboard  
- Fast Real-Time Monitoring  
- Modern Web Dashboard Interface  

---

## 🛠️ Tech Stack

### 🎨 Frontend
- React.js  
- Vite  
- CSS  

### ⚙️ Backend
- Python  
- OpenCV  
- MediaPipe  
- SQLite  

### 🤖 AI Models
- BlazeFace Model  
- Face Landmark Detection  
- Face Recognition Embeddings  

---

## 📁 Repository Structure

```
Visual-Intrusion-Detector/
│── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── face_detector.py
│   │   ├── face_recognizer.py
│   │   ├── gaze_detector.py
│   │   ├── monitor_engine.py
│   │   ├── blaze_face_short_range.tflite
│   │   └── face_landmarker.task
│   │
│   ├── background_monitor.py
│   ├── database.py
│   ├── desktop_notifier.py
│   ├── main.py
│   ├── requirements.txt
│
│── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── AuthPage.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── LandingPage.jsx
│   │   │   ├── LogsPage.jsx
│   │   │   ├── SettingsPage.jsx
│   │   │   └── UsersPage.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
│── assets/
│   └── screenshots/
│
│── .gitignore
│── README.md
```
## 🚀 Installation

▶️ Clone the repository:

```bash
git clone https://github.com/manasvidhawad/Visual-Intrusion-Detector.git
cd visual-intrusion-detector
```
## How to run 

## ⚙️ Backend Setup
```bash
cd backend
pip install -r requirements.txt
.\start_backend.bat
```

## 💻 Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
