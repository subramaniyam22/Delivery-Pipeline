'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { projectsAPI } from '@/lib/api';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { canCreateProject } from '@/lib/rbac';
import RoleGuard from '@/components/RoleGuard';
import Navigation from '@/components/Navigation';
import { Role } from '@/lib/auth';

export default function ProjectsPage() {
    const router = useRouter();
    const [projects, setProjects] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState<any>(null);
    const [filter, setFilter] = useState('active');

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        const currentUser = getCurrentUser();
        setUser(currentUser);
        loadProjects();
    }, []);

    const loadProjects = async () => {
        try {
            const response = await projectsAPI.list();
            setProjects(response.data);
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredProjects = projects.filter((p) => {
        if (filter === 'active') return p.current_stage !== 'COMPLETE';
        if (filter === 'complete') return p.current_stage === 'COMPLETE';
        return true;
    });

    const getStageColor = (stage: string) => {
        const colors: Record<string, string> = {
            'ONBOARDING': 'var(--stage-onboarding)',
            'ASSIGNMENT': 'var(--stage-assignment)',
            'BUILD': 'var(--stage-build)',
            'TEST': 'var(--stage-test)',
            'DEFECT_VALIDATION': 'var(--stage-defect)',
            'COMPLETE': 'var(--stage-complete)',
        };
        return colors[stage] || 'var(--text-muted)';
    };

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading projects...</p>
                <style jsx>{`
                    .loading-screen {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        gap: var(--space-md);
                    }
                    .loading-screen p {
                        color: var(--text-muted);
                    }
                `}</style>
            </div>
        );
    }

    if (!user) return null;

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="projects-page">
                <header className="page-header">
                    <div className="header-text">
                        <h1>Active Projects</h1>
                        <p>Manage and track all projects in the pipeline</p>
                    </div>
                    <RoleGuard
                        userRole={user.role}
                        requiredRoles={[Role.CONSULTANT, Role.ADMIN, Role.MANAGER]}
                    >
                        <button className="btn-create" onClick={() => router.push('/projects/create')}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="12" y1="5" x2="12" y2="19" />
                                <line x1="5" y1="12" x2="19" y2="12" />
                            </svg>
                            New Project
                        </button>
                    </RoleGuard>
                </header>

                <div className="filter-bar">
                    <div className="filter-tabs">
                        {[
                            { key: 'all', label: 'All', count: projects.length },
                            { key: 'active', label: 'Active', count: projects.filter(p => p.current_stage !== 'COMPLETE').length },
                            { key: 'complete', label: 'Complete', count: projects.filter(p => p.current_stage === 'COMPLETE').length },
                        ].map((tab) => (
                            <button
                                key={tab.key}
                                className={`filter-tab ${filter === tab.key ? 'active' : ''}`}
                                onClick={() => setFilter(tab.key)}
                            >
                                {tab.label}
                                <span className="tab-count">{tab.count}</span>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="projects-table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Project</th>
                                <th>Client</th>
                                <th>Priority</th>
                                <th>Stage</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredProjects.map((project, index) => (
                                <tr key={project.id} style={{ animationDelay: `${index * 30}ms` }}>
                                    <td className="cell-title">{project.title}</td>
                                    <td>{project.client_name}</td>
                                    <td>
                                        <span className={`badge badge-priority badge-${project.priority?.toLowerCase()}`}>
                                            {project.priority}
                                        </span>
                                    </td>
                                    <td>
                                        <span 
                                            className="badge badge-stage"
                                            style={{ 
                                                '--stage-color': getStageColor(project.current_stage)
                                            } as React.CSSProperties}
                                        >
                                            {project.current_stage?.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`badge badge-status badge-${project.status?.toLowerCase()}`}>
                                            {project.status}
                                        </span>
                                    </td>
                                    <td>
                                        <button
                                            className="btn-view"
                                            onClick={() => router.push(`/projects/${project.id}`)}
                                        >
                                            View
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    
                    {filteredProjects.length === 0 && (
                        <div className="empty-state">
                            <div className="empty-icon">📭</div>
                            <h3>No projects found</h3>
                            <p>Create a new project to get started</p>
                        </div>
                    )}
                </div>
            </main>

            <style jsx>{`
                .projects-page {
                    max-width: 1600px;
                    margin: 0 auto;
                    padding: var(--space-xl) var(--space-lg);
                }
                
                .page-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-xl);
                }
                
                .header-text h1 {
                    margin-bottom: var(--space-xs);
                }
                
                .header-text p {
                    color: var(--text-muted);
                }
                
                .btn-create {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: 12px var(--space-lg);
                    background: linear-gradient(135deg, var(--color-success) 0%, #059669 100%);
                    color: white;
                    border-radius: var(--radius-md);
                    font-weight: 600;
                    font-size: 14px;
                    transition: all var(--transition-normal);
                }
                
                .btn-create:hover {
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                }
                
                .btn-create:focus-visible {
                    outline: 2px solid var(--color-success);
                    outline-offset: 2px;
                }
                
                .filter-bar {
                    margin-bottom: var(--space-lg);
                }
                
                .filter-tabs {
                    display: flex;
                    gap: var(--space-sm);
                }
                
                .filter-tab {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    color: var(--text-muted);
                    font-size: 13px;
                    font-weight: 500;
                    transition: all var(--transition-fast);
                }
                
                .filter-tab:hover {
                    background: var(--bg-card-hover);
                    color: var(--text-primary);
                }
                
                .filter-tab.active {
                    background: var(--color-info-bg);
                    border-color: var(--accent-primary);
                    color: var(--accent-primary);
                }
                
                .filter-tab:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                
                .tab-count {
                    padding: 2px 8px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    font-size: 11px;
                }
                
                .filter-tab.active .tab-count {
                    background: var(--color-info-border);
                }
                
                .projects-table-container {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    overflow: hidden;
                }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                
                th {
                    text-align: left;
                    padding: var(--space-md) var(--space-lg);
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--text-muted);
                    background: var(--bg-tertiary);
                    border-bottom: 1px solid var(--border-light);
                }
                
                td {
                    padding: var(--space-md) var(--space-lg);
                    color: var(--text-secondary);
                    border-bottom: 1px solid var(--border-light);
                }
                
                tbody tr {
                    animation: fadeIn 0.3s ease forwards;
                    opacity: 0;
                }
                
                tbody tr:hover {
                    background: var(--bg-secondary);
                }
                
                tbody tr:last-child td {
                    border-bottom: none;
                }
                
                .cell-title {
                    font-weight: 600;
                    color: var(--text-primary);
                }
                
                .badge {
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                    font-size: 11px;
                    font-weight: 600;
                }
                
                .badge-priority.badge-high,
                .badge-priority.badge-critical {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                }
                
                .badge-priority.badge-medium {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                }
                
                .badge-priority.badge-low {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }
                
                .badge-stage {
                    background: color-mix(in srgb, var(--stage-color) 15%, transparent);
                    color: var(--stage-color);
                    border: 1px solid color-mix(in srgb, var(--stage-color) 30%, transparent);
                }
                
                .badge-status {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                }
                
                .btn-view {
                    padding: 6px 14px;
                    background: var(--bg-input);
                    color: var(--text-secondary);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-sm);
                    font-size: 12px;
                    font-weight: 500;
                    transition: all var(--transition-fast);
                }
                
                .btn-view:hover {
                    background: var(--accent-primary);
                    border-color: var(--accent-primary);
                    color: white;
                }
                
                .btn-view:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                
                .empty-state {
                    padding: var(--space-2xl);
                    text-align: center;
                }
                
                .empty-icon {
                    font-size: 48px;
                    margin-bottom: var(--space-md);
                }
                
                .empty-state h3 {
                    margin-bottom: var(--space-sm);
                }
                
                .empty-state p {
                    color: var(--text-muted);
                }
                
                @media (max-width: 768px) {
                    .page-header {
                        flex-direction: column;
                        gap: var(--space-lg);
                        text-align: center;
                    }
                }
            `}</style>
        </div>
    );
}
