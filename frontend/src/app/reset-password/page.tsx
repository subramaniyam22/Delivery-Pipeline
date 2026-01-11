'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { authAPI } from '@/lib/api';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Invalid reset link. Please request a new password reset.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);

    try {
      await authAPI.resetPassword(token, password);
      setSuccess(true);
    } catch (err: any) {
      let errorMessage = 'Failed to reset password';
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="reset-page">
        <div className="reset-container">
          <div className="reset-card">
            <div className="success-content">
              <div className="success-icon">✓</div>
              <h1>Password Reset Successful</h1>
              <p>Your password has been updated. You can now log in with your new password.</p>
              <a href="/login" className="btn-submit">
                Go to Login
              </a>
            </div>
          </div>
        </div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="reset-page">
        <div className="reset-container">
          <div className="reset-card">
            <div className="error-content">
              <div className="error-icon">!</div>
              <h1>Invalid Reset Link</h1>
              <p>This password reset link is invalid or has expired. Please request a new one.</p>
              <a href="/login" className="btn-submit">
                Back to Login
              </a>
            </div>
          </div>
        </div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  return (
    <div className="reset-page">
      <div className="reset-container">
        <div className="reset-card">
          <header className="reset-header">
            <div className="logo" aria-hidden="true">
              <span>📦</span>
            </div>
            <h1>Reset Password</h1>
            <p>Enter your new password below</p>
          </header>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="password">New Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="Enter new password"
                minLength={8}
              />
              <span className="hint">Must be at least 8 characters</span>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="Confirm new password"
              />
            </div>

            {error && (
              <div className="error-message" role="alert">
                {error}
              </div>
            )}

            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? (
                <>
                  <span className="btn-spinner" aria-hidden="true" />
                  <span>Resetting...</span>
                </>
              ) : (
                'Reset Password'
              )}
            </button>
          </form>

          <div className="back-link">
            <a href="/login">← Back to Login</a>
          </div>
        </div>
      </div>

      <div className="decorations" aria-hidden="true">
        <div className="decoration decoration-1" />
        <div className="decoration decoration-2" />
      </div>

      <style jsx>{styles}</style>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="reset-page">
        <div className="reset-container">
          <div className="reset-card">
            <div className="loading">Loading...</div>
          </div>
        </div>
      </div>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}

const styles = `
  .reset-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  }
  
  .reset-container {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 420px;
    padding: var(--space-lg);
  }
  
  .reset-card {
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-xl);
    padding: var(--space-2xl);
    box-shadow: var(--shadow-lg);
    animation: fadeIn 0.5s ease;
  }
  
  .reset-header {
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
  
  .reset-header h1 {
    font-size: 24px;
    margin-bottom: var(--space-xs);
    color: var(--text-primary);
  }
  
  .reset-header p {
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
  
  .hint {
    display: block;
    margin-top: var(--space-xs);
    font-size: 12px;
    color: var(--text-hint);
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
    text-decoration: none;
  }
  
  .btn-submit:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
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
  
  .back-link {
    margin-top: var(--space-lg);
    text-align: center;
  }
  
  .back-link a {
    color: var(--accent-primary);
    font-size: 14px;
    text-decoration: none;
    font-weight: 500;
  }
  
  .back-link a:hover {
    text-decoration: underline;
  }
  
  .success-content,
  .error-content {
    text-align: center;
    padding: var(--space-lg) 0;
  }
  
  .success-icon {
    width: 64px;
    height: 64px;
    background: var(--color-success-bg);
    color: var(--color-success);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    margin: 0 auto var(--space-lg);
    border: 2px solid var(--color-success);
  }
  
  .error-icon {
    width: 64px;
    height: 64px;
    background: var(--color-error-bg);
    color: var(--color-error);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    font-weight: bold;
    margin: 0 auto var(--space-lg);
    border: 2px solid var(--color-error);
  }
  
  .success-content h1,
  .error-content h1 {
    font-size: 22px;
    color: var(--text-primary);
    margin-bottom: var(--space-md);
  }
  
  .success-content p,
  .error-content p {
    color: var(--text-secondary);
    font-size: 14px;
    margin-bottom: var(--space-xl);
    line-height: 1.6;
  }
  
  .loading {
    text-align: center;
    padding: var(--space-2xl);
    color: var(--text-muted);
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
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
