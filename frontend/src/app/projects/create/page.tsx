'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { projectsAPI, usersAPI } from '@/lib/api';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { canCreateProject } from '@/lib/rbac';
import { Role } from '@/lib/auth';
import Navigation from '@/components/Navigation';

export default function CreateProjectPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const editId = searchParams.get('edit');

    const [title, setTitle] = useState('');
    const [clientName, setClientName] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState('MEDIUM');

    // Sales Fields
    const [pmcName, setPmcName] = useState('');
    const [location, setLocation] = useState('');
    const [clientEmailIds, setClientEmailIds] = useState('');

    // New Field
    const [projectType, setProjectType] = useState('Full Website');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        const currentUser = getCurrentUser();
        setUser(currentUser);

        if (currentUser && !canCreateProject(currentUser.role)) {
            router.push('/dashboard');
            return;
        }

        // Fetch project if editing
        if (editId) {
            setLoading(true);
            projectsAPI.get(editId)
                .then(response => {
                    const project = response.data;
                    setTitle(project.title);
                    setClientName(project.client_name);
                    setDescription(project.description || '');
                    setPriority(project.priority);
                    setPmcName(project.pmc_name || '');
                    const locationNames = Array.isArray(project.location_names)
                        ? project.location_names.join(', ')
                        : '';
                    setLocation(locationNames || project.location || '');
                    setClientEmailIds(project.client_email_ids || '');
                    setProjectType(project.project_type || 'Full Website');
                    setLoading(false);
                })
                .catch(err => {
                    console.error("Failed to fetch project", err);
                    setError("Failed to load project details");
                    setLoading(false);
                });
        }
    }, [router, editId]);

    const handleCreate = async (status: 'DRAFT' | 'ACTIVE') => {
        setError('');
        setLoading(true);

        const locationNames = normalizeList(location);
        const payload = {
            title,
            client_name: clientName,
            description,
            priority,
            pmc_name: pmcName || undefined,
            location: location || undefined,
            location_names: locationNames.length ? locationNames : undefined,
            client_email_ids: clientEmailIds || undefined,
            project_type: projectType,
            status: status
        };

        try {
            if (editId) {
                await projectsAPI.update(editId, payload);
            } else {
                await projectsAPI.create(payload);
            }
            router.push('/projects');
        } catch (err: any) {
            console.error("Project Create/Update Error:", err);
            const errorDetail = err.response?.data?.detail ||
                (typeof err.response?.data === 'string' ? err.response.data : JSON.stringify(err.response?.data)) ||
                err.message;
            setError(errorDetail || `Failed to ${editId ? 'update' : 'create'} project`);
            setLoading(false);
        }
    };

    const normalizeList = (value: string) =>
        value.split(',').map(item => item.trim()).filter(Boolean);

    const isFormValid = () => {
        const baseValid = title.trim() && clientName.trim();
        const locations = normalizeList(location);
        return (
            baseValid &&
            description.trim() &&
            pmcName.trim() &&
            locations.length > 0 &&
            clientEmailIds.trim() &&
            projectType.trim() &&
            priority
        );
    };

    const priorities = [
        { key: 'LOW', label: 'Low', color: 'var(--color-success)' },
        { key: 'MEDIUM', label: 'Medium', color: 'var(--color-info)' },
        { key: 'HIGH', label: 'High', color: 'var(--color-warning)' },
        { key: 'CRITICAL', label: 'Critical', color: 'var(--color-error)' },
    ];

    const projectTypes = [
        "Full Website",
        "Partial Website",
        "Landing Page",
        "DA Landing Page",
        "Rapid Landing Page"
    ];

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="create-page">
                <div className="form-card">
                    <button onClick={() => router.push('/projects')} className="btn-close-icon" title="Cancel">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>

                    <div className="card-header">
                        <div className="header-icon">📁</div>
                        <div className="header-text">
                            <h1>Create New Project</h1>
                            <p>Fill in the details to start a new project</p>
                        </div>
                    </div>

                    <form onSubmit={(e) => e.preventDefault()}>
                        <div className="form-group">
                            <label htmlFor="title">Project Title <span className="required">*</span></label>
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
                            <label htmlFor="client">Client Name <span className="required">*</span></label>
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

                        {(user?.role === Role.SALES || user?.role === Role.ADMIN) && (
                            <>
                                <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
                                    <div className="form-group">
                                        <label htmlFor="pmcName">PMC Name <span className="required">*</span></label>
                                        <input
                                            id="pmcName"
                                            type="text"
                                            value={pmcName}
                                            onChange={(e) => setPmcName(e.target.value)}
                                            required
                                            disabled={loading}
                                            placeholder="Property Management Company"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label htmlFor="location">Location <span className="required">*</span></label>
                                        <input
                                            id="location"
                                            type="text"
                                            value={location}
                                            onChange={(e) => setLocation(e.target.value)}
                                            required
                                            disabled={loading}
                                            placeholder="Location 1, Location 2"
                                        />
                                    </div>
                                </div>

                                <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
                                    <div className="form-group">
                                        <label htmlFor="clientEmails">Client Email IDs <span className="required">*</span></label>
                                        <input
                                            id="clientEmails"
                                            type="text"
                                            value={clientEmailIds}
                                            onChange={(e) => setClientEmailIds(e.target.value)}
                                            required
                                            disabled={loading}
                                            placeholder="email1@example.com, email2@example.com"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label htmlFor="projectType">Project Type <span className="required">*</span></label>
                                        <select
                                            id="projectType"
                                            value={projectType}
                                            onChange={(e) => setProjectType(e.target.value)}
                                            required
                                            disabled={loading}
                                            style={{
                                                width: '100%',
                                                padding: '14px var(--space-md)',
                                                background: 'var(--bg-input)',
                                                border: '1px solid var(--border-medium)',
                                                borderRadius: 'var(--radius-md)',
                                                color: 'var(--text-primary)',
                                                fontSize: '15px'
                                            }}
                                        >
                                            {projectTypes.map((type) => (
                                                <option key={type} value={type}>{type}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            </>
                        )}

                        <div className="form-group">
                            <label htmlFor="description">
                                Description <span className="required">*</span>
                            </label>
                            <textarea
                                id="description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                required
                                disabled={loading}
                                placeholder="Brief project description"
                                rows={3}
                            />
                        </div>

                        <div className="form-group">
                            <label>Priority <span className="required">*</span></label>
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

                        <div className="form-actions" style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '16px' }}>
                            <button
                                type="button"
                                onClick={() => handleCreate('DRAFT')}
                                className="btn-draft"
                                disabled={loading}
                                style={{
                                    padding: '14px',
                                    background: 'var(--bg-input)',
                                    color: 'var(--text-secondary)',
                                    border: '1px solid var(--border-medium)',
                                    borderRadius: 'var(--radius-md)',
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    cursor: 'pointer'
                                }}
                            >
                                {loading ? 'Saving...' : 'Save as Draft'}
                            </button>

                            <button
                                type="button"
                                disabled={loading || !isFormValid()}
                                className="btn-submit"
                                onClick={() => handleCreate('ACTIVE')}
                                title={!isFormValid() ? "Please fill all required fields" : ""}
                                style={{ opacity: !isFormValid() ? 0.6 : 1, cursor: !isFormValid() ? 'not-allowed' : 'pointer' }}
                            >
                                {loading ? (
                                    <>
                                        <span className="btn-spinner" />
                                        Creating...
                                    </>
                                ) : (
                                    'Create Active Project'
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
                
                .required {
                    color: var(--color-error);
                    margin-left: 2px;
                }

                .btn-close-icon {
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: transparent;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 50%;
                    transition: all 0.2s;
                }

                .btn-close-icon:hover {
                    background: var(--bg-secondary);
                    color: var(--text-primary);
                }

                .form-card {
                    position: relative;
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-xl);
                    padding: var(--space-xl);
                }

                .btn-draft {
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
                
                .btn-draft:hover:not(:disabled) {
                    background: var(--bg-card-hover);
                    color: var(--text-primary);
                    border-color: var(--text-secondary);
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
