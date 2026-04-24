import React from 'react';

export default function LandingPage({ onEnterApp }) {
  return (
    <div className="landing-page" style={{ marginLeft: 0 }}>
      {/* Hero Section  */}
      <section className="hero-section">
        <div className="hero-grid-bg"></div>
        <div className="hero-content" style={{ animation: 'slideUp 0.8s ease' }}>
          <div className="hero-badge">
            🛡️ Visual Intrusion Dectector
          </div>
          <h1 className="hero-title">
            Protect Your Screen<br />
            <span className="gradient-text">From Shoulder Surfing</span>
          </h1>
          {/* <p className="hero-subtitle">
            Advanced AI face recognition and gaze tracking that detects unauthorized
            viewers in real-time. Get instant system-wide alerts — even when you're
            using other apps.
          </p> */}
          <div className="hero-buttons">
            <button className="btn btn-primary" onClick={onEnterApp}>
              🚀 Launch Dashboard
            </button>
            <a href="#features" className="btn btn-secondary">
              Learn More ↓
            </a>
          </div>
        </div>
      </section>

      {/* Features Section  */}
      <section className="features-section" id="features">
        <h2 className="section-title">Privacy Features</h2>
        <p className="section-subtitle">
          
        </p>
        <div className="features-grid">
          {[
            { icon: '👁️', title: 'Real-Time Face Detection', desc: 'MediaPipe-powered AI detects all faces in front of your screen with sub-50ms latency. Smooth bounding box tracking without jitter.' },
            { icon: '🔐', title: 'Face Recognition', desc: 'Register authorized users from your webcam. It instantly distinguishes you from unauthorized viewers using geometric face signatures.' },
            { icon: '👀', title: 'Gaze Detection', desc: 'Head pose estimation determines if someone is actually looking at your screen — not just standing nearby.' },
            { icon: '🔔', title: 'System-Wide Alerts', desc: 'Alerts appear OVER any application — Chrome, VS Code, PowerPoint. Desktop notifications even when minimized.' },
            { icon: '🛡️', title: 'Auto Screen Protection', desc: 'If an unauthorized viewer persists for 10 seconds, the system automatically blurs your screen or locks your workstation.' },
            { icon: '📊', title: 'Analytics & Logs', desc: 'Complete history of all privacy events with timestamps, threat severity, and duration tracking for security audits.' },
          ].map((f, i) => (
            <div className="feature-card" key={i} style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="feature-icon">{f.icon}</div>
              <div className="feature-title">{f.title}</div>
              <div className="feature-desc">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="how-section">
        <h2 className="section-title">How It Works</h2>
        <p className="section-subtitle">Three simple steps to protect your privacy</p>
        <div className="steps-grid">
          {[
            { n: '1', title: 'Register Your Face', desc: 'Take a quick photo from your webcam. The system creates a unique facial signature that identifies you as the authorized user.' },
            { n: '2', title: 'Start Monitoring', desc: 'Hit the Start button. The backend captures your webcam and runs the monitoring continuously even when minimized.' },
            { n: '3', title: 'Stay Protected', desc: 'If anyone unauthorized looks at your screen, you get an instant system-wide popup alert with auto-protection.' },
          ].map((s, i) => (
            <div className="step-card" key={i}>
              <div className="step-number">{s.n}</div>
              <div className="step-title">{s.title}</div>
              <div className="step-desc">{s.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/*  CTA Section  */}
      <section style={{
        padding: '80px 40px', textAlign: 'center',
        background: 'radial-gradient(ellipse at 50% 50%, rgba(99,102,241,0.1) 0%, transparent 60%)',
      }}>
        <h2 className="section-title" style={{ marginBottom: '16px' }}>
          Ready to Secure Your Screen?
        </h2>
        <p className="section-subtitle">Start protecting your privacy in under a minute</p>
        <button className="btn btn-primary" onClick={onEnterApp} style={{ padding: '16px 40px', fontSize: '1rem' }}>
          🚀 Get Started Now
        </button>
      </section>
    </div>
  );
}
