import React, { useState } from 'react';
import { apiSignup, apiLogin } from '../hooks/useWebSocket';

export default function AuthPage({ onLogin }) {
  const [isSignup, setIsSignup] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('Please fill in all fields');
      return;
    }

    if (isSignup) {
      if (!email.trim()) { setError('Please enter your email'); return; }
      if (password.length < 6) { setError('Password must be at least 6 characters'); return; }
      if (password !== confirmPassword) { setError('Passwords do not match'); return; }
    }

    setLoading(true);
    try {
      let result;
      if (isSignup) {
        result = await apiSignup(username.trim(), email.trim(), password);
      } else {
        result = await apiLogin(username.trim(), password);
      }

      if (result.success) {
        onLogin(result.user);
      } else {
        setError(result.error || 'Authentication failed');
      }
    } catch (err) {
      setError('Cannot connect to server. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="hero-grid-bg"></div>
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-icon" style={{ fontSize: '2.5rem', WebkitTextFillColor: 'unset', background: 'none' }}>🛡️</span>
          <span className="logo-text" style={{ fontSize: '1.2rem', display: 'block' }}>Privacy Guard</span>
        </div>

        <h1>{isSignup ? 'Create Account' : 'Welcome Back'}</h1>
        <p className="auth-subtitle">
          {isSignup
            ? 'Set up your secure privacy dashboard'
            : 'Sign in to your privacy dashboard'}
        </p>

        {error && <div className="auth-error">⚠ {error}</div>}

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            className="form-input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          {isSignup && (
            <input
              type="email"
              className="form-input"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          )}

          <input
            type="password"
            className="form-input"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isSignup ? 'new-password' : 'current-password'}
          />

          {isSignup && (
            <input
              type="password"
              className="form-input"
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
            />
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading
              ? '⏳ Please wait...'
              : isSignup ? '🚀 Create Account' : '🔓 Sign In'}
          </button>
        </form>

        <div className="auth-toggle">
          {isSignup ? 'Already have an account? ' : "Don't have an account? "}
          <button onClick={() => { setIsSignup(!isSignup); setError(''); }}>
            {isSignup ? 'Sign In' : 'Sign Up'}
          </button>
        </div>
      </div>
    </div>
  );
}
