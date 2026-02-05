'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';

interface ProjectDelayStatus {
  project_id: string;
  project_title: string;
  client_name: string;
  current_stage: string;
  is_delayed: boolean;
  delay_reason: string | null;
  days_in_stage: number;
  sla_days: number;
  status: 'ON_TRACK' | 'WARNING' | 'CRITICAL' | 'DELAYED';
}

interface Project {
  id: string;
  title: string;
  client_name: string;
  current_stage: string;
  status: string;
  priority: string;
  created_at?: string;
}

interface ExecutiveDashboard {
  total_projects: number;
  on_track_count: number;
  warning_count: number;
  critical_count: number;
  delayed_count: number;
  projects_by_stage: Record<string, number>;
  delayed_projects: ProjectDelayStatus[];
}



const STAGE_LABELS: Record<string, string> = {
  SALES: 'Sales Handover',
  ONBOARDING: 'Onboarding',
  ASSIGNMENT: 'Assignment',
  BUILD: 'Build',
  TEST: 'Test',
  DEFECT_VALIDATION: 'Defect Validation',
  COMPLETE: 'Complete'
};

const STAGE_ICONS: Record<string, string> = {
  SALES: '🤝',
  ONBOARDING: '📋',
  ASSIGNMENT: '📤',
  BUILD: '🔨',
  TEST: '🧪',
  DEFECT_VALIDATION: '🔍',
  COMPLETE: '✅'
};

const STAGE_ORDER = ['SALES', 'ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE'];

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  ON_TRACK: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
  WARNING: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
  CRITICAL: { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' },
  DELAYED: { bg: '#fecaca', text: '#7f1d1d', border: '#f87171' }
};

