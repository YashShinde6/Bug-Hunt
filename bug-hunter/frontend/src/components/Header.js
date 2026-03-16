import React from 'react';
import './Header.css';

export default function Header() {
  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">🐛</div>
        <div>
          <h1 className="header-title">AI Bug Hunter</h1>
          <span className="header-subtitle">Multi-Agent Bug Detection System</span>
        </div>
      </div>
      <div className="header-status">
        <span className="status-dot"></span>
        System Online
      </div>
    </header>
  );
}
