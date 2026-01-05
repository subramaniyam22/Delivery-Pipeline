'use client';

import { useState } from 'react';
import { login } from '@/lib/auth';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      console.log('Attempting login...');
      const token = await login(email, password);
      console.log('Login successful, token received:', token ? 'yes' : 'no');
      console.log('Token in localStorage:', localStorage.getItem('access_token') ? 'yes' : 'no');
      
      // Small delay to ensure localStorage is written
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Use router for client-side navigation instead of full page reload
      window.location.href = '/dashboard';
    } catch (err: any) {
      console.error('Login error:', err);
      let errorMessage = 'Login failed';
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <header className="login-header">
            <div className="logo" aria-hidden="true">
              <span>🚀</span>
            </div>
            <h1>Delivery Pipeline</h1>
            <p>Multi-Agent Project Management</p>
          </header>

          <form onSubmit={handleSubmit} aria-label="Login form">
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                disabled={loading}
                placeholder="Enter your email"
                aria-describedby={error ? 'login-error' : undefined}
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                disabled={loading}
                placeholder="Enter your password"
              />
            </div>

            {error && (
              <div className="error-message" id="login-error" role="alert" aria-live="polite">
                {error}
              </div>
            )}

            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? (
                <>
                  <span className="btn-spinner" aria-hidden="true" />
                  <span>Signing in...</span>
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="credentials-hint">
            <span className="hint-label">Demo Credentials</span>
            <code>admin@delivery.com / admin123</code>
          </div>
        </div>
      </div>

      <div className="decorations" aria-hidden="true">
        <div className="decoration decoration-1" />
        <div className="decoration decoration-2" />
        <div className="decoration decoration-3" />
      </div>

      <style jsx>{`
        .login-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
          background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }
        
        .login-container {
          position: relative;
          z-index: 1;
          width: 100%;
          max-width: 420px;
          padding: var(--space-lg);
        }
        
        .login-card {
          background: var(--bg-card);
          border: 1px solid var(--border-light);
          border-radius: var(--radius-xl);
          padding: var(--space-2xl);
          box-shadow: var(--shadow-lg);
          animation: fadeIn 0.5s ease;
        }
        
        .login-header {
          text-align: center;
          margin-bottom: var(--space-xl);
        }
        
        .logo {
          width: 64px;
          height: 64px;
          margin: 0 auto var(--space-md);
          background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
          border-radius: var(--radius-lg);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 32px;
          box-shadow: var(--shadow-md);
        }
        
        .login-header h1 {
          font-size: 24px;
          margin-bottom: var(--space-xs);
          color: var(--text-primary);
        }
        
        .login-header p {
          color: var(--text-muted);
          font-size: 14px;
        }
        
        .form-group {
          margin-bottom: var(--space-lg);
        }
        
        label {
          display: block;
          margin-bottom: var(--space-sm);
          font-size: 13px;
          font-weight: 600;
          color: var(--text-secondary);
        }
        
        input {
          width: 100%;
          padding: 14px var(--space-md);
          background: var(--bg-input);
          border: 1px solid var(--border-medium);
          border-radius: var(--radius-md);
          color: var(--text-primary);
          font-size: 15px;
          transition: all var(--transition-fast);
        }
        
        input:focus {
          outline: none;
          border-color: var(--accent-primary);
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
        
        input:disabled {
          opacity: 0.6;
          background: var(--bg-tertiary);
        }
        
        .error-message {
          background: var(--color-error-bg);
          color: var(--color-error);
          padding: var(--space-md);
          border-radius: var(--radius-md);
          margin-bottom: var(--space-lg);
          font-size: 13px;
          font-weight: 500;
          border: 1px solid var(--color-error-border);
        }
        
        .btn-submit {
          width: 100%;
          padding: 14px var(--space-lg);
          background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
          color: white;
          border: none;
          border-radius: var(--radius-md);
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: var(--space-sm);
          transition: all var(--transition-normal);
          box-shadow: var(--shadow-sm);
        }
        
        .btn-submit:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: var(--shadow-md);
        }
        
        .btn-submit:focus-visible {
          outline: 2px solid var(--accent-primary);
          outline-offset: 2px;
        }
        
        .btn-submit:disabled {
          opacity: 0.7;
          cursor: not-allowed;
          transform: none;
        }
        
        .btn-spinner {
          width: 18px;
          height: 18px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        
        .credentials-hint {
          margin-top: var(--space-xl);
          padding-top: var(--space-lg);
          border-top: 1px solid var(--border-light);
          text-align: center;
        }
        
        .hint-label {
          display: block;
          font-size: 11px;
          color: var(--text-hint);
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: var(--space-sm);
        }
        
        .credentials-hint code {
          font-family: var(--font-mono);
          font-size: 13px;
          color: var(--text-secondary);
          background: var(--bg-tertiary);
          padding: var(--space-sm) var(--space-md);
          border-radius: var(--radius-sm);
          border: 1px solid var(--border-light);
        }
        
        .decorations {
          position: absolute;
          inset: 0;
          pointer-events: none;
          overflow: hidden;
        }
        
        .decoration {
          position: absolute;
          border-radius: 50%;
          opacity: 0.6;
        }
        
        .decoration-1 {
          width: 500px;
          height: 500px;
          top: -200px;
          right: -150px;
          background: radial-gradient(circle, rgba(37, 99, 235, 0.12) 0%, transparent 70%);
        }
        
        .decoration-2 {
          width: 400px;
          height: 400px;
          bottom: -150px;
          left: -100px;
          background: radial-gradient(circle, rgba(124, 58, 237, 0.12) 0%, transparent 70%);
        }
        
        .decoration-3 {
          width: 200px;
          height: 200px;
          top: 40%;
          left: 10%;
          background: radial-gradient(circle, rgba(22, 163, 74, 0.08) 0%, transparent 70%);
        }
      `}</style>
    </div>
  );
}
