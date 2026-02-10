'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const SEGMENT_LABELS: Record<string, string> = {
    dashboard: 'Dashboard',
    projects: 'Projects',
    create: 'Create',
    users: 'Manage Users',
    configuration: 'Configuration',
    'client-management': 'Clients',
    capacity: 'Capacity',
    forecast: 'Forecast',
    'leave-management': 'Leave',
    team: 'Team',
    reports: 'Reports',
    sentiments: 'Sentiments',
    sentiment: 'Sentiment',
    admin: 'Admin',
    operations: 'Operations',
    quality: 'Quality',
    'audit-logs': 'Audit Logs',
    'executive-dashboard': 'Executive Dashboard',
};

function getLabel(segment: string, isId = false): string {
    if (isId) return 'Detail';
    return SEGMENT_LABELS[segment] || segment.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function Breadcrumbs() {
    const pathname = usePathname();
    if (!pathname || pathname === '/' || pathname === '/login') return null;

    const segments = pathname.split('/').filter(Boolean);
    const items: { href: string; label: string }[] = [{ href: '/', label: 'Home' }];
    let href = '';
    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        href += `/${seg}`;
        const isId = /^[0-9a-f-]{36}$/i.test(seg) || seg.length > 20;
        items.push({ href, label: getLabel(seg, isId) });
    }

    return (
        <nav aria-label="Breadcrumb" className="breadcrumbs">
            <ol className="breadcrumbs-list">
                {items.map((item, i) => (
                    <li key={item.href} className="breadcrumb-item">
                        {i === items.length - 1 ? (
                            <span aria-current="page" className="breadcrumb-current">
                                {item.label}
                            </span>
                        ) : (
                            <>
                                <Link href={item.href} className="breadcrumb-link">
                                    {item.label}
                                </Link>
                                <span className="breadcrumb-sep" aria-hidden>/</span>
                            </>
                        )}
                    </li>
                ))}
            </ol>
            <style jsx>{`
                .breadcrumbs {
                    margin-bottom: var(--space-md);
                }
                .breadcrumbs-list {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: center;
                    gap: 4px;
                    list-style: none;
                    padding: 0;
                    margin: 0;
                    font-size: 13px;
                    color: var(--text-muted);
                }
                .breadcrumb-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                .breadcrumb-link {
                    color: var(--accent-primary);
                    text-decoration: none;
                }
                .breadcrumb-link:hover {
                    text-decoration: underline;
                }
                .breadcrumb-current {
                    color: var(--text-primary);
                    font-weight: 500;
                }
                .breadcrumb-sep {
                    color: var(--text-hint);
                }
            `}</style>
        </nav>
    );
}
