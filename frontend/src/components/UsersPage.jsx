import React, { useState, useEffect, useRef } from 'react';
import { apiGetUsers, apiRegisterUser, apiDeleteUser } from '../hooks/useWebSocket';

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [newName, setNewName] = useState('');
  const [capturedImage, setCapturedImage] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const videoRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    loadUsers();
    return () => stopCamera();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await apiGetUsers();
      setUsers(data.users || []);
    } catch (e) {
      setError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const startCamera = async () => {
    setShowCamera(true);
    setCapturedImage(null);
    setError('');
    setSuccess('');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (e) {
      setError('Cannot access camera. Please allow camera permissions.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0, 640, 480);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    setCapturedImage(dataUrl);
  };

  const registerUser = async () => {
    if (!newName.trim()) {
      setError('Please enter a name');
      return;
    }
    if (!capturedImage) {
      setError('Please capture a photo first');
      return;
    }

    setRegistering(true);
    setError('');

    try {
      const result = await apiRegisterUser(newName.trim(), capturedImage);
      if (result.success) {
        setSuccess(`"${newName}" registered successfully!`);
        setNewName('');
        setCapturedImage(null);
        setShowCamera(false);
        stopCamera();
        loadUsers();
      } else {
        setError(result.error || 'Registration failed');
      }
    } catch (e) {
      setError('Failed to register user. Is the backend running?');
    } finally {
      setRegistering(false);
    }
  };

  const deleteUser = async (id, name) => {
    if (!confirm(`Remove "${name}" from authorized users?`)) return;
    try {
      await apiDeleteUser(id);
      setSuccess(`"${name}" removed`);
      loadUsers();
    } catch (e) {
      setError('Failed to delete user');
    }
  };

  return (
    <div style={{ animation: 'slideUp 0.4s ease' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Authorized Users</h1>
          <p className="page-subtitle">Register and manage who is allowed to view your screen</p>
        </div>
        <button className="btn btn-primary" onClick={startCamera}>
          + Register New User
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div style={{
          background: 'var(--danger-glow)', color: 'var(--danger)',
          padding: '12px 16px', borderRadius: 'var(--radius-md)',
          marginBottom: '20px', fontSize: '0.85rem', fontWeight: 500,
        }}>
          ⚠ {error}
        </div>
      )}
      {success && (
        <div style={{
          background: 'var(--safe-glow)', color: 'var(--safe)',
          padding: '12px 16px', borderRadius: 'var(--radius-md)',
          marginBottom: '20px', fontSize: '0.85rem', fontWeight: 500,
        }}>
          ✓ {success}
        </div>
      )}

      {/* Registration Panel */}
      {showCamera && (
        <div className="card" style={{ marginBottom: '28px' }}>
          <h3 style={{ marginBottom: '16px', fontWeight: 700 }}>📸 Register New Authorized User</h3>

          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="Enter name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ maxWidth: '400px' }}
            />
          </div>

          <div className="camera-preview" style={{ marginBottom: '16px' }}>
            {capturedImage ? (
              <img src={capturedImage} alt="Captured" style={{ width: '100%', display: 'block' }} />
            ) : (
              <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', display: 'block' }} />
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
            {!capturedImage ? (
              <button className="btn btn-primary" onClick={capturePhoto}>
                📸 Capture Photo
              </button>
            ) : (
              <>
                <button className="btn btn-secondary" onClick={() => setCapturedImage(null)}>
                  🔄 Retake
                </button>
                <button
                  className="btn btn-success"
                  onClick={registerUser}
                  disabled={registering}
                >
                  {registering ? '⏳ Registering...' : '✓ Register User'}
                </button>
              </>
            )}
            <button className="btn btn-secondary" onClick={() => { setShowCamera(false); stopCamera(); }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* User List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          Loading users...
        </div>
      ) : users.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>👤</div>
          <div style={{ fontWeight: 600, marginBottom: '8px' }}>No Authorized Users</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '20px' }}>
            Register yourself as the first authorized user to enable face recognition.
          </div>
          <button className="btn btn-primary" onClick={startCamera}>
            + Register Now
          </button>
        </div>
      ) : (
        <div className="user-grid">
          {users.map((user) => (
            <div key={user.id} className="user-card">
              <div className="user-avatar">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="user-name">{user.name}</div>
              <div className="user-date">
                Registered: {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </div>
              <button
                className="btn btn-danger"
                style={{ fontSize: '0.75rem', padding: '6px 14px' }}
                onClick={() => deleteUser(user.id, user.name)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
