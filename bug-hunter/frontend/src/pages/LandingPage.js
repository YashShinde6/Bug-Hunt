import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-logo">
          <span>🎯</span> Bug Hunter
        </div>
        <div className="nav-actions">
          <button className="nav-login-btn" onClick={() => navigate('/login')}>
            Login / Get Started
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">
            Squash Bugs with <span className="highlight-text">Superhuman AI</span>
          </h1>
          <p className="hero-subtitle">
            The ultimate multi-agent AI debugging suite. Upload code, CSV data, or screenshots, and let our ensemble of LLMs hunt down vulnerabilities instantly.
          </p>
          <div className="hero-cta">
            <button className="primary-btn" onClick={() => navigate('/login')}>
              Start Hunting Bugs
            </button>
            <button className="secondary-btn" onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}>
              Learn More
            </button>
          </div>
        </div>
        <div className="hero-visual">
          {/* Abstract dynamic code element */}
          <div className="glass-card visual-card main-visual">
             <div className="visual-header">
               <span className="dot red"></span>
               <span className="dot yellow"></span>
               <span className="dot green"></span>
             </div>
             <pre className="visual-code">
               <code>
                 <span className="keyword">async function</span> <span className="function">detectBugs</span>(code) {'{\n'}
                 {'  '}<span className="keyword">const</span> ensemble = <span className="keyword">await</span> <span className="variable">LLM_Agents</span>.analyze(code);{'\n'}
                 {'  '}<span className="keyword">return</span> ensemble.filter(bug {'=>'} bug.severity === <span className="string">'critical'</span>);{'\n'}
                 {'}'}
               </code>
             </pre>
          </div>
        </div>
      </section>

      {/* Functionality Overview */}
      <section id="features" className="features-section">
        <h2 className="section-title">How It Works</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <h3>Multi-Agent Analysis</h3>
            <p>Our orchestrator pipelines your code through static analyzers, syntax parsers, and pattern detectors.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>LLM Ensemble Validation</h3>
            <p>We don't trust just one model. We cross-verify bugs across Gemini, LLaMA, and more to eliminate false positives.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📸</div>
            <h3>Vision OCR</h3>
            <p>Got a screenshot of broken code? Upload the image, and our Gemini Vision engine extracts and analyzes it instantly.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>RAG Memory</h3>
            <p>Bug Hunter remembers past issues. Using Pinecone Vector DB, it instantly flags recurring vulnerabilities.</p>
          </div>
        </div>
      </section>

      {/* Team Members */}
      <section className="team-section">
        <h2 className="section-title">Meet the Team</h2>
        <p className="section-subtitle">The minds behind the AI Bug Hunter</p>
        <div className="team-grid">
          <div className="team-card">
            <div className="team-avatar">👨‍💻</div>
            <h3 className="team-name">Yash Shinde</h3>
          </div>
          <div className="team-card">
            <div className="team-avatar">👩‍💻</div>
            <h3 className="team-name">Deepika Sidral</h3>
          </div>
          <div className="team-card">
            <div className="team-avatar">👨‍💻</div>
            <h3 className="team-name">Tushar Ghorpade</h3>
          </div>
          <div className="team-card">
            <div className="team-avatar">👩‍💻</div>
            <h3 className="team-name">Saburi Nikam</h3>
          </div>
          <div className="team-card">
            <div className="team-avatar">👨‍💻</div>
            <h3 className="team-name">Madhav Jagtap</h3>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <span>🎯 Bug Hunter © 2026. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
