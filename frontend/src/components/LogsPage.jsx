import React, { useState, useEffect } from 'react';
import { apiGetLogs, apiClearLogs } from '../hooks/useWebSocket';

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLogs();
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadLogs, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadLogs = async () => {
    try {
      const data = await apiGetLogs();
      setLogs(data.logs || []);
    } catch (e) {
      console.error('Failed to load logs:', e);
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    if (!confirm('Clear all intrusion logs?')) return;
    try {
      await apiClearLogs();
      setLogs([]);
    } catch (e) {
      console.error('Failed to clear logs:', e);
    }
  };

  const getSeverityBadge = (severity) => {
    const map = {
      critical: 'badge-critical',
      warning: 'badge-warning',
      info: 'badge-info',
      safe: 'badge-safe',
    };
    return map[severity] || 'badge-info';
  };

  return (
    <div style={{ animation: 'slideUp 0.4s ease' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Alert Logs</h1>
          <p className="page-subtitle">History of all privacy events and intrusion alerts</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={loadLogs}>
            🔄 Refresh
          </button>
          <button className="btn btn-danger" onClick={clearAll} disabled={logs.length === 0}>
            🗑️ Clear All
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="metrics-row" style={{ marginBottom: '24px' }}>
        <div className="metric-card">
          <div className="metric-icon info">📊</div>
          <div>
            <div className="metric-label">Total Events</div>
            <div className="metric-value">{logs.length}</div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon danger">🔴</div>
          <div>
            <div className="metric-label">Critical</div>
            <div className="metric-value">
              {logs.filter(l => l.severity === 'critical').length}
            </div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon warning">🟡</div>
          <div>
            <div className="metric-label">Warnings</div>
            <div className="metric-value">
              {logs.filter(l => l.severity === 'warning').length}
            </div>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-icon safe">🟢</div>
          <div>
            <div className="metric-label">Info</div>
            <div className="metric-value">
              {logs.filter(l => l.severity === 'info').length}
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            Loading logs...
          </div>
        ) : logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📋</div>
            <div style={{ fontWeight: 600, marginBottom: '8px' }}>No Events Recorded</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Privacy events will appear here once monitoring detects activity.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Person</th>
                  <th>Action</th>
                  <th>Duration</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td>{log.person || '—'}</td>
                    <td>{log.action || '—'}</td>
                    <td>{log.duration ? `${log.duration}s` : '—'}</td>
                    <td>
                      <span className={`badge ${getSeverityBadge(log.severity)}`}>
                        {log.severity || 'info'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