export default function ExecutiveDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<ExecutiveDashboard | null>(null);


  // New state for expandable sections
  const [allProjects, setAllProjects] = useState<Project[]>([]);
  const [expandedHealthStatus, setExpandedHealthStatus] = useState<string | null>(null);
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');

    if (!userData || !token) {
      router.push('/login');
      return;
    }

    const parsed = JSON.parse(userData);
    if (parsed.role !== 'ADMIN') {
      router.push('/dashboard');
      return;
    }

    setUser(parsed);
    loadData();
  }, [router]);

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

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashboardRes, projectsRes] = await Promise.all([
        fetch(`${getApiUrl()}/sla/executive-dashboard`, { headers: getAuthHeaders() }),
        fetch(`${getApiUrl()}/projects/`, { headers: getAuthHeaders() })
      ]);

      if (dashboardRes.ok) {
        setDashboard(await dashboardRes.json());
      }
      if (projectsRes.ok) {
        setAllProjects(await projectsRes.json());
      }
    } catch (error) {
      console.error('Failed to load executive dashboard:', error);
    } finally {
      setLoading(false);
    }
  };



  const toggleHealthStatus = (status: string) => {
    setExpandedHealthStatus(expandedHealthStatus === status ? null : status);
    setExpandedStage(null); // Close stage panel if open
  };

  const toggleStage = (stage: string) => {
    setExpandedStage(expandedStage === stage ? null : stage);
    setExpandedHealthStatus(null); // Close health panel if open
  };

  const getProjectsByHealthStatus = (status: string): Project[] => {
    if (!dashboard || !allProjects.length) return [];

    const delayedProjectIds = dashboard.delayed_projects
      .filter(p => p.status === status)
      .map(p => p.project_id);

    if (status === 'ON_TRACK') {
      // Projects not in delayed list
      const delayedIds = dashboard.delayed_projects.map(p => p.project_id);
      return allProjects.filter(p => !delayedIds.includes(p.id));
    }

    return allProjects.filter(p => delayedProjectIds.includes(p.id));
  };

  const getProjectsByStage = (stage: string): Project[] => {
    return allProjects.filter(p => p.current_stage === stage);
  };

  if (loading || !user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="spinner" />
      </div>
    );
  }

  const healthPercentage = dashboard ?
    Math.round(((dashboard.on_track_count) / (dashboard.total_projects || 1)) * 100) : 0;

  return (
    <div className="page-container">
      <Navigation />

      <main className="main-content">
        <div className="page-header">
          <div>
            <h1>📊 Dashboard</h1>
            <p>Project health overview and SLA management</p>
          </div>
          <button className="btn-refresh" onClick={loadData}>🔄 Refresh</button>
        </div>

        {/* Health Overview */}
        <section className="health-section">
          <h2>Portfolio Health</h2>
          <div className="health-grid">
            <div className="health-card main">
              <div className="health-ring" style={{ '--percentage': healthPercentage } as React.CSSProperties}>
                <span className="health-value">{healthPercentage}%</span>
              </div>
              <div className="health-label">Overall Health</div>
              <div className="health-sub">{dashboard?.total_projects || 0} Total Projects</div>
            </div>

            <div className="status-cards">
              <div
                className={`status-card on-track clickable ${expandedHealthStatus === 'ON_TRACK' ? 'selected' : ''}`}
                onClick={() => toggleHealthStatus('ON_TRACK')}
              >
                <span className="status-icon">✅</span>
                <span className="status-count">{dashboard?.on_track_count || 0}</span>
                <span className="status-label">On Track</span>
              </div>
              <div
                className={`status-card warning clickable ${expandedHealthStatus === 'WARNING' ? 'selected' : ''}`}
                onClick={() => toggleHealthStatus('WARNING')}
              >
                <span className="status-icon">⚠️</span>
                <span className="status-count">{dashboard?.warning_count || 0}</span>
                <span className="status-label">Warning</span>
              </div>
              <div
                className={`status-card critical clickable ${expandedHealthStatus === 'CRITICAL' ? 'selected' : ''}`}
                onClick={() => toggleHealthStatus('CRITICAL')}
              >
                <span className="status-icon">🚨</span>
                <span className="status-count">{dashboard?.critical_count || 0}</span>
                <span className="status-label">Critical</span>
              </div>
              <div
                className={`status-card delayed clickable ${expandedHealthStatus === 'DELAYED' ? 'selected' : ''}`}
                onClick={() => toggleHealthStatus('DELAYED')}
              >
                <span className="status-icon">❌</span>
                <span className="status-count">{dashboard?.delayed_count || 0}</span>
                <span className="status-label">Delayed</span>
              </div>
            </div>
          </div>

          {/* Expanded Health Status Projects */}
          {expandedHealthStatus && (
            <div className="expanded-projects">
              <h3>
                {expandedHealthStatus === 'ON_TRACK' && `✅ On Track Projects (${getProjectsByHealthStatus('ON_TRACK').length})`}
                {expandedHealthStatus === 'WARNING' && `⚠️ Warning Projects (${getProjectsByHealthStatus('WARNING').length})`}
                {expandedHealthStatus === 'CRITICAL' && `🚨 Critical Projects (${getProjectsByHealthStatus('CRITICAL').length})`}
                {expandedHealthStatus === 'DELAYED' && `❌ Delayed Projects (${getProjectsByHealthStatus('DELAYED').length})`}
              </h3>
              <div className="project-list">
                {getProjectsByHealthStatus(expandedHealthStatus).map(project => (
                  <div
                    key={project.id}
                    className="project-list-item"
                    onClick={() => router.push(`/projects/${project.id}`)}
                  >
                    <div className="project-info">
                      <span className="project-title">{project.title}</span>
                      <span className="project-client">{project.client_name}</span>
                    </div>
                    <div className="project-badges">
                      <span className={`badge badge-priority badge-${project.priority?.toLowerCase()}`}>
                        {project.priority}
                      </span>
                      <span className="badge badge-stage">{STAGE_LABELS[project.current_stage]}</span>
                    </div>
                  </div>
                ))}
                {getProjectsByHealthStatus(expandedHealthStatus).length === 0 && (
                  <p className="no-projects">No projects in this category</p>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Pipeline Stages - Card View */}
        <section className="pipeline-section">
          <h2>Project Stages</h2>
          <div className="pipeline-cards">
            {STAGE_ORDER.map((stage) => {
              const count = dashboard?.projects_by_stage[stage] || 0;
              const projects = getProjectsByStage(stage);
              return (
                <div
                  key={stage}
                  className={`pipeline-card ${expandedStage === stage ? 'selected' : ''} ${count > 0 ? 'clickable' : ''}`}
                  onClick={() => count > 0 && toggleStage(stage)}
                >
                  <div className="pipeline-icon">{STAGE_ICONS[stage]}</div>
                  <div className="pipeline-count">{count}</div>
                  <div className="pipeline-label">{STAGE_LABELS[stage]}</div>
                  <div className="pipeline-bar">
                    <div
                      className="pipeline-bar-fill"
                      style={{ width: `${(count / (dashboard?.total_projects || 1)) * 100}%` }}
                    />
                  </div>
                  {projects.length > 0 && (
                    <div className="pipeline-projects-preview">
                      {projects.slice(0, 2).map(p => p.title).join(', ')}
                      {projects.length > 2 && ` +${projects.length - 2} more`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Expanded Stage Projects */}
          {expandedStage && (
            <div className="expanded-projects">
              <h3>{STAGE_ICONS[expandedStage]} {STAGE_LABELS[expandedStage]} Projects ({getProjectsByStage(expandedStage).length})</h3>
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
                    {getProjectsByStage(expandedStage).map((project) => (
                      <tr key={project.id}>
                        <td className="cell-title">{project.title}</td>
                        <td>{project.client_name}</td>
                        <td>
                          <span className={`badge badge-priority badge-${project.priority?.toLowerCase()}`}>
                            {project.priority}
                          </span>
                        </td>
                        <td className="cell-date">
                          {project.created_at ? new Date(project.created_at).toLocaleDateString() : '-'}
                        </td>
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
            </div>
          )}
        </section>

        {/* At-Risk Projects */}
        {dashboard && dashboard.delayed_projects.length > 0 && (
          <section className="risk-section">
            <h2>⚠️ Projects Requiring Attention</h2>
            <div className="risk-table">
              <table>
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Client</th>
                    <th>Stage</th>
                    <th>Days in Stage</th>
                    <th>SLA</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.delayed_projects.map((project) => (
                    <tr
                      key={project.project_id}
                      className="clickable-row"
                      onClick={() => router.push(`/projects/${project.project_id}`)}
                    >
                      <td className="cell-title">{project.project_title}</td>
                      <td>{project.client_name}</td>
                      <td>{STAGE_LABELS[project.current_stage] || project.current_stage}</td>
                      <td>{project.days_in_stage} days</td>
                      <td>{project.sla_days} days</td>
                      <td>
                        <span
                          className="status-badge"
                          style={{
                            backgroundColor: STATUS_COLORS[project.status].bg,
                            color: STATUS_COLORS[project.status].text,
                            borderColor: STATUS_COLORS[project.status].border
                          }}
                        >
                          {project.status.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}


      </main>

      <style jsx>{`
        .page-container { min-height: 100vh; background: #f8fafc; }
        .main-content { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        
        .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        .page-header h1 { font-size: 1.75rem; color: #1e293b; margin-bottom: 0.25rem; }
        .page-header p { color: #64748b; }
        .btn-refresh { padding: 0.5rem 1rem; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; }
        
        section { margin-bottom: 2rem; background: #ffffff; border-radius: 12px; padding: 1.5rem; border: 1px solid #e2e8f0; }
        section h2 { font-size: 1.1rem; color: #1e293b; margin-bottom: 1rem; }
        
        .health-grid { display: grid; grid-template-columns: 200px 1fr; gap: 2rem; align-items: center; }
        .health-card.main { text-align: center; }
        .health-ring { width: 150px; height: 150px; border-radius: 50%; background: conic-gradient(#22c55e calc(var(--percentage) * 1%), #e2e8f0 0); display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; position: relative; }
        .health-ring::before { content: ''; position: absolute; width: 120px; height: 120px; background: white; border-radius: 50%; }
        .health-value { position: relative; font-size: 2rem; font-weight: 700; color: #1e293b; }
        .health-label { font-weight: 600; color: #1e293b; }
        .health-sub { font-size: 0.85rem; color: #64748b; }
        
        .status-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
        .status-card { padding: 1.5rem; border-radius: 12px; text-align: center; transition: all 0.2s; }
        .status-card.clickable { cursor: pointer; }
        .status-card.clickable:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .status-card.selected { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); outline: 3px solid #3b82f6; }
        .status-card.on-track { background: #dcfce7; }
        .status-card.warning { background: #fef3c7; }
        .status-card.critical { background: #fee2e2; }
        .status-card.delayed { background: #fecaca; }
        .status-icon { font-size: 1.5rem; display: block; margin-bottom: 0.5rem; }
        .status-count { font-size: 2rem; font-weight: 700; display: block; color: #1e293b; }
        .status-label { font-size: 0.85rem; color: #64748b; }
        
        /* Expanded Projects Panel */
        .expanded-projects { margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; animation: slideDown 0.3s ease; }
        .expanded-projects h3 { font-size: 1rem; margin-bottom: 1rem; color: #1e293b; }
        .project-list { display: flex; flex-direction: column; gap: 0.5rem; }
        .project-list-header { display: grid; grid-template-columns: 2fr 2fr 1fr 1fr; gap: 1rem; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.04em; padding: 0 0.25rem; }
        .project-list-header span:last-child { text-align: right; }
        .project-list-item { display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: #f8fafc; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .project-list-item:hover { background: #e0f2fe; transform: translateX(4px); }
        .project-info { display: flex; flex-direction: column; gap: 0.25rem; }
        .project-title { font-weight: 600; color: #1e293b; }
        .project-client { font-size: 0.85rem; color: #64748b; }
        .project-badges { display: flex; gap: 0.5rem; }
        .badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 500; }
        .badge-priority { background: #f1f5f9; color: #475569; }
        .badge-priority.badge-high { background: #fee2e2; color: #991b1b; }
        .badge-priority.badge-critical { background: #fecaca; color: #7f1d1d; }
        .badge-priority.badge-medium { background: #fef3c7; color: #92400e; }
        .badge-priority.badge-low { background: #dcfce7; color: #166534; }
        .badge-stage { background: #e0f2fe; color: #0369a1; }
        .badge-status { background: #f1f5f9; color: #475569; }
        .badge-status.badge-active { background: #dcfce7; color: #166534; }
        .badge-status.badge-draft { background: #fef3c7; color: #92400e; }
        .no-projects { color: #64748b; font-style: italic; text-align: center; padding: 1rem; }
        
        @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Pipeline Stages */
        .pipeline-section { }
        .pipeline-cards { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1rem; }
        .pipeline-card { background: #f8fafc; border-radius: 12px; padding: 1.25rem; text-align: center; transition: all 0.2s; border: 2px solid transparent; }
        .pipeline-card.clickable { cursor: pointer; }
        .pipeline-card.clickable:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-color: #3b82f6; }
        .pipeline-card.selected { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-color: #3b82f6; background: #eff6ff; }
        .pipeline-icon { font-size: 2rem; margin-bottom: 0.5rem; }
        .pipeline-count { font-size: 1.75rem; font-weight: 700; color: #1e293b; }
        .pipeline-label { font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem; }
        .pipeline-bar { height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; margin-bottom: 0.5rem; }
        .pipeline-bar-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 2px; }
        .pipeline-projects-preview { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        
        .risk-table { overflow-x: auto; }
        .projects-table { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 0.75rem; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #64748b; border-bottom: 1px solid #e2e8f0; }
        td { padding: 0.75rem; border-bottom: 1px solid #f1f5f9; }
        .clickable-row { cursor: pointer; transition: background 0.2s; }
        .clickable-row:hover { background: #f8fafc; }
        .cell-title { font-weight: 500; color: #1e293b; }
        .cell-date { font-size: 0.85rem; color: #64748b; }
        .status-badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 500; border: 1px solid; }
        .btn-view { padding: 6px 14px; background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; border-radius: 6px; font-size: 0.75rem; font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .btn-view:hover { background: #0ea5e9; color: white; border-color: #0ea5e9; }
        
        @media (max-width: 1024px) {
          .pipeline-cards { grid-template-columns: repeat(3, 1fr); }
        }
        
        @media (max-width: 768px) {
          .health-grid { grid-template-columns: 1fr; }
          .status-cards { grid-template-columns: repeat(2, 1fr); }
          .pipeline-cards { grid-template-columns: repeat(2, 1fr); }
        }
      `}</style>
    </div>
  );
}
