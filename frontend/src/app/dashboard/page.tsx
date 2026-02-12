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
            return [
                {
                    title: 'My Projects',
                    value: String(projects.length),
                    subtitle: `Active ${statusCounts.active} • Draft ${statusCounts.draft} • Paused ${statusCounts.paused} • Complete ${statusCounts.complete}`,
                    href: '/projects?mine=true',
                },
                {
                    title: 'Revenue Generated',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
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
                    href: '/executive-dashboard',
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
            const total = executiveDashboard?.total_projects ?? 0;
            const onTrack = executiveDashboard?.on_track_count ?? 0;
            const warning = executiveDashboard?.warning_count ?? 0;
            const critical = executiveDashboard?.critical_count ?? 0;
            const delayed = executiveDashboard?.delayed_count ?? 0;
            const healthSub = executiveDashboard
                ? `On track: ${onTrack} • Warning: ${warning} • Critical: ${critical} • Delayed: ${delayed}`
                : 'Data source not connected yet';
            const sentiment = metrics?.quality_metrics?.avg_client_sentiment != null
                ? String(metrics.quality_metrics.avg_client_sentiment)
                : '—';
            return [
                {
                    title: 'Revenue Summary',
                    value: String(total),
                    subtitle: executiveDashboard ? 'Total active projects' : 'Data source not connected yet',
                    href: '/executive-dashboard',
                    placeholder: !executiveDashboard,
                },
                {
                    title: 'Delivery Health',
                    value: executiveDashboard ? `${onTrack}/${total} on track` : '—',
                    subtitle: healthSub,
                    href: '/executive-dashboard',
                    placeholder: !executiveDashboard,
                },
                {
                    title: 'Sentiment Trend',
                    value: sentiment,
                    subtitle: metrics ? 'Avg client sentiment' : 'Data source not connected yet',
                    placeholder: metrics == null,
                },
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
                            const top = [...withScore].sort((a: any, b: any) => (b._score ?? 0) - (a._score ?? 0)).slice(0, 5);
                            const under = withScore.filter((t: any) => {
                                const m = t.performance_metrics_json || {};
                                const usage = m.usage_count ?? 0;
                                const sentiment = m.avg_sentiment ?? 5;
                                const score = m.weighted_score ?? sentiment;
                                return t.is_deprecated === false && (score < 2.5 || (usage >= 3 && sentiment < 3.5));
                            });
                            return (
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
                                        {under.length === 0 ? (
                                            <p className="template-perf-muted">None flagged.</p>
                                        ) : (
                                            <ul className="template-perf-list">
                                                {under.map((t: any) => (
                                                    <li key={t.id}>
                                                        <a href={`/configuration?tab=templates&template=${t.id}`} className="template-perf-link template-perf-link--warn">{t.name}</a>
                                                        <span className="template-perf-badge template-perf-badge--warn">{(t.performance_metrics_json?.avg_sentiment ?? t._score ?? 0).toFixed(1)}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
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

