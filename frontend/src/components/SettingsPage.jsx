import React, { useState, useEffect } from 'react';
import { apiGetSettings, apiUpdateSettings } from '../hooks/useWebSocket';

export default function SettingsPage() {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await apiGetSettings();
      setSettings(data.settings || {});
    } catch (e) {
      console.error('Failed to load settings:', e);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const saveSettings = async () => {
    setSaving(true);
    setMessage('');
    try {
      await apiUpdateSettings(settings);
      setMessage('Settings saved successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
        Loading settings...
      </div>
    );
  }

  return (
    <div style={{ animation: 'slideUp 0.4s ease' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure privacy guard behavior and sensitivity</p>
        </div>
        <button className="btn btn-primary" onClick={saveSettings} disabled={saving}>
          {saving ? '⏳ Saving...' : '💾 Save Changes'}
        </button>
      </div>

      {message && (
        <div style={{
          background: message.includes('Failed') ? 'var(--danger-glow)' : 'var(--safe-glow)',
          color: message.includes('Failed') ? 'var(--danger)' : 'var(--safe)',
          padding: '12px 16px', borderRadius: 'var(--radius-md)',
          marginBottom: '20px', fontSize: '0.85rem', fontWeight: 500,
        }}>
          {message.includes('Failed') ? '⚠' : '✓'} {message}
        </div>
      )}

      <div className="settings-grid">
        {/* Detection Settings */}
        <div className="card">
          <h3 style={{ marginBottom: '20px', fontWeight: 700 }}>🎯 Detection Settings</h3>

          <div className="setting-item">
            <div>
              <div className="setting-label-text">Detection Sensitivity</div>
              {/* <div className="setting-description">
                Lower = more sensitive (more false positives). Higher = stricter.
              </div> */}
            </div>
            <div style={{ width: '180px' }}>
              <input
                type="range"
                min="0.3"
                max="0.9"
                step="0.05"
                value={settings.sensitivity || '0.5'}
                onChange={(e) => updateSetting('sensitivity', e.target.value)}
                style={{ width: '100%' }}
              />
              <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {settings.sensitivity || '0.5'}
              </div>
            </div>
          </div>

          <div className="setting-item">
            <div>
              <div className="setting-label-text">Camera Index</div>
              {/* <div className="setting-description">
                Which camera to use (0 = default webcam)
              </div> */}
            </div>
            <select
              className="form-select"
              style={{ width: '120px' }}
              value={settings.camera_index || '0'}
              onChange={(e) => updateSetting('camera_index', e.target.value)}
            >
              <option value="0">Camera 0</option>
              <option value="1">Camera 1</option>
              <option value="2">Camera 2</option>
            </select>
          </div>
        </div>

        {/* Protection Settings */}
        <div className="card">
          <h3 style={{ marginBottom: '20px', fontWeight: 700 }}>🛡️ Protection Settings</h3>

          <div className="setting-item">
            <div>
              <div className="setting-label-text">Alert Timer (seconds)</div>
              {/* <div className="setting-description">
                Seconds before screen protection activates
              </div> */}
            </div>
            <div style={{ width: '180px' }}>
              <input
                type="range"
                min="3"
                max="30"
                step="1"
                value={settings.alert_timer || '7'}
                onChange={(e) => updateSetting('alert_timer', e.target.value)}
                style={{ width: '100%' }}
              />
              <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {settings.alert_timer || '7'}s
              </div>
            </div>
          </div>

          <div className="setting-item">
            <div>
              <div className="setting-label-text">Protection Mode</div>
              {/*<div className="setting-description">
                What happens when threat persists
              </div> */}
            </div>
            <select
              className="form-select"
              style={{ width: '160px' }}
              value={settings.protection_mode || 'blur'}
              onChange={(e) => updateSetting('protection_mode', e.target.value)}
            >
              <option value="blur">Blur Screen</option>
              <option value="lock">Lock Workstation</option>
            </select>
          </div>

          <div className="setting-item">
            <div>
              <div className="setting-label-text">Sound Alerts</div>
              {/* <div className="setting-description">
                Play system sound on detection
              </div> */}
            </div>
            <select
              className="form-select"
              style={{ width: '120px' }}
              value={settings.sound_alert || 'true'}
              onChange={(e) => updateSetting('sound_alert', e.target.value)}
            >
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
