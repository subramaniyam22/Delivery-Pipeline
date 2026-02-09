'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { projectsAPI } from '@/lib/api';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { canCreateProject } from '@/lib/rbac';
import RoleGuard from '@/components/RoleGuard';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';
import { Role } from '@/lib/auth';
import NotificationToast from '@/components/NotificationToast';
import { useNotification } from '@/context/NotificationContext';

export default function ProjectsPage() {
    const router = useRouter();
    const [projects, setProjects] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState<any>(null);
    const { refreshSignal, notifications, markAsRead } = useNotification();

    // Only show urgent details via toast
    const latestUrgent = notifications.find(n => n.type === 'urgent' && !n.read && (Date.now() - new Date(n.timestamp).getTime() < 10000));
    const [visibleToast, setVisibleToast] = useState<{ message: string, id: string } | null>(null);

    useEffect(() => {
        if (latestUrgent) {
            setVisibleToast({ message: latestUrgent.message, id: latestUrgent.id });
        }
    }, [latestUrgent]);

    const handleToastClose = () => {
        if (visibleToast) {
            markAsRead(visibleToast.id);
            setVisibleToast(null);
        }
    };

    // Listen to global refresh signal (triggered by NotificationContext)
    useEffect(() => {
        if (refreshSignal > 0) {
            loadProjects();
        }
    }, [refreshSignal]);

    // UI State
    const [filter, setFilter] = useState('all');
    const [selectedProject, setSelectedProject] = useState<any>(null);
    const [selectedRegion, setSelectedRegion] = useState<string>('ALL'); // Region Filter
    const [showMyProjects, setShowMyProjects] = useState(false);
    const [selectedStageFilter, setSelectedStageFilter] = useState('ALL');
    const [quickFilter, setQuickFilter] = useState<'none' | 'blocked' | 'at_risk' | 'due_soon'>('none');
    const [needsAssignment, setNeedsAssignment] = useState(false);

    // Action State
    const [showActionModal, setShowActionModal] = useState(false);
    const [actionType, setActionType] = useState<'pause' | 'resume' | 'archive' | 'complete'>('pause');
    const [actionReason, setActionReason] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    // Derived state
    const showRegionFilter = user?.role === 'ADMIN' || user?.role === 'MANAGER';
    const showHitlColumn = ['ADMIN', 'MANAGER', 'PC', 'CONSULTANT'].includes(user?.role || '');
    const showApprovalColumn = true;

    const getFilteredProjects = (projectList: any[], activeFilter: string) => {
        let filtered = projectList;

        // 1. Status Filter
        if (activeFilter !== 'all') {
            filtered = filtered.filter(p => {
                if (activeFilter === 'active') return p.status === 'ACTIVE';
                if (activeFilter === 'draft') return p.status === 'DRAFT';
                if (activeFilter === 'paused') return p.status === 'PAUSED';
                if (activeFilter === 'archived') return p.status === 'ARCHIVED' || p.is_archived;
                if (activeFilter === 'complete') return p.status === 'COMPLETED';
                return true;
            });
        }

        // 2. Region Filter (for Admin/Manager)
        if (showRegionFilter && selectedRegion !== 'ALL') {
            filtered = filtered.filter(p => p.region === selectedRegion);
        }

        // 3. Quick Filters (only apply when data exists)
        if (quickFilter === 'blocked') {
            filtered = filtered.filter(p => p.is_delayed === true);
        }
        if (quickFilter === 'at_risk') {
            if (filtered.some(p => p?.health?.status)) {
                filtered = filtered.filter(p => ['WARNING', 'CRITICAL'].includes(p?.health?.status));
            }
        }
        if (quickFilter === 'due_soon') {
            if (filtered.some(p => typeof p?.health?.remaining_days === 'number')) {
                filtered = filtered.filter(p => p?.health?.remaining_days <= 1 && p?.health?.remaining_days >= 0);
            }
        }

        return filtered;
    };

    const getApiUrl = () => {
        if (typeof window !== 'undefined') {
            const hostname = window.location.hostname;
            if (hostname === 'localhost' || hostname === '127.0.0.1') {
                return 'http://localhost:8000';
            }
            return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        }
        return 'http://localhost:8000';
    };

    const getAuthHeaders = () => {
        const token = localStorage.getItem('access_token');
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    };

    const getDefaultFiltersForRole = (role?: string) => {
        if (role === 'SALES') {
            return { showMyProjects: true, stage: 'ALL', needsAssignment: false };
        }
        if (role === 'CONSULTANT') {
            return { showMyProjects: true, stage: 'ALL', needsAssignment: false };
        }
        if (role === 'PC') {
            return { showMyProjects: false, stage: 'ASSIGNMENT', needsAssignment: true };
        }
        if (role === 'BUILDER') {
            return { showMyProjects: true, stage: 'BUILD', needsAssignment: false };
        }
        if (role === 'TESTER') {
            return { showMyProjects: true, stage: 'TEST', needsAssignment: false };
        }
        return { showMyProjects: false, stage: 'ALL', needsAssignment: false };
    };

    const buildProjectsParams = (override?: { showMyProjects?: boolean; stage?: string; needsAssignment?: boolean; role?: string }) => {
        if (!user && !override) return {};
        const effectiveShowMyProjects = override?.showMyProjects ?? showMyProjects;
        const effectiveStage = override?.stage ?? selectedStageFilter;
        const effectiveNeedsAssignment = override?.needsAssignment ?? needsAssignment;
        const effectiveRole = override?.role ?? user?.role;
        const params: Record<string, any> = {};

        if (effectiveShowMyProjects) {
            if (effectiveRole === 'SALES' || effectiveRole === 'CONSULTANT') {
                params.mine = true;
            } else {
                params.assigned = true;
            }
        }

        if (effectiveStage && effectiveStage !== 'ALL') {
            params.stage = effectiveStage;
        }

        if (effectiveNeedsAssignment) {
            params.needs_assignment = true;
        }

        return params;
    };

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        const currentUser = getCurrentUser();
        setUser(currentUser);
        const defaults = getDefaultFiltersForRole(currentUser?.role);
        setShowMyProjects(defaults.showMyProjects);
        setSelectedStageFilter(defaults.stage);
        setNeedsAssignment(defaults.needsAssignment);
        loadProjects({ ...defaults, role: currentUser?.role });
    }, []);

    const loadProjects = async (override?: { showMyProjects?: boolean; stage?: string; needsAssignment?: boolean; role?: string }) => {
        try {
            setLoading(true);
            const params = buildProjectsParams(override);
            const response = await projectsAPI.list(params);
            setProjects(response.data);
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!user) return;
        loadProjects();
    }, [showMyProjects, selectedStageFilter, needsAssignment]);

    const canManageProject = (project: any) => {
        if (!user) return false;
        if (['ADMIN', 'MANAGER'].includes(user.role)) return true;
        if (user.role === 'CONSULTANT') {
            return project.consultant_user_id === user.id || project.pc_user_id === user.id;
        }
        return false;
    };

    const isAssignedToProject = (project: any) => {
        if (!user) return false;

        // Direct assignment
        if (
            project.consultant_user_id === user.id ||
            project.pc_user_id === user.id ||
            project.builder_user_id === user.id ||
            project.consultant_user_id === user.id ||
            project.pc_user_id === user.id ||
            project.builder_user_id === user.id ||
            project.tester_user_id === user.id ||
            project.manager_user_id === user.id ||
            project.sales_user_id === user.id
        ) {
            return true;
        }

        // Manager Regional Assignment
        if (user.role === 'MANAGER' && user.region) {
            let projectRegion = null;
            if (project.consultant) {
                projectRegion = project.consultant.region;
            } else if (project.creator) {
                projectRegion = project.creator.region;
            }

            if (projectRegion === user.region) {
                return true;
            }
        }

        return false;
    };

    const isMyProject = (project: any) => {
        if (!user) return false;
        if (user.role === 'CONSULTANT') {
            return project.consultant_user_id === user.id;
        }
        return isAssignedToProject(project);
    };

    const hasClientUpdates = (project: any) => {
        return project.has_new_updates === true;
    };

    const getAssignedUserDisplay = (project: any) => {
        const assigned =
            project.builder ||
            project.consultant ||
            project.pc ||
            project.tester ||
            project.manager_chk ||
            project.sales_rep;

        if (assigned?.name) {
            return (
                <div className="user-info-cell">
                    <span className="user-name">{assigned.name}</span>
                    <span className="user-role">{assigned.role || 'Team Member'}</span>
                </div>
            );
        }

        return <span className="not-assigned">Build Agent</span>;
    };

    const handlePause = (project: any) => {
        setSelectedProject(project);
        setActionType('pause');
        setActionReason('');
        setShowActionModal(true);
    };

    const handleArchive = (project: any) => {
        setSelectedProject(project);
        setActionType('archive');
        setActionReason('');
        setShowActionModal(true);
    };

    const handleResume = async (project: any) => {
        try {
            const response = await fetch(`${getApiUrl()}/project-management/resume/${project.id}`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (response.ok) {
                loadProjects();
            } else {
                const error = await response.json();
                alert(error.detail || 'Failed to resume project');
            }
        } catch (error) {
            console.error('Error resuming project:', error);
        }
    };

    const handleUnarchive = async (project: any) => {
        try {
            const response = await fetch(`${getApiUrl()}/project-management/unarchive/${project.id}`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (response.ok) {
                loadProjects();
            } else {
                const error = await response.json();
                alert(error.detail || 'Failed to unarchive project');
            }
        } catch (error) {
            console.error('Error unarchiving project:', error);
        }
    };

    const submitAction = async () => {
        if (!selectedProject || !actionType) return;
        setSubmitting(true);

        try {
            if (actionType === 'pause') {
                await projectsAPI.pause(selectedProject.id, actionReason);
            } else if (actionType === 'archive') {
                await projectsAPI.archive(selectedProject.id, actionReason);
            } else {
                // Fallback for legacy actions like resume/complete if not in projectsAPI yet
                // Or if actionType is 'resume'
                const response = await fetch(`${getApiUrl()}/project-management/${actionType}/${selectedProject.id}`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ reason: actionReason || null })
                });
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `Failed to ${actionType} project`);
                }
            }

            setShowActionModal(false);
            loadProjects();
        } catch (error: any) {
            console.error(`Error ${actionType}ing project:`, error);
            alert(error.message || `Failed to ${actionType} project`);
        } finally {
            setSubmitting(false);
        }
    };

    const hasHealthData = projects.some(p => p?.health?.status);
    const hasDueSoonData = projects.some(p => typeof p?.health?.remaining_days === 'number');
    const filteredProjects = getFilteredProjects(projects, filter);

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

    console.log('ProjectsPage Render - User Role:', user.role);

    return (
        <RequireCapability cap="view_projects">
        <div className="page-wrapper">
            <Navigation />
            <main className="projects-page">
                <header className="page-header">
                    <PageHeader
                        title="Active Projects"
                        purpose="Manage and track all projects in the pipeline."
                        variant="page"
                    />
                    <RoleGuard
                        userRole={user.role}
                        requiredRoles={[Role.SALES]}
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
                            { key: 'active', label: 'Active', count: projects.filter(p => p.status === 'ACTIVE').length },
                            { key: 'draft', label: 'Draft', count: projects.filter(p => p.status === 'DRAFT').length },
                            { key: 'paused', label: '⏸️ Paused', count: projects.filter(p => p.status === 'PAUSED').length },
                            { key: 'archived', label: '📦 Archived', count: projects.filter(p => p.status === 'ARCHIVED').length },
                            { key: 'complete', label: '✅ Complete', count: projects.filter(p => p.status === 'COMPLETED').length },
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

                    <div className="filter-controls">
                        <label className="toggle">
                            <input
                                type="checkbox"
                                checked={showMyProjects}
                                onChange={(e) => setShowMyProjects(e.target.checked)}
                            />
                            <span>My Projects</span>
                        </label>

                        <select
                            value={selectedStageFilter}
                            onChange={(e) => setSelectedStageFilter(e.target.value)}
                            className="stage-select"
                            aria-label="Stage filter"
                        >
                            <option value="ALL">All Stages</option>
                            <option value="ONBOARDING">Onboarding</option>
                            <option value="ASSIGNMENT">Assignment</option>
                            <option value="BUILD">Build</option>
                            <option value="TEST">Test</option>
                            <option value="DEFECT_VALIDATION">Defect Validation</option>
                            <option value="COMPLETE">Complete</option>
                        </select>

                        <div className="quick-chips">
                            <button
                                className={`quick-chip ${quickFilter === 'blocked' ? 'active' : ''}`}
                                onClick={() => setQuickFilter(quickFilter === 'blocked' ? 'none' : 'blocked')}
                                title="Show blocked or delayed projects"
                            >
                                Blocked
                            </button>
                            <button
                                className={`quick-chip ${quickFilter === 'at_risk' ? 'active' : ''}`}
                                onClick={() => setQuickFilter(quickFilter === 'at_risk' ? 'none' : 'at_risk')}
                                disabled={!hasHealthData}
                                title={hasHealthData ? 'Show projects at risk' : 'Risk data not available yet'}
                            >
                                At Risk
                            </button>
                            <button
                                className={`quick-chip ${quickFilter === 'due_soon' ? 'active' : ''}`}
                                onClick={() => setQuickFilter(quickFilter === 'due_soon' ? 'none' : 'due_soon')}
                                disabled={!hasDueSoonData}
                                title={hasDueSoonData ? 'Show projects due soon' : 'Due soon data not available yet'}
                            >
                                Due Soon
                            </button>
                        </div>
                    </div>

                    {showRegionFilter && (
                        <div className="region-filter" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>Region:</label>
                            <select
                                value={selectedRegion}
                                onChange={(e) => setSelectedRegion(e.target.value)}
                                className="region-select"
                                style={{
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-card)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer'
                                }}
                            >
                                <option value="ALL">All Regions</option>
                                <option value="INDIA">India</option>
                                <option value="US">US</option>
                                <option value="PH">Philippines</option>
                            </select>
                        </div>
                    )}
                </div>

                {user?.role && ['CONSULTANT', 'PC', 'BUILDER', 'TESTER'].includes(user.role) && (
                    <div className="my-projects-section">
                        <h2>📌 My Assigned Projects ({filteredProjects.filter(p => isAssignedToProject(p)).length})</h2>
                        <div className="my-projects-grid">
                            {filteredProjects.filter(p => isAssignedToProject(p)).map((project) => (
                                <div key={project.id} className="my-project-card" onClick={() => router.push(`/projects/${project.id}`)}>
                                    <div className="project-card-header">
                                        <h3>
                                            {project.title}
                                            {hasClientUpdates(project) && (
                                                <span className="badge-update-text" style={{
                                                    marginLeft: '8px',
                                                    fontSize: '0.75rem',
                                                    backgroundColor: '#fee2e2',
                                                    color: '#ef4444',
                                                    padding: '2px 8px',
                                                    borderRadius: '12px',
                                                    border: '1px solid #fecaca'
                                                }}>New Updates</span>
                                            )}
                                        </h3>
                                        <span className={`badge badge-priority badge-${project.priority?.toLowerCase()}`}>
                                            {project.priority}
                                        </span>
                                    </div>
                                    <p className="client-name">{project.client_name}</p>
                                    <div className="project-card-footer">
                                        <span
                                            className="badge badge-stage"
                                            style={{ '--stage-color': getStageColor(project.current_stage) } as React.CSSProperties}
                                        >
                                            {project.current_stage?.replace('_', ' ')}
                                        </span>
                                        <span className="my-role-badge">
                                            {project.consultant_user_id === user.id && '🎯 Consultant'}
                                            {project.pc_user_id === user.id && '📋 PC'}
                                            {project.builder_user_id === user.id && '🔧 Builder'}
                                            {project.tester_user_id === user.id && '🧪 Tester'}
                                        </span>
                                    </div>
                                </div>
                            ))}
                            {filteredProjects.filter(p => isAssignedToProject(p)).length === 0 && (
                                <p className="no-projects">No projects assigned to you in this filter.</p>
                            )}
                        </div>
                    </div>
                )}

                <div className="all-projects-header">
                    <h2>{user?.role === 'ADMIN' ? '📊 All Projects Overview' : '📋 All Projects (Backlog)'}</h2>
                    {user?.role !== 'ADMIN' && (
                        <p className="backlog-note">View all projects in the pipeline. Click to see high-level details.</p>
                    )}
                </div>

                <div className="projects-table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Project</th>
                                <th>Client</th>
                                <th>Created By</th>
                                {user?.role !== 'SALES' && <th>Assigned To</th>}
                                <th>Priority</th>
                                <th>Stage</th>
                                <th>Status</th>
                                {showHitlColumn && <th>HITL</th>}
                                {showApprovalColumn && <th>Approval Pending</th>}
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredProjects.map((project, index) => (
                                <tr
                                    key={project.id}
                                    style={{ animationDelay: `${index * 30}ms` }}
                                    className={isAssignedToProject(project) ? 'my-project-row' : ''}
                                >
                                    <td className="cell-title">
                                        {project.title}
                                        {isMyProject(project) && <span className="owned-badge">★</span>}
                                    </td>
                                    <td>{project.client_name}</td>
                                    <td className="cell-user">
                                        {project.creator ? (
                                            <div className="user-info-cell">
                                                <span className="user-name">{project.creator.name}</span>
                                                <span className="user-role">{project.creator.role}</span>
                                            </div>
                                        ) : (
                                            <span className="not-assigned">—</span>
                                        )}
                                    </td>
                                    {user?.role !== 'SALES' && (
                                        <td className="cell-user">
                                            {getAssignedUserDisplay(project)}
                                        </td>
                                    )}
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
                                    {showHitlColumn && (
                                        <td>
                                            {project.hitl_enabled === true && (
                                                <span className="badge badge-hitl badge-hitl-on">ON</span>
                                            )}
                                            {project.hitl_enabled === false && (
                                                <span className="badge badge-hitl badge-hitl-off">OFF</span>
                                            )}
                                            {typeof project.hitl_enabled === 'undefined' && (
                                                <span className="not-assigned">—</span>
                                            )}
                                        </td>
                                    )}
                                    {showApprovalColumn && (
                                        <td>
                                            {project.pending_approvals_count > 0 ? (
                                                <span className="badge badge-approval badge-approval-yes">
                                                    Yes ({project.pending_approvals_count})
                                                </span>
                                            ) : (
                                                <span className="badge badge-approval badge-approval-no">No</span>
                                            )}
                                        </td>
                                    )}
                                    <td>
                                        <div className="action-buttons">
                                            {(() => {
                                                const canManage = canManageProject(project) || (user?.role === 'SALES' && (project.sales_user_id === user.id || project.status === 'DRAFT'));
                                                const isAdminManager = ['ADMIN', 'MANAGER'].includes(user?.role || '');
                                                return (
                                                    <>
                                                        {/* Standard View Button for All Users */}
                                                        <button
                                                            className="btn-view"
                                                            onClick={() => router.push(`/projects/${project.id}`)}
                                                            title="View Details"
                                                        >
                                                            👁️
                                                        </button>

                                                        {/* Pause Button */}
                                                        {(project.status === 'ACTIVE' || project.status === 'DRAFT') && (
                                                            <button
                                                                className="btn-pause"
                                                                onClick={() => canManage && handlePause(project)}
                                                                title="Pause Project"
                                                                disabled={!canManage || (user?.role === 'SALES' && project.status !== 'DRAFT' && project.status !== 'ACTIVE')}
                                                            >
                                                                ⏸️
                                                            </button>
                                                        )}

                                                        {/* Resume Button */}
                                                        {project.status === 'PAUSED' && (
                                                            <button
                                                                className="btn-resume"
                                                                onClick={() => canManage && handleResume(project)}
                                                                title="Resume Project"
                                                                disabled={!canManage}
                                                            >
                                                                ▶️
                                                            </button>
                                                        )}

                                                        {/* Archive Button */}
                                                        {project.status !== 'ARCHIVED' && (
                                                            <button
                                                                className="btn-archive"
                                                                onClick={() => canManage && handleArchive(project)}
                                                                title="Archive Project"
                                                                disabled={!canManage}
                                                            >
                                                                📦
                                                            </button>
                                                        )}

                                                        {/* Unarchive Button */}
                                                        {project.status === 'ARCHIVED' && (
                                                            <button
                                                                className="btn-unarchive"
                                                                onClick={() => isAdminManager && handleUnarchive(project)}
                                                                title="Unarchive Project"
                                                                disabled={!isAdminManager}
                                                            >
                                                                📤
                                                            </button>
                                                        )}

                                                        {/* Delete Button */}
                                                        <button
                                                            className="btn-delete"
                                                            onClick={() => {
                                                                if (!canManage) return;
                                                                if (confirm("Are you sure you want to DELETE this project?")) {
                                                                    fetch(`${getApiUrl()}/projects/${project.id}`, { method: 'DELETE', headers: getAuthHeaders() })
                                                                        .then(() => loadProjects())
                                                                        .catch(err => alert("Failed to delete"));
                                                                }
                                                            }}
                                                            title="Delete Project"
                                                            style={{ color: '#ef4444' }}
                                                            disabled={!canManage}
                                                        >
                                                            🗑️
                                                        </button>

                                                        {/* Edit Button (Sales Drafts) - End */}
                                                        {user?.role === 'SALES' && project.status === 'DRAFT' && (
                                                            <button
                                                                className="btn-edit"
                                                                onClick={() => router.push(`/projects/create?edit=${project.id}`)}
                                                                title="Edit Project"
                                                            >
                                                                ✏️
                                                            </button>
                                                        )}
                                                    </>
                                                );
                                            })()}
                                        </div>
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

            {showActionModal && selectedProject && (
                <div className="modal-overlay" onClick={() => setShowActionModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>{actionType === 'pause' ? '⏸️ Pause Project' : '📦 Archive Project'}</h2>
                            <button className="close-btn" onClick={() => setShowActionModal(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            <p className="project-name">{selectedProject.title}</p>
                            <p className="action-description">
                                {actionType === 'pause'
                                    ? 'Pausing will temporarily halt all work on this project. It can be resumed later.'
                                    : 'Archiving will move this project to the archive. Only Admin/Manager can unarchive.'}
                            </p>
                            <div className="form-group">
                                <label>Reason (optional)</label>
                                <textarea
                                    value={actionReason}
                                    onChange={(e) => setActionReason(e.target.value)}
                                    placeholder={`Enter reason for ${actionType}ing...`}
                                    rows={3}
                                />
                            </div>
                        </div>
                        <div className="modal-actions">
                            <button className="btn-secondary" onClick={() => setShowActionModal(false)}>Cancel</button>
                            <button
                                className={actionType === 'pause' ? 'btn-warning' : 'btn-danger'}
                                onClick={submitAction}
                                disabled={submitting}
                            >
                                {submitting ? 'Processing...' : actionType === 'pause' ? '⏸️ Pause Project' : '📦 Archive Project'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {visibleToast && (
                <NotificationToast
                    message={visibleToast.message}
                    type="urgent"
                    onClose={handleToastClose}
                />
            )}

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
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    flex-wrap: wrap;
                }
                
                .filter-tabs {
                    display: flex;
                    gap: var(--space-sm);
                }

                .filter-controls {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    margin-left: var(--space-md);
                }

                .toggle {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 13px;
                    color: var(--text-secondary);
                    cursor: pointer;
                    user-select: none;
                }

                .toggle input {
                    accent-color: var(--accent-primary);
                }

                .stage-select {
                    padding: 8px 12px;
                    border-radius: 6px;
                    border: 1px solid var(--border-color);
                    background-color: var(--bg-card);
                    color: var(--text-primary);
                    cursor: pointer;
                    font-size: 13px;
                }

                .quick-chips {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                }

                .quick-chip {
                    padding: 6px 10px;
                    border-radius: 999px;
                    border: 1px solid var(--border-light);
                    background: var(--bg-card);
                    color: var(--text-secondary);
                    font-size: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .quick-chip:hover:not(:disabled) {
                    background: var(--bg-card-hover);
                    color: var(--text-primary);
                }

                .quick-chip.active {
                    background: var(--color-info-bg);
                    border-color: var(--accent-primary);
                    color: var(--accent-primary);
                }

                .quick-chip:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
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
                
                .badge-status.badge-paused {
                    background: #fef3c7;
                    color: #92400e;
                }
                
                .badge-status.badge-archived {
                    background: #f3f4f6;
                    color: #6b7280;
                }

                .badge-hitl {
                    min-width: 36px;
                    text-align: center;
                }

                .badge-hitl-on {
                    background: #dcfce7;
                    color: #166534;
                    border: 1px solid #86efac;
                }

                .badge-hitl-off {
                    background: #f3f4f6;
                    color: #6b7280;
                    border: 1px solid #e5e7eb;
                }

                .badge-approval-yes {
                    background: #fef3c7;
                    color: #92400e;
                    border: 1px solid #fcd34d;
                }

                .badge-approval-no {
                    background: #e5f7ef;
                    color: #0f766e;
                    border: 1px solid #99f6e4;
                }
                
                .action-buttons {
                    display: flex;
                    gap: 0.5rem;
                    align-items: center;
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
                
                .btn-pause, .btn-archive, .btn-resume, .btn-unarchive {
                    padding: 6px 10px;
                    border-radius: var(--radius-sm);
                    font-size: 14px;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                    border: 1px solid transparent;
                    background: var(--bg-input);
                }
                
                .btn-pause:hover { background: #fef3c7; border-color: #f59e0b; }
                .btn-archive:hover { background: #f3f4f6; border-color: #6b7280; }
                .btn-resume:hover { background: #dcfce7; border-color: #22c55e; }
                .btn-unarchive:hover { background: #dbeafe; border-color: #3b82f6; }
                
                /* Modal Styles */
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                }
                
                .modal {
                    background: white;
                    border-radius: 16px;
                    width: 90%;
                    max-width: 450px;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                }
                
                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1.25rem 1.5rem;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                .modal-header h2 {
                    font-size: 1.25rem;
                    color: #1e293b;
                    margin: 0;
                }
                
                .close-btn {
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    color: #64748b;
                    cursor: pointer;
                }
                
                .modal-body {
                    padding: 1.5rem;
                }
                
                .project-name {
                    font-weight: 600;
                    color: #1e293b;
                    margin-bottom: 0.5rem;
                }
                
                .action-description {
                    color: #64748b;
                    font-size: 0.9rem;
                    margin-bottom: 1rem;
                }
                
                .form-group {
                    margin-bottom: 1rem;
                }
                
                .form-group label {
                    display: block;
                    margin-bottom: 0.5rem;
                    font-weight: 500;
                    color: #1e293b;
                }
                
                .form-group textarea {
                    width: 100%;
                    padding: 0.75rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 1rem;
                    resize: vertical;
                    font-family: inherit;
                    box-sizing: border-box;
                }
                
                .modal-actions {
                    display: flex;
                    gap: 1rem;
                    padding: 1rem 1.5rem;
                    border-top: 1px solid #e2e8f0;
                }
                
                .modal-actions button {
                    flex: 1;
                    padding: 0.75rem;
                    border-radius: 8px;
                    font-weight: 500;
                    cursor: pointer;
                }
                
                .btn-secondary {
                    background: #f1f5f9;
                    color: #1e293b;
                    border: 1px solid #e2e8f0;
                }
                
                .btn-warning {
                    background: #f59e0b;
                    color: white;
                    border: none;
                }
                
                .btn-danger {
                    background: #ef4444;
                    color: white;
                    border: none;
                }
                
                .btn-secondary:hover { background: #e2e8f0; }
                .btn-warning:hover { background: #d97706; }
                .btn-danger:hover { background: #dc2626; }
                
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

                /* My Projects Section */
                .my-projects-section {
                    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                    border-radius: 16px;
                    padding: 1.5rem;
                    margin-bottom: 2rem;
                    border: 1px solid #bae6fd;
                }

                .my-projects-section h2 {
                    margin: 0 0 1rem 0;
                    color: #0369a1;
                    font-size: 1.25rem;
                }

                .my-projects-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 1rem;
                }

                .my-project-card {
                    background: white;
                    border-radius: 12px;
                    padding: 1rem;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    border: 1px solid #e2e8f0;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }

                .my-project-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
                    border-color: #3b82f6;
                }

                .project-card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 0.5rem;
                }

                .project-card-header h3 {
                    margin: 0;
                    font-size: 1rem;
                    color: #1e293b;
                }

                .client-name {
                    color: #64748b;
                    font-size: 0.9rem;
                    margin: 0 0 0.75rem 0;
                }

                .project-card-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .my-role-badge {
                    font-size: 0.75rem;
                    color: #0369a1;
                    background: #e0f2fe;
                    padding: 0.25rem 0.5rem;
                    border-radius: 6px;
                }

                .no-projects {
                    color: #64748b;
                    font-style: italic;
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 1rem;
                }

                /* All Projects Header */
                .all-projects-header {
                    margin-bottom: 1rem;
                }

                .all-projects-header h2 {
                    margin: 0 0 0.25rem 0;
                    font-size: 1.25rem;
                    color: #1e293b;
                }

                .backlog-note {
                    color: #64748b;
                    font-size: 0.9rem;
                    margin: 0;
                }

                /* Table enhancements */
                .my-project-row {
                    background: #f0fdf4 !important;
                }

                .owned-badge {
                    color: #f59e0b;
                    margin-left: 0.5rem;
                    font-size: 0.9rem;
                }

                .assigned-to-me {
                    color: #22c55e;
                    font-weight: 500;
                    font-size: 0.85rem;
                }

                .not-assigned {
                    color: #94a3b8;
                }

                /* User info cells */
                .cell-user {
                    min-width: 120px;
                }

                .user-info-cell {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }

                .user-info-cell .user-name {
                    font-weight: 500;
                    color: #1e293b;
                    font-size: 0.9rem;
                }

                .user-info-cell .user-role {
                    font-size: 0.75rem;
                    color: #64748b;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                /* My role tags */
                @media (max-width: 768px) {
                    .page-header {
                        flex-direction: column;
                        gap: var(--space-lg);
                        text-align: center;
                    }

                    .my-projects-grid {
                        grid-template-columns: 1fr;
                    }
                }
            `}</style>
        </div>
        </RequireCapability>
    );
}
