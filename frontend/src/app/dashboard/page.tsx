'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';
import { projectsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import PageHeader from '@/components/PageHeader';

export default function DashboardPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [projects, setProjects] = useState<any[]>([]);
    const [user, setUser] = useState<any>(null);
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
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const buildWidget = (widget: Widget) => (
        <button
            key={widget.title}
            className={`widget-card ${widget.placeholder ? 'placeholder' : ''}`}
            onClick={() => {
                if (widget.href && !widget.placeholder) {
                    router.push(widget.href);
                }
            }}
            disabled={!widget.href || widget.placeholder}
        >
            <div className="widget-title">{widget.title}</div>
            <div className="widget-value">{widget.value}</div>
            <div className="widget-subtitle">{widget.subtitle}</div>
            {widget.href && !widget.placeholder && (
                <div className="widget-link">View</div>
            )}
        </button>
    );

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
            return [
                {
                    title: 'SLA Breaches',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'HITL Approvals Pending',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Sentiment Dips',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
            ];
        }

        if (role === 'ADMIN') {
            return [
                {
                    title: 'Revenue Summary',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Delivery Health',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
                },
                {
                    title: 'Sentiment Trend',
                    value: '—',
                    subtitle: 'Data source not connected yet',
                    placeholder: true,
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
            <main className="dashboard">
                <header className="page-header">
                    <div className="header-text">
                        <PageHeader
                            title="Dashboard"
                            purpose={`Welcome back, ${user?.name || 'team'}! Here's your delivery pipeline overview.`}
                            variant="page"
                        />
                    </div>
                </header>

                <section className="widgets-section">
                    <h2>Your Focus</h2>
                    <div className="widgets-grid">
                        {getWidgetsForRole().map(buildWidget)}
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
                
                /* Sections */
                section {
                    margin-bottom: var(--space-2xl);
                }
                section h2 {
                    margin-bottom: var(--space-lg);
                    font-size: 18px;
                    color: var(--text-secondary);
                }
                
                .widgets-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: var(--space-md);
                }
                .widget-card {
                    text-align: left;
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    cursor: pointer;
                    transition: all var(--transition-normal);
                }
                .widget-card.placeholder,
                .widget-card:disabled {
                    cursor: default;
                    opacity: 0.8;
                }
                .widget-card:not(.placeholder):hover {
                    background: var(--bg-card-hover);
                    border-color: var(--accent-primary);
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                }
                .widget-card:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                .widget-title {
                    font-size: 12px;
                    color: var(--text-muted);
                    margin-bottom: var(--space-xs);
                }
                .widget-value {
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--text-primary);
                    line-height: 1;
                }
                .widget-subtitle {
                    margin-top: var(--space-xs);
                    font-size: 12px;
                    color: var(--text-secondary);
                }
                .widget-link {
                    margin-top: var(--space-sm);
                    font-size: 12px;
                    color: var(--accent-primary);
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

