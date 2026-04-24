import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = "http://localhost:5000";
const WS_URL = "ws://localhost:5000/ws";

export default function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [detectionResult, setDetectionResult] = useState(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    // Cleanup previous
    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
    }

    try {
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log("[WS] Connected to Privacy Guard Backend");
        setConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "detection_result") {
            setDetectionResult(data);
          }
        } catch (e) {
          console.error("[WS] Parse error:", e);
        }
      };

      ws.current.onclose = () => {
        console.log("[WS] Disconnected. Retrying in 3s...");
        setConnected(false);
        reconnectTimeout.current = setTimeout(connect, 3000);
      };

      ws.current.onerror = () => {
        setConnected(false);
      };
    } catch (e) {
      console.error("[WS] Connection error:", e);
      setConnected(false);
      reconnectTimeout.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [connect]);

  const startMonitoring = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/monitoring/start`, { method: 'POST' });
      const data = await res.json();
      return data;
    } catch (e) {
      console.error("Failed to start monitoring:", e);
    }
  }, []);

  const stopMonitoring = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/monitoring/stop`, { method: 'POST' });
      const data = await res.json();
      setDetectionResult(null);
      return data;
    } catch (e) {
      console.error("Failed to stop monitoring:", e);
    }
  }, []);

  return { connected, detectionResult, startMonitoring, stopMonitoring };
}

// ── REST API Helpers ───────────────────────────────────────

export const apiGetUsers = () =>
  fetch(`${API_BASE}/api/users`).then(r => r.json());

export const apiRegisterUser = (name, image) => {
  const body = new FormData();
  body.append('name', name);
  body.append('image', image);
  return fetch(`${API_BASE}/api/users`, { method: 'POST', body }).then(r => r.json());
};

export const apiDeleteUser = (id) =>
  fetch(`${API_BASE}/api/users/${id}`, { method: 'DELETE' }).then(r => r.json());

export const apiGetLogs = () =>
  fetch(`${API_BASE}/api/logs`).then(r => r.json());

export const apiClearLogs = () =>
  fetch(`${API_BASE}/api/logs`, { method: 'DELETE' }).then(r => r.json());

export const apiGetSettings = () =>
  fetch(`${API_BASE}/api/settings`).then(r => r.json());

export const apiUpdateSettings = (updates) =>
  fetch(`${API_BASE}/api/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  }).then(r => r.json());

export const apiGetHealth = () =>
  fetch(`${API_BASE}/api/health`).then(r => r.json());

// ── Auth API ──────────────────────────────────────────────

export const apiSignup = (username, email, password) =>
  fetch(`${API_BASE}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  }).then(r => r.json());

export const apiLogin = (username, password) =>
  fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }).then(r => r.json());

export const apiAuthCheck = () =>
  fetch(`${API_BASE}/api/auth/check`).then(r => r.json());
