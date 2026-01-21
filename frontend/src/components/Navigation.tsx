'use client';

import { useRouter, usePathname } from 'next/navigation';
import { getCurrentUser, logout } from '@/lib/auth';
import { healthAPI } from '@/lib/api';
import { useEffect, useState } from 'react';

import { useNotification } from '@/context/NotificationContext';

export default function Navigation() {
    const { unreadCount, toggleDrawer, isDrawerOpen, notifications, markAsRead, clearAll } = useNotification();
    const router = useRouter();
    const pathname = usePathname();
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        const currentUser = getCurrentUser();
        setUser(currentUser);

        if (currentUser) {
            // Single warm-up ping; avoid continuous background requests
            healthAPI.ping().catch(() => { });
        }
        return;
    }, []);

    const isActive = (path: string) => pathname === path;
    const isAdmin = user?.role === 'ADMIN';
    const isManager = user?.role === 'ADMIN' || user?.role === 'MANAGER';
    const isConsultantPlus = ['ADMIN', 'MANAGER', 'CONSULTANT', 'PC'].includes(user?.role);

    // Build nav items based on role
    const navItems = [
        // Admin: Executive Dashboard instead of regular Dashboard
        ...(isAdmin ? [
            { path: '/executive-dashboard', label: 'Dashboard', icon: '📊' },
        ] : [
            { path: '/dashboard', label: 'Dashboard', icon: '📊' },
        ]),
        // All users: Projects (with role-based detail views)
        { path: '/projects', label: 'Projects', icon: '📁' },
        // Consultant+: Client Management
        ...(isConsultantPlus ? [
            { path: '/client-management', label: 'Clients', icon: '📧' },
        ] : []),
        // Non-admin: Forecast and Capacity
        ...(!isAdmin ? [
            { path: '/forecast', label: 'Forecast', icon: '🔮', badge: 'AI' },
            { path: '/capacity', label: 'Capacity', icon: '👥', badge: 'AI' },
        ] : []),
        // All users: Leave Management
        { path: '/leave-management', label: 'Leave', icon: '📅' },
        // Managers+: User Management & Configuration
        ...(isManager ? [
            { path: '/users', label: 'Manage Users', icon: '⚙️' },
            { path: '/configuration', label: 'Config', icon: '🛠️' },
        ] : []),
        // All users: Team directory
        { path: '/team', label: 'Team', icon: '📋' },
    ];

    if (!user) return null;

    return (
        <nav className="navigation" role="navigation" aria-label="Main navigation">
            <div className="nav-container">
                <div
                    className="nav-brand"
                    onClick={() => router.push('/dashboard')}
                    onKeyDown={(e) => e.key === 'Enter' && router.push('/dashboard')}
                    tabIndex={0}
                    role="button"
                    aria-label="Go to dashboard"
                >
                    <div className="brand-logo" aria-hidden="true">
                        <span>🚀</span>
                    </div>
                    <div className="brand-text">
                        <span className="brand-name">Delivery</span>
                        <span className="brand-tagline">Pipeline</span>
                    </div>
                </div>

                <div className="nav-links" role="menubar">
                    {navItems.map((item) => (
                        <button
                            key={item.path}
                            onClick={() => router.push(item.path)}
                            className={`nav-link ${isActive(item.path) ? 'active' : ''}`}
                            role="menuitem"
                            aria-current={isActive(item.path) ? 'page' : undefined}
                        >
                            <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                            <span className="nav-label">{item.label}</span>
                            {item.badge && <span className="nav-badge" aria-label={`${item.badge} powered`}>{item.badge}</span>}
                        </button>
                    ))}
                </div>



                <div className="nav-user">
                    <div className="user-avatar" aria-hidden="true">
                        {user.name?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <div className="user-details">
                        <span className="user-name">{user.name}</span>
                        <span className="user-role">{user.role}</span>
                    </div>

                    <div className="nav-actions" style={{ display: 'flex', alignItems: 'center', position: 'relative' }}>
                        <button
                            onClick={toggleDrawer}
                            className="btn-notification"
                            title="Notifications"
                            aria-label="Notifications"
                            style={{
                                background: 'transparent',
                                border: 'none',
                                position: 'relative',
                                cursor: 'pointer',
                                padding: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '50%',
                                transition: 'background 0.2s',
                            }}
                        >
                            <span style={{ fontSize: '20px', filter: unreadCount === 0 ? 'grayscale(100%) opacity(0.7)' : 'none' }}>🔔</span>
                            {unreadCount > 0 && (
                                <span className="notification-badge" style={{
                                    position: 'absolute',
                                    top: '-2px',
                                    right: '-2px',
                                    background: '#ef4444',
                                    color: 'white',
                                    fontSize: '10px',
                                    fontWeight: 'bold',
                                    minWidth: '18px',
                                    height: '18px',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    border: '2px solid var(--nav-bg)',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                }}>
                                    {unreadCount > 9 ? '9+' : unreadCount}
                                </span>
                            )}
                        </button>

                        {isDrawerOpen && (
                            <div className="notification-drawer">
                                <div className="drawer-header">
                                    <h3>Notifications</h3>
                                    {notifications.length > 0 && (
                                        <button onClick={clearAll} className="btn-clear">Clear All</button>
                                    )}
                                </div>
                                <div className="drawer-content">
                                    {notifications.length === 0 ? (
                                        <p className="empty-state">No notifications</p>
                                    ) : (
                                        notifications.map(n => (
                                            <div
                                                key={n.id}
                                                className={`notification-item ${n.read ? 'read' : 'unread'} ${n.type}`}
                                                onClick={() => markAsRead(n.id)}
                                            >
                                                <div className="item-icon">{n.type === 'urgent' ? '⚠️' : 'ℹ️'}</div>
                                                <div className="item-body">
                                                    <p className="item-message">{n.message}</p>
                                                    <span className="item-time">{new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: 'numeric' }).format(new Date(n.timestamp))}</span>
                                                </div>
                                                {!n.read && <span className="item-dot" />}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                    <button
                        onClick={logout}
                        className="btn-logout"
                        title="Logout"
                        aria-label="Logout from application"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                        </svg>
                    </button>
                </div>
            </div>

            <style jsx>{`
                .navigation {
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    background: var(--nav-bg);
                    border-bottom: 1px solid var(--border-light);
                    box-shadow: var(--shadow-sm);
                }
                .nav-container {
                    max-width: 1600px;
                    margin: 0 auto;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 var(--space-lg);
                    height: var(--nav-height);
                }
                .nav-brand {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    cursor: pointer;
                    transition: opacity var(--transition-fast);
                    border-radius: var(--radius-md);
                    padding: var(--space-sm);
                    margin-left: calc(-1 * var(--space-sm));
                }
                .nav-brand:hover {
                    opacity: 0.8;
                }
                .nav-brand:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                .brand-logo {
                    width: 40px;
                    height: 40px;
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    border-radius: var(--radius-md);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    box-shadow: var(--shadow-sm);
                }
                .brand-text {
                    display: flex;
                    flex-direction: column;
                }
                .brand-name {
                    font-size: 16px;
                    font-weight: 700;
                    color: var(--text-primary);
                    line-height: 1.2;
                }
                .brand-tagline {
                    font-size: 11px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .nav-links {
                    display: flex;
                    gap: var(--space-xs);
                }
                .nav-link {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: transparent;
                    border: none;
                    border-radius: var(--radius-md);
                    color: var(--text-secondary);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                    font-size: 13px;
                    font-weight: 500;
                }
                .nav-link:hover {
                    background: var(--bg-tertiary);
                    color: var(--text-primary);
                }
                .nav-link:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                .nav-link.active {
                    background: var(--color-info-bg);
                    color: var(--accent-primary);
                    font-weight: 600;
                }
                .nav-icon {
                    font-size: 16px;
                }
                .nav-label {
                    white-space: nowrap;
                }
                .btn-notification span {
                    filter: none !important;
                }
                .notification-drawer {
                    position: absolute;
                    top: 100%;
                    right: 0;
                    width: 320px;
                    max-height: 400px;
                    background: white;
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-lg);
                    z-index: 1000;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    margin-top: 8px;
                    animation: slideDown 0.2s ease-out;
                }
                .drawer-header {
                    padding: 12px 16px;
                    border-bottom: 1px solid var(--border-light);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: var(--bg-tertiary);
                }
                .drawer-header h3 {
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                }
                .btn-clear {
                    font-size: 12px;
                    color: var(--text-muted);
                    background: none;
                    border: none;
                    cursor: pointer;
                }
                .btn-clear:hover {
                    color: var(--color-error);
                }
                .drawer-content {
                    overflow-y: auto;
                    max-height: 350px;
                }
                .empty-state {
                    padding: 24px;
                    text-align: center;
                    color: var(--text-muted);
                    font-size: 13px;
                }
                .notification-item {
                    padding: 12px 16px;
                    border-bottom: 1px solid var(--border-light);
                    display: flex;
                    gap: 12px;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .notification-item:hover {
                    background: var(--bg-tertiary);
                }
                .notification-item.unread {
                    background: #f0f9ff;
                }
                .notification-item.urgent {
                    border-left: 3px solid #ef4444;
                }
                .item-icon {
                    font-size: 18px;
                }
                .item-body {
                    flex: 1;
                }
                .item-message {
                    margin: 0 0 4px;
                    font-size: 13px;
                    color: var(--text-primary);
                    line-height: 1.4;
                }
                .item-time {
                    font-size: 11px;
                    color: var(--text-muted);
                }
                .item-dot {
                    width: 8px;
                    height: 8px;
                    background: #3b82f6;
                    border-radius: 50%;
                    align-self: center;
                }
                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .nav-badge {
                    font-size: 9px;
                    padding: 2px 6px;
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    color: white;
                    border-radius: var(--radius-full);
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .nav-user {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                }
                .user-avatar {
                    width: 36px;
                    height: 36px;
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    border-radius: var(--radius-full);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 600;
                    font-size: 14px;
                    box-shadow: var(--shadow-sm);
                }
                .user-details {
                    display: flex;
                    flex-direction: column;
                }
                .user-name {
                    color: var(--text-primary);
                    font-weight: 600;
                    font-size: 13px;
                    line-height: 1.2;
                }
                .user-role {
                    color: var(--text-muted);
                    font-size: 11px;
                }
                .btn-logout {
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--color-error-bg);
                    color: var(--color-error);
                    border: 1px solid var(--color-error-border);
                    border-radius: var(--radius-md);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }
                .btn-logout:hover {
                    background: var(--color-error);
                    color: white;
                    border-color: var(--color-error);
                }
                .btn-logout:focus-visible {
                    outline: 2px solid var(--color-error);
                    outline-offset: 2px;
                }
                @media (max-width: 1200px) {
                    .nav-label {
                        display: none;
                    }
                    .nav-badge {
                        display: none;
                    }
                }
                @media (max-width: 768px) {
                    .user-details {
                        display: none;
                    }
                    .brand-text {
                        display: none;
                    }
                }
            `}</style>
        </nav>
    );
}
