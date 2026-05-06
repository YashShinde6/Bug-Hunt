import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth, googleProvider } from '../firebase';
import { signInWithPopup } from 'firebase/auth';
import './LoginPage.css';

export default function LoginPage() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError('');
    try {
      await signInWithPopup(auth, googleProvider);
      navigate('/app');
    } catch (err) {
      if (err.code === 'auth/invalid-api-key') {
         setError('Firebase API Key is missing or invalid. Please check your .env file.');
      } else {
         setError('Failed to log in: ' + err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <span>🎯</span> Bug Hunter
        </div>
        <h2>Welcome Back</h2>
        <p className="login-subtitle">Sign in to access the ultimate AI debugging tool</p>

        {error && <div className="login-error">{error}</div>}

        <button 
          className="google-btn" 
          onClick={handleGoogleSignIn}
          disabled={loading}
        >
          <img 
            src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" 
            alt="Google logo" 
          />
          {loading ? 'Signing in...' : 'Sign in with Google'}
        </button>

        <div className="login-footer">
          <button className="back-btn" onClick={() => navigate('/')}>
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
