'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { projectsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';

interface StageStats {
    stage: string;
    key: string;
    count: number;
    projects: any[];
    color: string;
    icon: string;
}

export default function DashboardPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [projects, setProjects] = useState<any[]>([]);
    const [stageStats, setStageStats] = useState<StageStats[]>([]);
    const [selectedStage, setSelectedStage] = useState<string | null>(null);
    const [user, setUser] = useState<any>(null);

    const stageConfig = [
        { key: 'ONBOARDING', label: 'Project Onboarding', color: 'var(--stage-onboarding)', icon: '📋' },
        { key: 'ASSIGNMENT', label: 'Project Assignment', color: 'var(--stage-assignment)', icon: '📤' },
        { key: 'BUILD', label: 'Build', color: 'var(--stage-build)', icon: '🔨' },
        { key: 'TEST', label: 'Test', color: 'var(--stage-test)', icon: '🧪' },
        { key: 'DEFECT_VALIDATION', label: 'Defect Validation', color: 'var(--stage-defect)', icon: '🔍' },
        { key: 'COMPLETE', label: 'Complete', color: 'var(--stage-complete)', icon: '✅' },
    ];

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        const currentUser = getCurrentUser();
        setUser(currentUser);
        
        // Redirect ADMIN to executive dashboard
        if (currentUser?.role === 'ADMIN') {
            router.push('/executive-dashboard');
            return;
        }
        
        loadProjects();
    }, [router]);

    const loadProjects = async () => {
        try {
            const response = await projectsAPI.list();
            const allProjects = response.data;
            setProjects(allProjects);

            const stats = stageConfig.map((stage) => ({
                stage: stage.label,
                key: stage.key,
                count: allProjects.filter((p: any) => p.current_stage === stage.key).length,
                projects: allProjects.filter((p: any) => p.current_stage === stage.key),
                color: stage.color,
                icon: stage.icon,
            }));
            setStageStats(stats);
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const totalActive = projects.filter((p) => p.current_stage !== 'COMPLETE').length;
    const totalComplete = projects.filter((p) => p.current_stage === 'COMPLETE').length;

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner"></div>
                <p>Loading dashboard...</p>
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

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="dashboard">
                <header className="page-header">
                    <div className="header-text">
                        <h1>Welcome back, {user?.name}!</h1>
                        <p>Here&apos;s your delivery pipeline overview</p>
                    </div>
                    <div className="header-stats">
                        <div className="stat-card stat-active">
                            <div className="stat-icon">📊</div>
                            <div className="stat-content">
                                <span className="stat-number">{totalActive}</span>
                                <span className="stat-label">Active</span>
                            </div>
                        </div>
                        <div className="stat-card stat-complete">
                            <div className="stat-icon">✅</div>
                            <div className="stat-content">
                                <span className="stat-number">{totalComplete}</span>
                                <span className="stat-label">Complete</span>
                            </div>
                        </div>
                    </div>
                </header>

                <section className="stages-section">
                    <h2>Pipeline Stages</h2>
                    <div className="stages-grid">
                        {stageStats.map((stage, index) => (
                            <button
                                key={stage.key}
                                className={`stage-card ${selectedStage === stage.key ? 'selected' : ''}`}
                                style={{ '--stage-color': stage.color, animationDelay: `${index * 50}ms` } as React.CSSProperties}
                                onClick={() => setSelectedStage(selectedStage === stage.key ? null : stage.key)}
                            >
                                <div className="stage-header">
                                    <span className="stage-icon">{stage.icon}</span>
                                    <span className="stage-count">{stage.count}</span>
                                </div>
                                <h3 className="stage-name">{stage.stage}</h3>
                                <div className="stage-bar">
                                    <div
                                        className="stage-bar-fill"
                                        style={{ width: `${Math.min((stage.count / (projects.length || 1)) * 100, 100)}%` }}
                                    />
                                </div>
                                {stage.projects.length > 0 && (
                                    <div className="stage-preview">
                                        {stage.projects.slice(0, 2).map((p: any) => (
                                            <span key={p.id} className="preview-item">{p.title}</span>
                                        ))}
                                        {stage.projects.length > 2 && (
                                            <span className="preview-more">+{stage.projects.length - 2} more</span>
                                        )}
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </section>

                {selectedStage && (
                    <section className="projects-section animate-fade-in">
                        <h2>Projects in {stageStats.find(s => s.key === selectedStage)?.stage}</h2>
                        <div className="projects-table">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Project Name</th>
                                        <th>Client</th>
                                        <th>Priority</th>
                                        <th>Created</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {stageStats
                                        .find((s) => s.key === selectedStage)
                                        ?.projects.map((project: any) => (
                                            <tr key={project.id}>
                                                <td className="cell-title">{project.title}</td>
                                                <td>{project.client_name}</td>
                                                <td>
                                                    <span className={`badge badge-${project.priority?.toLowerCase()}`}>
                                                        {project.priority}
                                                    </span>
                                                </td>
                                                <td className="cell-date">{new Date(project.created_at).toLocaleDateString()}</td>
                                                <td>
                                                    <button
                                                        className="btn-view"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            router.push(`/projects/${project.id}`);
                                                        }}
                                                    >
                                                        View
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}

                <section className="actions-section">
                    <h2>Quick Actions</h2>
                    <div className="actions-grid">
                        <button className="action-card" onClick={() => router.push('/projects/create')}>
                            <div className="action-icon">➕</div>
                            <span className="action-label">New Project</span>
                        </button>
                        <button className="action-card" onClick={() => router.push('/projects')}>
                            <div className="action-icon">📁</div>
                            <span className="action-label">All Projects</span>
                        </button>
                        <button className="action-card" onClick={() => router.push('/forecast')}>
                            <div className="action-icon">🔮</div>
                            <span className="action-label">Forecast</span>
                        </button>
                        <button className="action-card" onClick={() => router.push('/capacity')}>
                            <div className="action-icon">👥</div>
                            <span className="action-label">Team Capacity</span>
                        </button>
                    </div>
                </section>
            </main>

            <style jsx>{`
                .dashboard {
                    max-width: 1600px;
                    margin: 0 auto;
                    padding: var(--space-xl) var(--space-lg);
                }
                
                /* Header */
                .page-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-2xl);
                    padding: var(--space-xl);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-xl);
                }
                .header-text h1 {
                    margin-bottom: var(--space-xs);
                }
                .header-text p {
                    color: var(--text-muted);
                }
                .header-stats {
                    display: flex;
                    gap: var(--space-md);
                }
                .stat-card {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-md) var(--space-lg);
                    border-radius: var(--radius-lg);
                    min-width: 140px;
                }
                .stat-active {
                    background: var(--color-info-bg);
                    border: 1px solid var(--color-info-border);
                }
                .stat-complete {
                    background: var(--color-success-bg);
                    border: 1px solid var(--color-success-border);
                }
                .stat-icon {
                    font-size: 24px;
                }
                .stat-content {
                    display: flex;
                    flex-direction: column;
                }
                .stat-number {
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--text-primary);
                    line-height: 1;
                }
                .stat-label {
                    font-size: 12px;
                    color: var(--text-muted);
                }
                
                /* Sections */
                section {
                    margin-bottom: var(--space-2xl);
                }
                section h2 {
                    margin-bottom: var(--space-lg);
                    font-size: 18px;
                    color: var(--text-secondary);
                }
                
                /* Stages Grid */
                .stages-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: var(--space-md);
                }
                .stage-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    text-align: left;
                    cursor: pointer;
                    transition: all var(--transition-normal);
                    animation: fadeIn 0.4s ease forwards;
                    opacity: 0;
                }
                .stage-card:hover {
                    background: var(--bg-card-hover);
                    border-color: var(--stage-color);
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                }
                .stage-card.selected {
                    border-color: var(--stage-color);
                    box-shadow: var(--shadow-md);
                }
                .stage-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-sm);
                }
                .stage-icon {
                    font-size: 24px;
                }
                .stage-count {
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--stage-color);
                }
                .stage-name {
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--text-secondary);
                    margin-bottom: var(--space-md);
                }
                .stage-bar {
                    height: 4px;
                    background: var(--border-light);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                    margin-bottom: var(--space-sm);
                }
                .stage-bar-fill {
                    height: 100%;
                    background: var(--stage-color);
                    border-radius: var(--radius-full);
                    transition: width 0.5s ease;
                }
                .stage-preview {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                .preview-item {
                    font-size: 11px;
                    color: var(--text-hint);
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .preview-more {
                    font-size: 11px;
                    color: var(--stage-color);
                }
                
                /* Projects Table */
                .projects-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }
                .projects-section h2 {
                    margin-bottom: var(--space-md);
                }
                .projects-table {
                    overflow-x: auto;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th {
                    text-align: left;
                    padding: var(--space-sm) var(--space-md);
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--text-hint);
                    border-bottom: 1px solid var(--border-light);
                }
                td {
                    padding: var(--space-md);
                    color: var(--text-secondary);
                    border-bottom: 1px solid var(--border-light);
                }
                tr:last-child td {
                    border-bottom: none;
                }
                tr:hover td {
                    background: var(--bg-tertiary);
                }
                .cell-title {
                    font-weight: 600;
                    color: var(--text-primary);
                }
                .cell-date {
                    font-size: 13px;
                    color: var(--text-muted);
                }
                .badge {
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                    font-size: 11px;
                    font-weight: 600;
                }
                .badge-high, .badge-critical {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                }
                .badge-medium {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                }
                .badge-low {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }
                .btn-view {
                    padding: 6px 14px;
                    background: var(--color-info-bg);
                    color: var(--color-info);
                    border: 1px solid var(--color-info-border);
                    border-radius: var(--radius-sm);
                    font-size: 12px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }
                .btn-view:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                .btn-view:hover {
                    background: var(--color-info);
                    color: white;
                }
                
                /* Actions */
                .actions-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                    gap: var(--space-md);
                }
                .action-card {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-lg);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    cursor: pointer;
                    transition: all var(--transition-normal);
                }
                .action-card:hover {
                    background: var(--bg-card-hover);
                    border-color: var(--accent-primary);
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                }
                .action-card:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                .action-icon {
                    font-size: 28px;
                }
                .action-label {
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--text-secondary);
                }
                
                @media (max-width: 768px) {
                    .page-header {
                        flex-direction: column;
                        gap: var(--space-lg);
                        text-align: center;
                    }
                    .header-stats {
                        width: 100%;
                        justify-content: center;
                    }
                }
            `}</style>
        </div>
    );
}

