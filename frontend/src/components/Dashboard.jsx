import React, { useRef, useEffect, useState, useCallback } from 'react';

export default function Dashboard({ detectionResult, connected, onStartMonitoring, onStopMonitoring }) {
  const [streaming, setStreaming] = useState(false);
  const [events, setEvents] = useState([]);
  const eventIdRef = useRef(0);
  const canvasRef = useRef(null);
  const prevStatusRef = useRef(null);

  const startMonitoring = async () => {
    setStreaming(true);
    await onStartMonitoring();
  };

  const stopMonitoring = async () => {
    setStreaming(false);
    await onStopMonitoring();
  };

  const addEvent = useCallback((text, type = 'info') => {
    setEvents((prev) => [
      { id: ++eventIdRef.current, text, type, time: new Date().toLocaleTimeString() },
      ...prev.slice(0, 49),
    ]);
  }, []);

  // Add live events — only when status CHANGES
  useEffect(() => {
    if (!detectionResult) return;
    const { status, total_faces, unauthorized_count } = detectionResult;
    if (status === prevStatusRef.current) return;
    prevStatusRef.current = status;

    if (unauthorized_count > 0) {
      if (status === 'locked') addEvent('🔴 SCREEN LOCKED — Privacy shield active', 'danger');
      else if (status === 'countdown') addEvent(`⏱ Countdown started — ${unauthorized_count} unauthorized viewer(s)`, 'danger');
      else if (status === 'warning') addEvent(`⚠ ${unauthorized_count} unauthorized viewer(s) detected`, 'danger');
    } else if (status === 'safe' || status === 'monitoring') {
      if (total_faces > 0) addEvent(`✓ ${total_faces} authorized face(s) — all clear`, 'safe');
      else addEvent('✓ No faces detected — safe', 'safe');
    }
  }, [detectionResult, addEvent]);

  useEffect(() => {
    if (detectionResult?.frame) setStreaming(true);
  }, [detectionResult?.frame]);

  // Draw frames on canvas
  useEffect(() => {
    if (!detectionResult?.frame || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => { canvas.width = img.width; canvas.height = img.height; ctx.drawImage(img, 0, 0); };
    img.src = `data:image/jpeg;base64,${detectionResult.frame}`;
  }, [detectionResult?.frame]);

  const dr = detectionResult || { status: 'safe', total_faces: 0, authorized_count: 0, unauthorized_count: 0, faces: [], countdown: 0 };

  const statusColor = dr.status === 'safe' || dr.status === 'monitoring' ? 'safe'
    : dr.status === 'warning' || dr.status === 'countdown' ? 'warning'
    : dr.status === 'locked' ? 'danger' : 'info';

  const riskLevel = dr.unauthorized_count === 0 ? 'LOW' : dr.status === 'locked' ? 'CRITICAL' : dr.status === 'countdown' ? 'HIGH' : 'MEDIUM';
  const riskColor = riskLevel === 'LOW' ? 'safe' : riskLevel === 'CRITICAL' ? 'danger' : riskLevel === 'HIGH' ? 'danger' : 'warning';

  // Compute gaze status summary
  const gazeAtScreen = (dr.faces || []).filter(f => f.gaze === 'at_screen').length;
  const gazeAway = (dr.faces || []).filter(f => f.gaze === 'looking_away').length;

  return (
    <div className="dashboard-page" style={{ animation: 'slideUp 0.4s ease' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Live Dashboard</h1>
       { /* <p className="page-subtitle">Real-time monitoring and threat detection</p>*/}
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          {!streaming ? (
            <button className="btn btn-primary" onClick={startMonitoring} disabled={!connected}>
              ▶ Start Monitoring
            </button>
          ) : (
            <button className="btn btn-danger" onClick={stopMonitoring}>
              ■ Stop Monitoring
            </button>
          )}
        </div>
      </div>

      {/*  Metrics Row  */}
      <div className="metrics-row">
        <div className="metric-card">
          <div className="metric-icon info">👤</div>
          <div><div className="metric-label">Total Faces</div><div className="metric-value">{dr.total_faces}</div></div>
        </div>
        <div className="metric-card">
          <div className="metric-icon safe">✓</div>
          <div><div className="metric-label">Authorized</div><div className="metric-value">{dr.authorized_count}</div></div>
        </div>
        <div className="metric-card">
          <div className="metric-icon danger">⚠</div>
          <div><div className="metric-label">Unauthorized</div><div className="metric-value">{dr.unauthorized_count}</div></div>
        </div>
        <div className="metric-card">
          <div className={`metric-icon ${riskColor}`}>
            {riskLevel === 'LOW' ? '🟢' : riskLevel === 'CRITICAL' ? '🔴' : '🟡'}
          </div>
          <div><div className="metric-label">Risk Level</div><div className="metric-value" style={{ fontSize: '1.2rem' }}>{riskLevel}</div></div>
        </div>
      </div>

      {/* Status Row */}
      <div className="metrics-row" style={{ marginBottom: '24px' }}>
        <div className="metric-card">
          <div className={`status-dot ${statusColor}`}></div>
          <div><div className="metric-label">System State</div><div className="metric-value" style={{ textTransform: 'uppercase', fontSize: '1rem' }}>{dr.status}</div></div>
        </div>
        <div className="metric-card">
          <div className={`status-dot ${streaming ? 'safe' : 'info'}`}></div>
          <div><div className="metric-label">Monitoring</div><div className="metric-value" style={{ fontSize: '1rem' }}>{streaming ? 'ACTIVE' : 'STOPPED'}</div></div>
        </div>
        <div className="metric-card">
          <div className="metric-icon warning">⏱️</div>
          <div><div className="metric-label">Countdown</div><div className="metric-value">{dr.countdown > 0 ? `${dr.countdown}s` : '—'}</div></div>
        </div>
        <div className="metric-card">
          <div className="metric-icon info">👁️</div>
          <div><div className="metric-label">Gaze Status</div><div className="metric-value" style={{ fontSize: '0.85rem' }}>{dr.total_faces > 0 ? `${gazeAtScreen} looking, ${gazeAway} away` : '—'}</div></div>
        </div>
      </div>

      {/*  Camera + Events  */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px' }}>
        <div className={`monitor-container ${dr.status === 'locked' || dr.status === 'countdown' ? 'warning-state' : ''}`}>
          {streaming && detectionResult?.frame ? (
            <canvas ref={canvasRef} className="webcam-video" />
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', minHeight: '360px' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', marginBottom: '12px', animation: 'float 3s ease infinite' }}>📷</div>
                <div style={{ color: 'var(--text-muted)' }}>
                  {connected ? 'Press Start to begin monitoring' : 'Connecting to backend...'}
                </div>
              </div>
            </div>
          )}
          <div className="monitor-hud">
            <div className="scan-line"></div>
            {streaming && dr.faces && dr.faces.map((face, i) => {
              const [x, y, w, h] = face.bbox;
              return (
                <div key={i} className={`face-overlay ${!face.authorized ? 'unauthorized' : ''}`} style={{
                  left: `${(x / 640) * 100}%`, top: `${(y / 480) * 100}%`,
                  width: `${(w / 640) * 100}%`, height: `${(h / 480) * 100}%`,
                }}>
                  <span className="face-label">
                    {face.name} • {face.gaze === 'at_screen' ? '👁️' : '👤'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Events Panel */}
        <div className="card" style={{ height: 'fit-content', maxHeight: '500px' }}>
          <h3 style={{ marginBottom: '16px', fontSize: '0.95rem', fontWeight: 700 }}>📡 Live Events</h3>
          <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
            {events.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '40px 0' }}>
                No events yet. Start monitoring to see activity.
              </div>
            ) : events.map((evt) => (
              <div key={evt.id} style={{ marginBottom: '12px', display: 'flex', gap: '10px', animation: 'slideUp 0.3s ease' }}>
                <span className={`status-dot ${evt.type}`} style={{ marginTop: '5px' }}></span>
                <div>
                  <div style={{ fontSize: '0.82rem' }}>{evt.text}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{evt.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
