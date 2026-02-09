'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login, setCurrentUser, type User } from '@/lib/auth';
import { authAPI, healthAPI, usersAPI } from '@/lib/api';
import { getLandingRouteForRole } from '@/lib/nav';
import { hasCapability, type Capability } from '@/lib/rbac';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError, setForgotError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      console.log('Attempting login...');
      const token = await login(email, password);
      console.log('Login successful, token received:', token ? 'yes' : 'no');
      console.log('Token in localStorage:', localStorage.getItem('access_token') ? 'yes' : 'no');
      
      // Warm the backend in the background to reduce cold-start latency
      healthAPI.ping().catch(() => {});

      const meResponse = await usersAPI.me();
      const currentUser = meResponse.data as User;
      setCurrentUser(currentUser);

      const redirectPath = sessionStorage.getItem('post_login_redirect');
      if (redirectPath) {
        sessionStorage.removeItem('post_login_redirect');
        const cap = mapRouteToCapability(redirectPath);
        if (!cap || hasCapability(currentUser, cap)) {
          router.push(redirectPath);
          return;
        }
      }

      const landing = getLandingRouteForRole(currentUser.role);
      router.push(landing);
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

  const mapRouteToCapability = (path: string): Capability | null => {
    if (path.startsWith('/configuration')) return 'configure_system';
    if (path.startsWith('/users') || path.startsWith('/manage-users')) return 'manage_users';
    if (path.startsWith('/admin/operations') || path.startsWith('/operations')) return 'view_operations';
    if (path.startsWith('/admin/quality') || path.startsWith('/quality')) return 'view_quality';
    if (path.startsWith('/capacity')) return 'view_capacity';
    if (path.startsWith('/forecast')) return 'view_forecast';
    if (path.startsWith('/sentiments')) return 'view_sentiments';
    if (path.startsWith('/admin/audit-logs') || path.startsWith('/audit-logs')) return 'view_audit_logs';
    if (path.startsWith('/client-management') || path.startsWith('/clients')) return 'view_clients';
    if (path.startsWith('/projects')) return 'view_projects';
    return null;
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError('');
    setForgotLoading(true);

    try {
      await authAPI.forgotPassword(forgotEmail);
      setForgotSuccess(true);
    } catch (err: any) {
      let errorMessage = 'Failed to send reset email';
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setForgotError(errorMessage);
    } finally {
      setForgotLoading(false);
    }
  };

  const closeForgotPassword = () => {
    setShowForgotPassword(false);
    setForgotEmail('');
    setForgotSuccess(false);
    setForgotError('');
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <header className="login-header">
            <div className="logo" aria-hidden="true">
              <img src="/logo.svg" alt="Delivery Automation Suite logo" style={{ width: '48px', height: '48px' }} />
            </div>
            <h1>Delivery Automation Suite</h1>
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

          <div className="forgot-password-link">
            <button 
              type="button" 
              className="btn-forgot" 
              onClick={() => setShowForgotPassword(true)}
            >
              Forgot Password?
            </button>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotPassword && (
        <div className="modal-overlay" onClick={closeForgotPassword}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeForgotPassword} aria-label="Close">
              ×
            </button>
            <h2>Reset Password</h2>
            
            {forgotSuccess ? (
              <div className="success-message">
                <div className="success-icon">✓</div>
                <p>Password reset instructions have been sent to your email address.</p>
                <button className="btn-submit" onClick={closeForgotPassword}>
                  Back to Login
                </button>
              </div>
            ) : (
              <>
                <p className="modal-description">
                  Enter your email address and we'll send you instructions to reset your password.
                </p>
                <form onSubmit={handleForgotPassword}>
                  <div className="form-group">
                    <label htmlFor="forgot-email">Email Address</label>
                    <input
                      id="forgot-email"
                      type="email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      required
                      disabled={forgotLoading}
                      placeholder="Enter your email"
                    />
                  </div>
                  
                  {forgotError && (
                    <div className="error-message" role="alert">
                      {forgotError}
                    </div>
                  )}
                  
                  <button type="submit" className="btn-submit" disabled={forgotLoading}>
                    {forgotLoading ? (
                      <>
                        <span className="btn-spinner" aria-hidden="true" />
                        <span>Sending...</span>
                      </>
                    ) : (
                      'Send Reset Link'
                    )}
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      )}

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
        
        .forgot-password-link {
          margin-top: var(--space-lg);
          text-align: center;
        }
        
        .btn-forgot {
          background: none;
          border: none;
          color: var(--accent-primary);
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          padding: var(--space-sm);
          transition: all var(--transition-fast);
        }
        
        .btn-forgot:hover {
          color: var(--accent-secondary);
          text-decoration: underline;
        }
        
        .btn-forgot:focus-visible {
          outline: 2px solid var(--accent-primary);
          outline-offset: 2px;
          border-radius: var(--radius-sm);
        }
        
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          animation: fadeIn 0.2s ease;
        }
        
        .modal-content {
          background: var(--bg-card);
          border-radius: var(--radius-xl);
          padding: var(--space-2xl);
          width: 100%;
          max-width: 400px;
          margin: var(--space-lg);
          position: relative;
          box-shadow: var(--shadow-xl);
          animation: slideUp 0.3s ease;
        }
        
        .modal-close {
          position: absolute;
          top: var(--space-md);
          right: var(--space-md);
          background: none;
          border: none;
          font-size: 24px;
          color: var(--text-muted);
          cursor: pointer;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: var(--radius-sm);
          transition: all var(--transition-fast);
        }
        
        .modal-close:hover {
          background: var(--bg-tertiary);
          color: var(--text-primary);
        }
        
        .modal-content h2 {
          font-size: 20px;
          color: var(--text-primary);
          margin-bottom: var(--space-md);
        }
        
        .modal-description {
          color: var(--text-secondary);
          font-size: 14px;
          margin-bottom: var(--space-xl);
          line-height: 1.5;
        }
        
        .success-message {
          text-align: center;
          padding: var(--space-lg) 0;
        }
        
        .success-icon {
          width: 56px;
          height: 56px;
          background: var(--color-success-bg);
          color: var(--color-success);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 28px;
          margin: 0 auto var(--space-lg);
          border: 2px solid var(--color-success);
        }
        
        .success-message p {
          color: var(--text-secondary);
          font-size: 14px;
          margin-bottom: var(--space-xl);
          line-height: 1.5;
        }
        
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
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
