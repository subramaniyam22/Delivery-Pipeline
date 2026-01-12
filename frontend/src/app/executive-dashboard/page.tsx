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

interface ExecutiveDashboard {
  total_projects: number;
  on_track_count: number;
  warning_count: number;
  critical_count: number;
  delayed_count: number;
  projects_by_stage: Record<string, number>;
  delayed_projects: ProjectDelayStatus[];
}

interface SLAConfig {
  id: string;
  stage: string;
  default_days: number;
  warning_threshold_days: number;
  critical_threshold_days: number;
  description: string;
  is_active: boolean;
}

const STAGE_LABELS: Record<string, string> = {
  ONBOARDING: 'Onboarding',
  ASSIGNMENT: 'Assignment',
  BUILD: 'Build',
  TEST: 'Test',
  DEFECT_VALIDATION: 'Defect Validation',
  COMPLETE: 'Complete'
};

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
  const [slaConfigs, setSlaConfigs] = useState<SLAConfig[]>([]);
  const [editingSLA, setEditingSLA] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ default_days: 0, warning_threshold_days: 0, critical_threshold_days: 0 });

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
      const [dashboardRes, slaRes] = await Promise.all([
        fetch(`${getApiUrl()}/sla/executive-dashboard`, { headers: getAuthHeaders() }),
        fetch(`${getApiUrl()}/sla/configurations`, { headers: getAuthHeaders() })
      ]);
      
      if (dashboardRes.ok) {
        setDashboard(await dashboardRes.json());
      }
      if (slaRes.ok) {
        setSlaConfigs(await slaRes.json());
      }
    } catch (error) {
      console.error('Failed to load executive dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSLAUpdate = async (stage: string) => {
    try {
      const response = await fetch(`${getApiUrl()}/sla/configurations/${stage}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(editForm)
      });
      
      if (response.ok) {
        setEditingSLA(null);
        loadData();
      }
    } catch (error) {
      console.error('Failed to update SLA:', error);
    }
  };

  const startEditing = (config: SLAConfig) => {
    setEditingSLA(config.stage);
    setEditForm({
      default_days: config.default_days,
      warning_threshold_days: config.warning_threshold_days,
      critical_threshold_days: config.critical_threshold_days
    });
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
            <h1>📊 Executive Dashboard</h1>
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
              <div className="status-card on-track">
                <span className="status-icon">✅</span>
                <span className="status-count">{dashboard?.on_track_count || 0}</span>
                <span className="status-label">On Track</span>
              </div>
              <div className="status-card warning">
                <span className="status-icon">⚠️</span>
                <span className="status-count">{dashboard?.warning_count || 0}</span>
                <span className="status-label">Warning</span>
              </div>
              <div className="status-card critical">
                <span className="status-icon">🚨</span>
                <span className="status-count">{dashboard?.critical_count || 0}</span>
                <span className="status-label">Critical</span>
              </div>
              <div className="status-card delayed">
                <span className="status-icon">❌</span>
                <span className="status-count">{dashboard?.delayed_count || 0}</span>
                <span className="status-label">Delayed</span>
              </div>
            </div>
          </div>
        </section>

        {/* Projects by Stage */}
        <section className="stage-section">
          <h2>Projects by Stage</h2>
          <div className="stage-bars">
            {Object.entries(dashboard?.projects_by_stage || {}).map(([stage, count]) => (
              <div key={stage} className="stage-bar-item">
                <div className="stage-bar-label">
                  <span>{STAGE_LABELS[stage] || stage}</span>
                  <span className="stage-count">{count}</span>
                </div>
                <div className="stage-bar-track">
                  <div 
                    className="stage-bar-fill" 
                    style={{ width: `${(count / (dashboard?.total_projects || 1)) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
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
                    <tr key={project.project_id}>
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

        {/* SLA Configuration */}
        <section className="sla-section">
          <h2>⚙️ SLA Configuration</h2>
          <p className="sla-desc">Configure the default time limits for each project phase</p>
          <div className="sla-grid">
            {slaConfigs.map((config) => (
              <div key={config.stage} className="sla-card">
                {editingSLA === config.stage ? (
                  <div className="sla-edit">
                    <h3>{STAGE_LABELS[config.stage] || config.stage}</h3>
                    <div className="edit-fields">
                      <label>
                        Default Days
                        <input 
                          type="number" 
                          value={editForm.default_days}
                          onChange={(e) => setEditForm({...editForm, default_days: parseInt(e.target.value)})}
                        />
                      </label>
                      <label>
                        Warning (days before)
                        <input 
                          type="number" 
                          value={editForm.warning_threshold_days}
                          onChange={(e) => setEditForm({...editForm, warning_threshold_days: parseInt(e.target.value)})}
                        />
                      </label>
                      <label>
                        Critical (days before)
                        <input 
                          type="number" 
                          value={editForm.critical_threshold_days}
                          onChange={(e) => setEditForm({...editForm, critical_threshold_days: parseInt(e.target.value)})}
                        />
                      </label>
                    </div>
                    <div className="edit-actions">
                      <button className="btn-cancel" onClick={() => setEditingSLA(null)}>Cancel</button>
                      <button className="btn-save" onClick={() => handleSLAUpdate(config.stage)}>Save</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="sla-header">
                      <h3>{STAGE_LABELS[config.stage] || config.stage}</h3>
                      <button className="btn-edit" onClick={() => startEditing(config)}>✏️</button>
                    </div>
                    <div className="sla-value">{config.default_days} days</div>
                    <div className="sla-thresholds">
                      <span className="threshold warning">⚠️ {config.warning_threshold_days}d</span>
                      <span className="threshold critical">🚨 {config.critical_threshold_days}d</span>
                    </div>
                    {config.description && <p className="sla-description">{config.description}</p>}
                  </>
                )}
              </div>
            ))}
          </div>
        </section>
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
        .status-card { padding: 1.5rem; border-radius: 12px; text-align: center; }
        .status-card.on-track { background: #dcfce7; }
        .status-card.warning { background: #fef3c7; }
        .status-card.critical { background: #fee2e2; }
        .status-card.delayed { background: #fecaca; }
        .status-icon { font-size: 1.5rem; display: block; margin-bottom: 0.5rem; }
        .status-count { font-size: 2rem; font-weight: 700; display: block; color: #1e293b; }
        .status-label { font-size: 0.85rem; color: #64748b; }
        
        .stage-bars { display: flex; flex-direction: column; gap: 1rem; }
        .stage-bar-item { }
        .stage-bar-label { display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem; }
        .stage-count { font-weight: 600; color: #2563eb; }
        .stage-bar-track { height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }
        .stage-bar-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 4px; transition: width 0.5s; }
        
        .risk-table { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 0.75rem; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #64748b; border-bottom: 1px solid #e2e8f0; }
        td { padding: 0.75rem; border-bottom: 1px solid #f1f5f9; }
        .cell-title { font-weight: 500; color: #1e293b; }
        .status-badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 500; border: 1px solid; }
        
        .sla-desc { color: #64748b; font-size: 0.9rem; margin-bottom: 1rem; }
        .sla-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
        .sla-card { background: #f8fafc; border-radius: 12px; padding: 1.25rem; border: 1px solid #e2e8f0; }
        .sla-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .sla-header h3 { font-size: 1rem; color: #1e293b; margin: 0; }
        .btn-edit { background: none; border: none; cursor: pointer; font-size: 1rem; }
        .sla-value { font-size: 1.75rem; font-weight: 700; color: #2563eb; margin-bottom: 0.5rem; }
        .sla-thresholds { display: flex; gap: 1rem; }
        .threshold { font-size: 0.8rem; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .threshold.warning { background: #fef3c7; color: #92400e; }
        .threshold.critical { background: #fee2e2; color: #991b1b; }
        .sla-description { font-size: 0.8rem; color: #64748b; margin-top: 0.5rem; }
        
        .sla-edit h3 { margin-bottom: 1rem; }
        .edit-fields { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1rem; }
        .edit-fields label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.85rem; color: #64748b; }
        .edit-fields input { padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 1rem; }
        .edit-actions { display: flex; gap: 0.5rem; }
        .btn-cancel { flex: 1; padding: 0.5rem; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; }
        .btn-save { flex: 1; padding: 0.5rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
        
        @media (max-width: 768px) {
          .health-grid { grid-template-columns: 1fr; }
          .status-cards { grid-template-columns: repeat(2, 1fr); }
        }
      `}</style>
    </div>
  );
}
