import React, { useState, useEffect } from 'react';
import useWebSocket from './hooks/useWebSocket';
import AuthPage from './components/AuthPage';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import UsersPage from './components/UsersPage';
import LogsPage from './components/LogsPage';
import SettingsPage from './components/SettingsPage';

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('privacyGuard_user');
    return saved ? JSON.parse(saved) : null;
  });

  const { connected, detectionResult, startMonitoring, stopMonitoring } = useWebSocket();

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('privacyGuard_user', JSON.stringify(userData));
    setCurrentPage('dashboard');
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('privacyGuard_user');
    setCurrentPage('landing');
  };

  // Landing page — no sidebar
  if (currentPage === 'landing') {
    return <LandingPage onEnterApp={() => setCurrentPage(user ? 'dashboard' : 'auth')} />;
  }

  // Auth page — no sidebar
  if (currentPage === 'auth' || (!user && currentPage !== 'landing')) {
    return <AuthPage onLogin={handleLogin} />;
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return (
          <Dashboard
            detectionResult={detectionResult}
            connected={connected}
            onStartMonitoring={startMonitoring}
            onStopMonitoring={stopMonitoring}
          />
        );
      case 'users':
        return <UsersPage />;
      case 'logs':
        return <LogsPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <Dashboard detectionResult={detectionResult} connected={connected}
                          onStartMonitoring={startMonitoring} onStopMonitoring={stopMonitoring} />;
    }
  };

  const statusColor =
    detectionResult?.status === 'safe' || detectionResult?.status === 'monitoring'
      ? 'safe'
      : detectionResult?.status === 'warning' || detectionResult?.status === 'countdown'
      ? 'warning'
      : detectionResult?.status === 'locked'
      ? 'danger'
      : 'info';

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-section">
          <span className="logo-icon">🛡️</span>
          <span className="logo-text">Visual Intrusion Detector</span>
        </div>

        <nav className="nav-menu">
          <button
            className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentPage('dashboard')}
          >
            <span className="nav-icon">📊</span> Dashboard
          </button>
          <button
            className={`nav-item ${currentPage === 'users' ? 'active' : ''}`}
            onClick={() => setCurrentPage('users')}
          >
            <span className="nav-icon">👥</span> Authorized Users
          </button>
          <button
            className={`nav-item ${currentPage === 'logs' ? 'active' : ''}`}
            onClick={() => setCurrentPage('logs')}
          >
            <span className="nav-icon">📜</span> Alert Logs
          </button>
          <button
            className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
            onClick={() => setCurrentPage('settings')}
          >
            <span className="nav-icon">⚙️</span> Settings
          </button>

          <div style={{ flex: 1 }}></div>

          <button
            className="nav-item"
            onClick={() => setCurrentPage('landing')}
            style={{ color: 'var(--text-muted)' }}
          >
            <span className="nav-icon">🏠</span> Home
          </button>
          <button
            className="nav-item"
            onClick={handleLogout}
            style={{ color: 'var(--danger)' }}
          >
            <span className="nav-icon">🚪</span> Logout
          </button>
        </nav>
    
        <div className="Account">
          {/* <div className="status-header">System Health</div>
          <div className="status-row">
            <span className={`status-dot ${connected ? 'safe' : 'danger'}`}></span>
            <span>API: {connected ? 'Online' : 'Offline'}</span>
          </div>
          <div className="status-row">
            <span className={`status-dot ${statusColor}`}></span>
            <span>Guard: {detectionResult?.status?.toUpperCase() || 'IDLE'}</span>
          </div>*/}
          {user && (
            <div className="status-row" style={{ marginTop: '8px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              👤 {user.username}
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {renderPage()}
      </main>

      {/* Global Intrusion Overlay */}
      {detectionResult?.status === 'locked' && (
        <div className="intrusion-overlay">
          <div className="overlay-content">
            <div className="overlay-warning">⚠️</div>
            <h1 className="overlay-title">UNAUTHORIZED VIEWER DETECTED</h1>
            <p className="overlay-msg">
              Privacy Shield Active. Your screen is currently being protected.
            </p>
            <div className="overlay-action">System Protected</div>
          </div>
        </div>
      )}
    </div>
  );
}
