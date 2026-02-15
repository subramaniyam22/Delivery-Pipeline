'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { projectsAPI, configurationAPI, metricsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import PageHeader from '@/components/PageHeader';
import Breadcrumbs from '@/components/Breadcrumbs';

export default function DashboardPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [projects, setProjects] = useState<any[]>([]);
    const [user, setUser] = useState<any>(null);
    const [executiveDashboard, setExecutiveDashboard] = useState<any>(null);
    const [metrics, setMetrics] = useState<any>(null);
    const [templatesWithPerf, setTemplatesWithPerf] = useState<any[]>([]);
    const [expandedHealthStatus, setExpandedHealthStatus] = useState<string | null>(null);
    const [expandedStage, setExpandedStage] = useState<string | null>(null);
    const STAGE_LABELS: Record<string, string> = { SALES: 'Sales Handover', ONBOARDING: 'Onboarding', ASSIGNMENT: 'Assignment', BUILD: 'Build', TEST: 'Test', DEFECT_VALIDATION: 'Defect Validation', COMPLETE: 'Complete' };
    const STAGE_ICONS: Record<string, string> = { SALES: '🤝', ONBOARDING: '📋', ASSIGNMENT: '📤', BUILD: '🔨', TEST: '🧪', DEFECT_VALIDATION: '🔍', COMPLETE: '✅' };
    const STAGE_ORDER = ['SALES', 'ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE'];
    const getProjectsByHealthStatus = (status: string): any[] => {
        if (!executiveDashboard?.delayed_projects?.length || !projects.length) return status === 'ON_TRACK' ? projects : [];
        const delayedIds = executiveDashboard.delayed_projects.map((p: any) => p.project_id);
        if (status === 'ON_TRACK') return projects.filter((p: any) => !delayedIds.includes(p.id));
        return projects.filter((p: any) => executiveDashboard.delayed_projects.some((d: any) => d.project_id === p.id && d.status === status));
    };
    const getProjectsByStage = (stage: string): any[] => projects.filter((p: any) => p.current_stage === stage);
    type Widget = {
        title: string;
        value: string;
        subtitle: string;
        href?: string;
        placeholder?: boolean;
    };

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        const currentUser = getCurrentUser();
        setUser(currentUser);

        loadProjects(currentUser);
    }, [router]);

    const loadProjects = async (currentUser: any) => {
        try {
            const params: Record<string, any> = {};
            if (currentUser?.role === 'SALES' || currentUser?.role === 'CONSULTANT') {
                params.mine = true;
            }
            if (currentUser?.role === 'BUILDER') {
                params.assigned = true;
                params.stage = 'BUILD';
            }
            if (currentUser?.role === 'TESTER') {
                params.assigned = true;
                params.stage = 'TEST';
            }
            if (currentUser?.role === 'PC') {
                params.stage = 'ASSIGNMENT';
                params.needs_assignment = true;
            }
            const response = await projectsAPI.list(params);
            setProjects(response.data || []);

            if (currentUser?.role === 'ADMIN' || currentUser?.role === 'MANAGER') {
                try {
                    const [dashboardRes, metricsRes, templatesRes] = await Promise.all([
                        configurationAPI.getExecutiveDashboard(),
                        metricsAPI.get(),
                        configurationAPI.getTemplates(),
                    ]);
                    setExecutiveDashboard(dashboardRes.data ?? null);
                    setMetrics(metricsRes.data ?? null);
                    setTemplatesWithPerf(Array.isArray(templatesRes?.data) ? templatesRes.data : []);
                } catch (e) {
                    console.error('Failed to load dashboard metrics:', e);
                }
            }
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const getWidgetsForRole = (): Widget[] => {
        const role = user?.role;
        const statusCounts = {
            active: projects.filter((p) => p.status === 'ACTIVE').length,
            draft: projects.filter((p) => p.status === 'DRAFT').length,
            paused: projects.filter((p) => p.status === 'PAUSED').length,
            complete: projects.filter((p) => p.status === 'COMPLETED' || p.current_stage === 'COMPLETE').length,
        };

        if (role === 'SALES') {
            const salesRevenueUsd = projects.reduce((s: number, p: any) => s + (Number(p.estimated_revenue_usd) || 0), 0);
            const salesRevenueDisplay = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(salesRevenueUsd);
            return [
                {
                    title: 'My Projects',
                    value: String(projects.length),
                    subtitle: `Active ${statusCounts.active} • Draft ${statusCounts.draft} • Paused ${statusCounts.paused} • Complete ${statusCounts.complete}`,
                    href: '/projects?mine=true',
                },
                {
                    title: 'Revenue Generated',
                    value: salesRevenueDisplay,
                    subtitle: salesRevenueUsd > 0 ? 'Sum of project estimated revenue' : 'Add estimated revenue on projects',
                    placeholder: false,
                },
                {
                    title: 'Reviews Generated',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
            ];
        }

        if (role === 'CONSULTANT') {
            const onboardingPending = projects.filter((p) => p.current_stage === 'ONBOARDING').length;
            return [
                {
                    title: 'Onboarding Pending',
                    value: String(onboardingPending),
                    subtitle: 'Projects in onboarding',
                    href: '/projects?mine=true&stage=ONBOARDING',
                },
                {
                    title: 'Awaiting Client Review',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Escalations',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
            ];
        }

        if (role === 'PC') {
            const needsAssignment = projects.filter(
                (p) => p.current_stage === 'ASSIGNMENT' && !p.pc_user_id
            ).length;
            return [
                {
                    title: 'Capacity vs Load',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Projects Needing Assignment',
                    value: String(needsAssignment),
                    subtitle: 'Awaiting team assignment',
                    href: '/projects?stage=ASSIGNMENT&needs_assignment=true',
                },
                {
                    title: 'Blocked Items',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
            ];
        }

        if (role === 'BUILDER') {
            const buildQueue = projects.filter(
                (p) => p.current_stage === 'BUILD' && p.builder_user_id === user?.id
            ).length;
            return [
                {
                    title: 'My Build Queue',
                    value: String(buildQueue),
                    subtitle: 'Ready for build',
                    href: '/projects?assigned=true&stage=BUILD',
                },
                {
                    title: 'Defects Assigned to Me',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Due Today',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
            ];
        }

        if (role === 'TESTER') {
            const pendingTests = projects.filter(
                (p) => p.current_stage === 'TEST' && p.tester_user_id === user?.id
            ).length;
            return [
                {
                    title: 'Pending Tests',
                    value: String(pendingTests),
                    subtitle: 'Waiting for QA',
                    href: '/projects?assigned=true&stage=TEST',
                },
                {
                    title: 'Defects Ageing',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Retests Required',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
            ];
        }

        if (role === 'MANAGER') {
            const delayed = executiveDashboard?.delayed_count ?? 0;
            const hitlRate = metrics?.hitl_rate != null ? `${metrics.hitl_rate}%` : '—';
            const sentiment = metrics?.quality_metrics?.avg_client_sentiment != null
                ? String(metrics.quality_metrics.avg_client_sentiment)
                : '—';
            return [
                {
                    title: 'SLA Breaches',
                    value: String(delayed),
                    subtitle: executiveDashboard ? 'Delayed / at-risk projects' : 'Data source not connected yet',
                    href: '/dashboard#portfolio-health',
                    placeholder: !executiveDashboard,
                },
                {
                    title: 'HITL Approvals Pending',
                    value: hitlRate,
                    subtitle: metrics ? 'HITL rate from stage outputs' : 'Data source not connected yet',
                    placeholder: metrics == null,
                },
                {
                    title: 'Sentiment Dips',
                    value: sentiment,
                    subtitle: metrics ? 'Avg client sentiment score' : 'Data source not connected yet',
                    placeholder: metrics == null,
                },
            ];
        }

        if (role === 'ADMIN') {
            const total = executiveDashboard?.total_projects ?? projects.length;
            const onTrack = executiveDashboard?.on_track_count ?? 0;
            const warning = executiveDashboard?.warning_count ?? 0;
            const critical = executiveDashboard?.critical_count ?? 0;
            const delayed = executiveDashboard?.delayed_count ?? 0;
            const deliveryCount = projects.filter((p: any) => p.status === 'ACTIVE' && ['BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE'].includes(p.current_stage)).length;
            const backlogCount = projects.filter((p: any) => p.status === 'DRAFT' || p.current_stage === 'SALES').length;
            const inConversationCount = projects.filter((p: any) => p.current_stage === 'ONBOARDING').length;
            const pmcSet = new Set(projects.map((p: any) => p.pmc_name).filter(Boolean));
            const locationSet = new Set(projects.flatMap((p: any) => (Array.isArray(p.location_names) && p.location_names?.length ? p.location_names : (p.location ? [p.location] : []))));
            const byType: Record<string, number> = {};
            projects.forEach((p: any) => {
                const t = (p.project_type || 'Other').trim() || 'Other';
                byType[t] = (byType[t] || 0) + 1;
            });
            const typeSub = Object.entries(byType).map(([k, v]) => `${k}: ${v}`).join(' • ') || '—';
            const riskSub = executiveDashboard
                ? `On track: ${onTrack} • Warning: ${warning} • Critical: ${critical} • Delayed: ${delayed}`
                : '—';
            const sentiment = metrics?.quality_metrics?.avg_client_sentiment != null
                ? String(metrics.quality_metrics.avg_client_sentiment)
                : '—';
            const totalRevenueUsd = projects.reduce((s: number, p: any) => s + (Number(p.estimated_revenue_usd) || 0), 0);
            const revenueDisplay = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(totalRevenueUsd);
            return [
                { title: 'Revenue (USD)', value: revenueDisplay, subtitle: totalRevenueUsd > 0 ? 'Sum of project estimated revenue' : 'Connect revenue source or project values', placeholder: false },
                { title: 'Pipeline', value: `${deliveryCount} / ${backlogCount} / ${inConversationCount}`, subtitle: 'In delivery • In backlog • In conversation (sales/onboarding)', href: '/projects' },
                { title: 'PMCs & Locations', value: `${pmcSet.size} PMCs • ${locationSet.size} locations`, subtitle: 'Distinct PMCs and locations across projects', href: '/projects' },
                { title: 'Project types', value: Object.keys(byType).length ? Object.entries(byType).map(([k, v]) => `${k}: ${v}`).join(', ') : '—', subtitle: typeSub, href: '/projects' },
                { title: 'Delivery Health', value: executiveDashboard ? `${onTrack}/${total} on track` : '—', subtitle: riskSub, href: '#portfolio-health', placeholder: !executiveDashboard },
                { title: 'Risk / Focus', value: (warning + critical + delayed) > 0 ? `${warning + critical + delayed} need attention` : 'All on track', subtitle: `Warning: ${warning} • Critical: ${critical} • Delayed: ${delayed}`, href: '#portfolio-health' },
                { title: 'Sentiment Trend', value: sentiment, subtitle: metrics ? 'Avg client sentiment' : '—', placeholder: metrics == null },
            ];
        }

        return [
            {
                title: 'My Projects',
                value: String(projects.length),
                subtitle: 'Active work items',
                href: '/projects',
            },
        ];
    };

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
            <main className="dashboard-page">
                <Breadcrumbs />
                <PageHeader
                    title="Dashboard"
                    purpose={`Welcome back, ${user?.name || 'team'}! Here's your delivery pipeline overview.`}
                    variant="page"
                />

                <section className="your-focus-section">
                    <h2 className="your-focus-title">Your Focus</h2>
                    <div className="your-focus-table-wrap">
                        <table className="your-focus-table">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Value</th>
                                    <th>Details</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {getWidgetsForRole().map((widget) => {
                                    const isClickable = widget.href && !widget.placeholder;
                                    return (
                                        <tr
                                            key={widget.title}
                                            className={isClickable ? 'focus-row--clickable' : ''}
                                            onClick={isClickable ? () => router.push(widget.href!) : undefined}
                                            role={isClickable ? 'button' : undefined}
                                        >
                                            <td className="focus-cell focus-cell--metric">{widget.title}</td>
                                            <td className="focus-cell focus-cell--value">{widget.value}</td>
                                            <td className="focus-cell focus-cell--details">{widget.subtitle}</td>
                                            <td className="focus-cell focus-cell--action">
                                                {isClickable ? (
                                                    <span className="focus-link">View →</span>
                                                ) : (
                                                    <span className="focus-link focus-link--muted">—</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </section>

                {(user?.role === 'ADMIN') && executiveDashboard && (
                    <section className="dashboard-portfolio-section" id="portfolio-health" style={{ marginTop: '2rem', marginBottom: '2rem', background: '#fff', borderRadius: 12, padding: '1.5rem', border: '1px solid #e2e8f0' }}>
                        <h2 className="your-focus-title">Portfolio Health</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '2rem', alignItems: 'center' }}>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ width: 150, height: 150, borderRadius: '50%', background: `conic-gradient(#22c55e ${((executiveDashboard.on_track_count || 0) / (executiveDashboard.total_projects || 1)) * 100}%, #e2e8f0 0)`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
                                    <span style={{ position: 'relative', fontSize: '2rem', fontWeight: 700 }}>{Math.round(((executiveDashboard.on_track_count || 0) / (executiveDashboard.total_projects || 1)) * 100)}%</span>
                                </div>
                                <div style={{ fontWeight: 600 }}>Overall Health</div>
                                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{executiveDashboard.total_projects || 0} Total Projects</div>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                                {(['ON_TRACK', 'WARNING', 'CRITICAL', 'DELAYED'] as const).map((status) => (
                                    <div key={status} role="button" tabIndex={0} onClick={() => { setExpandedStage(null); setExpandedHealthStatus(expandedHealthStatus === status ? null : status); }} style={{ padding: '1rem', borderRadius: 12, textAlign: 'center', cursor: 'pointer', background: status === 'ON_TRACK' ? '#dcfce7' : status === 'WARNING' ? '#fef3c7' : status === 'CRITICAL' ? '#fee2e2' : '#fecaca', border: expandedHealthStatus === status ? '3px solid #3b82f6' : '2px solid transparent' }}>
                                        <span style={{ display: 'block', marginBottom: '0.5rem' }}>{status === 'ON_TRACK' ? '✅' : status === 'WARNING' ? '⚠️' : status === 'CRITICAL' ? '🚨' : '❌'}</span>
                                        <span style={{ fontSize: '1.5rem', fontWeight: 700 }}>{status === 'ON_TRACK' ? executiveDashboard.on_track_count : status === 'WARNING' ? executiveDashboard.warning_count : status === 'CRITICAL' ? executiveDashboard.critical_count : executiveDashboard.delayed_count}</span>
                                        <span style={{ display: 'block', fontSize: '0.85rem', color: '#64748b' }}>{status.replace('_', ' ')}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        {expandedHealthStatus && (
                            <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
                                <h3 style={{ marginBottom: '1rem' }}>{expandedHealthStatus} Projects ({getProjectsByHealthStatus(expandedHealthStatus).length})</h3>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    {getProjectsByHealthStatus(expandedHealthStatus).map((project: any) => (
                                        <div key={project.id} role="button" onClick={() => router.push(`/projects/${project.id}`)} style={{ padding: '1rem', background: '#f8fafc', borderRadius: 8, cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div><strong>{project.title}</strong><br /><span style={{ fontSize: '0.85rem', color: '#64748b' }}>{project.client_name}</span></div>
                                            <span style={{ padding: '0.25rem 0.75rem', borderRadius: 20, fontSize: '0.75rem', background: '#e0f2fe', color: '#0369a1' }}>{STAGE_LABELS[project.current_stage] || project.current_stage}</span>
                                        </div>
                                    ))}
                                    {getProjectsByHealthStatus(expandedHealthStatus).length === 0 && <p style={{ color: '#64748b', fontStyle: 'italic' }}>No projects in this category</p>}
                                </div>
                            </div>
                        )}
                    </section>
                )}

                {(user?.role === 'ADMIN') && executiveDashboard && (
                    <section className="dashboard-stages-section" style={{ marginBottom: '2rem', background: '#fff', borderRadius: 12, padding: '1.5rem', border: '1px solid #e2e8f0' }}>
                        <h2 className="your-focus-title">Project Stages</h2>
                        <div className="dashboard-stages-grid">
                            {STAGE_ORDER.map((stage) => {
                                const count = executiveDashboard.projects_by_stage?.[stage] || 0;
                                const stageProjects = getProjectsByStage(stage);
                                return (
                                    <div key={stage} role="button" onClick={() => count > 0 && (setExpandedHealthStatus(null), setExpandedStage(expandedStage === stage ? null : stage))} style={{ padding: '1.25rem', background: '#f8fafc', borderRadius: 12, textAlign: 'center', cursor: count > 0 ? 'pointer' : 'default', border: expandedStage === stage ? '2px solid #3b82f6' : '2px solid transparent' }}>
                                        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{STAGE_ICONS[stage]}</div>
                                        <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{count}</div>
                                        <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '0.5rem' }}>{STAGE_LABELS[stage]}</div>
                                        <div style={{ height: 4, background: '#e2e8f0', borderRadius: 2, overflow: 'hidden' }}><div style={{ width: `${(count / (executiveDashboard.total_projects || 1)) * 100}%`, height: '100%', background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)', borderRadius: 2 }} /></div>
                                        {stageProjects.length > 0 && <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.5rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{stageProjects.slice(0, 2).map((p: any) => p.title).join(', ')}{stageProjects.length > 2 ? ` +${stageProjects.length - 2} more` : ''}</div>}
                                    </div>
                                );
                            })}
                        </div>
                        {expandedStage && (
                            <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
                                <h3 style={{ marginBottom: '1rem' }}>{STAGE_ICONS[expandedStage]} {STAGE_LABELS[expandedStage]} ({getProjectsByStage(expandedStage).length})</h3>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                                    <thead><tr style={{ borderBottom: '1px solid #e2e8f0' }}><th style={{ textAlign: 'left', padding: '0.75rem' }}>Project</th><th style={{ textAlign: 'left', padding: '0.75rem' }}>Client</th><th style={{ textAlign: 'left', padding: '0.75rem' }}>Priority</th><th style={{ textAlign: 'left', padding: '0.75rem' }}>Actions</th></tr></thead>
                                    <tbody>
                                        {getProjectsByStage(expandedStage).map((project: any) => (
                                            <tr key={project.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                <td style={{ padding: '0.75rem', fontWeight: 500 }}>{project.title}</td>
                                                <td style={{ padding: '0.75rem' }}>{project.client_name}</td>
                                                <td style={{ padding: '0.75rem' }}><span style={{ padding: '0.25rem 0.5rem', borderRadius: 20, fontSize: '0.75rem', background: '#f1f5f9' }}>{project.priority}</span></td>
                                                <td style={{ padding: '0.75rem' }}><button type="button" onClick={(e) => { e.stopPropagation(); router.push(`/projects/${project.id}`); }} style={{ padding: '6px 14px', background: '#e0f2fe', color: '#0369a1', border: '1px solid #bae6fd', borderRadius: 6, cursor: 'pointer' }}>View</button></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>
                )}

                {(user?.role === 'ADMIN' || user?.role === 'MANAGER') && templatesWithPerf.length > 0 && (
                    <section className="template-perf-section" aria-labelledby="template-perf-title">
                        <h2 id="template-perf-title" className="your-focus-title">Template performance</h2>
                        {(() => {
                            const withScore = templatesWithPerf
                                .filter((t: any) => (t.performance_metrics_json?.weighted_score != null) || (t.performance_metrics_json?.avg_sentiment != null))
                                .map((t: any) => ({
                                    ...t,
                                    _score: t.performance_metrics_json?.weighted_score ?? t.performance_metrics_json?.avg_sentiment ?? 0,
                                }));
                            const sorted = [...withScore].sort((a: any, b: any) => (b._score ?? 0) - (a._score ?? 0));
                            const dedupeByName = (list: any[]) => {
                                const seen = new Set<string>();
                                return list.filter((t: any) => {
                                    const name = (t.name || '').trim() || t.id;
                                    if (seen.has(name)) return false;
                                    seen.add(name);
                                    return true;
                                });
                            };
                            const sortedUnique = dedupeByName(sorted);
                            const top = sortedUnique.slice(0, 5);
                            const topIds = new Set(top.map((t: any) => t.id));
                            const needsImprovement = dedupeByName(
                                sortedUnique.filter((t: any) => !topIds.has(t.id) && t.is_deprecated !== true)
                                    .filter((t: any) => {
                                        const m = t.performance_metrics_json || {};
                                        const score = m.weighted_score ?? m.avg_sentiment ?? 0;
                                        const usage = m.usage_count ?? 0;
                                        const sentiment = m.avg_sentiment ?? 5;
                                        return score < 3.5 || (usage >= 2 && sentiment < 4);
                                    })
                            ).slice(0, 6);
                            const thresholdNote = 'Threshold: Top = highest weighted score; Needs improvement = score < 3.5 or (usage ≥ 2 and sentiment < 4).';
                            return (
                                <div>
                                    <p className="template-perf-muted" style={{ marginBottom: '12px', fontSize: '12px' }}>{thresholdNote} Use Configuration → Template Registry → Performance / Evolution for per-template details and AI-driven improvements.</p>
                                    <div className="template-perf-grid">
                                        <div className="template-perf-card">
                                            <h3 className="template-perf-card-title">Top performing</h3>
                                            {top.length === 0 ? (
                                                <p className="template-perf-muted">Run &quot;Template metrics&quot; in Configuration to see data.</p>
                                            ) : (
                                                <ul className="template-perf-list">
                                                    {top.map((t: any) => (
                                                        <li key={t.id}>
                                                            <a href={`/configuration?tab=templates&template=${t.id}`} className="template-perf-link">{t.name}</a>
                                                            <span className="template-perf-badge">{(t._score ?? 0).toFixed(1)}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}
                                        </div>
                                        <div className="template-perf-card">
                                            <h3 className="template-perf-card-title">Needs improvement</h3>
                                            {needsImprovement.length === 0 ? (
                                                <p className="template-perf-muted">None flagged.</p>
                                            ) : (
                                                <ul className="template-perf-list">
                                                    {needsImprovement.map((t: any) => (
                                                        <li key={t.id}>
                                                            <a href={`/configuration?tab=templates&template=${t.id}`} className="template-perf-link template-perf-link--warn">{t.name}</a>
                                                            <span className="template-perf-badge template-perf-badge--warn">{(t.performance_metrics_json?.avg_sentiment ?? t._score ?? 0).toFixed(1)}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })()}
                    </section>
                )}
            </main>

            <style jsx>{`
                .dashboard-page {
                    max-width: 1600px;
                    margin: 0 auto;
                    padding: var(--space-xl) var(--space-lg);
                }
                .your-focus-section {
                    margin-top: var(--space-2xl);
                    margin-bottom: var(--space-2xl);
                }
                .your-focus-title {
                    margin: 0 0 var(--space-lg) 0;
                    font-size: 1.125rem;
                    font-weight: 600;
                    color: var(--text-primary);
                }
                .your-focus-table-wrap {
                    overflow-x: auto;
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    background: var(--bg-card);
                }
                .your-focus-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 14px;
                }
                .your-focus-table th {
                    text-align: left;
                    padding: var(--space-md) var(--space-lg);
                    font-weight: 600;
                    color: var(--text-secondary);
                    background: var(--bg-secondary);
                    border-bottom: 2px solid var(--border-medium);
                }
                .your-focus-table td {
                    padding: var(--space-md) var(--space-lg);
                    border-bottom: 1px solid var(--border-light);
                    color: var(--text-primary);
                }
                .your-focus-table tbody tr:last-child td {
                    border-bottom: none;
                }
                .focus-row--clickable {
                    cursor: pointer;
                }
                .focus-row--clickable:hover {
                    background: var(--bg-card-hover);
                }
                .focus-cell--metric {
                    font-weight: 600;
                    color: var(--text-primary);
                }
                .focus-cell--value {
                    font-weight: 700;
                    font-size: 1.125rem;
                }
                .focus-cell--details {
                    color: var(--text-secondary);
                }
                .focus-link {
                    color: var(--accent-primary);
                    font-weight: 500;
                }
                .focus-link--muted {
                    color: var(--text-hint);
                }
                .dashboard-stages-grid {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 1rem;
                }
                @media (max-width: 1024px) {
                    .dashboard-stages-grid { grid-template-columns: repeat(3, 1fr); }
                }
                @media (max-width: 768px) {
                    .dashboard-stages-grid { grid-template-columns: repeat(2, 1fr); }
                }
                .template-perf-section {
                    margin-top: var(--space-2xl);
                    margin-bottom: var(--space-2xl);
                }
                .template-perf-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: var(--space-lg);
                }
                .template-perf-card {
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    background: var(--bg-card);
                    padding: var(--space-lg);
                }
                .template-perf-card-title {
                    margin: 0 0 var(--space-md) 0;
                    font-size: 1rem;
                    font-weight: 600;
                    color: var(--text-primary);
                }
                .template-perf-list {
                    list-style: none;
                    margin: 0;
                    padding: 0;
                }
                .template-perf-list li {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: var(--space-sm) 0;
                    border-bottom: 1px solid var(--border-light);
                }
                .template-perf-list li:last-child {
                    border-bottom: none;
                }
                .template-perf-link {
                    color: var(--accent-primary);
                    font-weight: 500;
                    text-decoration: none;
                }
                .template-perf-link:hover {
                    text-decoration: underline;
                }
                .template-perf-link--warn {
                    color: var(--warning, #b45309);
                }
                .template-perf-badge {
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--text-secondary);
                    background: var(--bg-secondary);
                    padding: 2px 8px;
                    border-radius: var(--radius-sm);
                }
                .template-perf-badge--warn {
                    background: var(--warning-bg, #fef3c7);
                    color: var(--warning, #b45309);
                }
                .template-perf-muted {
                    margin: 0;
                    font-size: 14px;
                    color: var(--text-muted);
                }
            `}</style>
        </div>
    );
}

