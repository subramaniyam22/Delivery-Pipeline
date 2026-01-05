'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { projectsAPI } from '@/lib/api';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { canCreateProject } from '@/lib/rbac';
import Navigation from '@/components/Navigation';

export default function CreateProjectPage() {
    const router = useRouter();
    const [title, setTitle] = useState('');
    const [clientName, setClientName] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState('MEDIUM');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        const user = getCurrentUser();
        if (user && !canCreateProject(user.role)) {
            router.push('/dashboard');
        }
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await projectsAPI.create({
                title,
                client_name: clientName,
                description,
                priority,
            });
            router.push('/projects');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create project');
            setLoading(false);
        }
    };

    const priorities = [
        { key: 'LOW', label: 'Low', color: 'var(--color-success)' },
        { key: 'MEDIUM', label: 'Medium', color: 'var(--color-info)' },
        { key: 'HIGH', label: 'High', color: 'var(--color-warning)' },
        { key: 'CRITICAL', label: 'Critical', color: 'var(--color-error)' },
    ];

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="create-page">
                <button onClick={() => router.push('/projects')} className="btn-back">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M19 12H5M12 19l-7-7 7-7" />
                    </svg>
                    Back to Projects
                </button>

                <div className="form-card">
                    <div className="card-header">
                        <div className="header-icon">📁</div>
                        <div className="header-text">
                            <h1>Create New Project</h1>
                            <p>Fill in the details to start a new project</p>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label htmlFor="title">Project Title</label>
                            <input
                                id="title"
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                required
                                disabled={loading}
                                placeholder="Enter project title"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="client">Client Name</label>
                            <input
                                id="client"
                                type="text"
                                value={clientName}
                                onChange={(e) => setClientName(e.target.value)}
                                required
                                disabled={loading}
                                placeholder="Enter client name"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="description">Description</label>
                            <textarea
                                id="description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                disabled={loading}
                                placeholder="Brief project description (optional)"
                                rows={3}
                            />
                        </div>

                        <div className="form-group">
                            <label>Priority</label>
                            <div className="priority-grid">
                                {priorities.map((p) => (
                                    <button
                                        key={p.key}
                                        type="button"
                                        className={`priority-btn ${priority === p.key ? 'selected' : ''}`}
                                        style={{ '--priority-color': p.color } as React.CSSProperties}
                                        onClick={() => setPriority(p.key)}
                                        disabled={loading}
                                    >
                                        {p.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {error && <div className="error-message">{error}</div>}

                        <div className="form-actions">
                            <button 
                                type="button" 
                                onClick={() => router.push('/projects')}
                                className="btn-cancel"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button type="submit" disabled={loading} className="btn-submit">
                                {loading ? (
                                    <>
                                        <span className="btn-spinner" />
                                        Creating...
                                    </>
                                ) : (
                                    'Create Project'
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            </main>

            <style jsx>{`
                .create-page {
                    max-width: 640px;
                    margin: 0 auto;
                    padding: var(--space-xl);
                }
                
                .btn-back {
                    display: inline-flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: transparent;
                    color: var(--text-muted);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    margin-bottom: var(--space-lg);
                    transition: all var(--transition-fast);
                }
                
                .btn-back:hover {
                    background: var(--bg-card);
                    color: var(--text-primary);
                }
                
                .form-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-xl);
                    padding: var(--space-xl);
                }
                
                .card-header {
                    display: flex;
                    align-items: flex-start;
                    gap: var(--space-md);
                    margin-bottom: var(--space-xl);
                    padding-bottom: var(--space-lg);
                    border-bottom: 1px solid var(--border-light);
                }
                
                .header-icon {
                    width: 48px;
                    height: 48px;
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    border-radius: var(--radius-md);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                }
                
                .header-text h1 {
                    font-size: 20px;
                    margin-bottom: var(--space-xs);
                }
                
                .header-text p {
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
                
                input, textarea {
                    width: 100%;
                    padding: 14px var(--space-md);
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 15px;
                    resize: vertical;
                    transition: all var(--transition-fast);
                }
                
                input:focus, textarea:focus {
                    outline: none;
                    border-color: var(--accent-primary);
                    background: var(--bg-input-focus);
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }
                
                input:disabled, textarea:disabled {
                    opacity: 0.6;
                }
                
                .priority-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: var(--space-sm);
                }
                
                .priority-btn {
                    padding: 12px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-muted);
                    font-size: 13px;
                    font-weight: 500;
                    transition: all var(--transition-fast);
                }
                
                .priority-btn:hover {
                    background: var(--bg-card-hover);
                    color: var(--text-primary);
                }
                
                .priority-btn.selected {
                    background: color-mix(in srgb, var(--priority-color) 15%, transparent);
                    border-color: var(--priority-color);
                    color: var(--priority-color);
                }
                
                .priority-btn:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
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
                
                .form-actions {
                    display: flex;
                    gap: var(--space-md);
                    margin-top: var(--space-xl);
                    padding-top: var(--space-lg);
                    border-top: 1px solid var(--border-light);
                }
                
                .btn-cancel {
                    flex: 1;
                    padding: 14px;
                    background: var(--bg-input);
                    color: var(--text-secondary);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    font-weight: 500;
                    transition: all var(--transition-fast);
                }
                
                .btn-cancel:hover:not(:disabled) {
                    background: var(--bg-card-hover);
                    color: var(--text-primary);
                }
                
                .btn-submit {
                    flex: 2;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: var(--space-sm);
                    padding: 14px;
                    background: linear-gradient(135deg, var(--color-success) 0%, #059669 100%);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    font-weight: 600;
                    transition: all var(--transition-normal);
                }
                
                .btn-submit:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                }
                
                .btn-submit:focus-visible,
                .btn-cancel:focus-visible,
                .btn-back:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                
                .btn-submit:disabled,
                .btn-cancel:disabled {
                    opacity: 0.6;
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
                
                @media (max-width: 640px) {
                    .priority-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
            `}</style>
        </div>
    );
}
