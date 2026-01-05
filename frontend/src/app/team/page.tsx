'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';
import { usersAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';

interface User {
    id: number;
    name: string;
    email: string;
    role: string;
    is_active: boolean;
    region?: string;
    department?: string;
}

export default function TeamPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [users, setUsers] = useState<User[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedRole, setSelectedRole] = useState<string>('all');
    const [selectedRegion, setSelectedRegion] = useState<string>('all');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        loadUsers();
    }, []);

    const loadUsers = async () => {
        try {
            const response = await usersAPI.list();
            const enrichedUsers = response.data.map((user: any) => ({
                ...user,
                department: getDepartment(user.role),
            }));
            setUsers(enrichedUsers);
        } catch (error) {
            console.error('Failed to load users:', error);
        } finally {
            setLoading(false);
        }
    };

    const REGIONS = [
        { value: 'INDIA', label: 'India', code: 'IN', flagUrl: 'https://flagcdn.com/w40/in.png' },
        { value: 'US', label: 'US', code: 'US', flagUrl: 'https://flagcdn.com/w40/us.png' },
        { value: 'PH', label: 'Philippines', code: 'PH', flagUrl: 'https://flagcdn.com/w40/ph.png' },
    ];

    const FlagIcon = ({ region, size = 20 }: { region: string; size?: number }) => {
        const regionData = REGIONS.find(r => r.value === region);
        if (!regionData) return <span>{region || 'N/A'}</span>;
        return (
            <img 
                src={regionData.flagUrl} 
                alt={`${regionData.label} flag`}
                width={size}
                height={Math.round(size * 0.75)}
                style={{ borderRadius: 2, objectFit: 'cover' }}
            />
        );
    };

    const getRegionCode = (region: string) => {
        return REGIONS.find(r => r.value === region)?.code || region || 'N/A';
    };

    const getDepartment = (role: string) => {
        const departments: Record<string, string> = {
            'ADMIN': 'Administration',
            'MANAGER': 'Management',
            'CONSULTANT': 'Consulting',
            'PC': 'Project Coordination',
            'BUILDER': 'Development',
            'TESTER': 'Quality Assurance',
        };
        return departments[role] || 'General';
    };

    const getRoleColor = (role: string) => {
        const colors: Record<string, string> = {
            'ADMIN': 'var(--role-admin)',
            'MANAGER': 'var(--role-manager)',
            'CONSULTANT': 'var(--role-consultant)',
            'PC': 'var(--role-pc)',
            'BUILDER': 'var(--role-builder)',
            'TESTER': 'var(--role-tester)',
        };
        return colors[role] || 'var(--text-muted)';
    };

    const getInitials = (name: string) => {
        return name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
    };

    const filteredUsers = users.filter((user) => {
        const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            user.email.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesRole = selectedRole === 'all' || user.role === selectedRole;
        const matchesRegion = selectedRegion === 'all' || user.region === selectedRegion;
        return matchesSearch && matchesRole && matchesRegion && user.is_active;
    });

    const roles = ['all', 'ADMIN', 'MANAGER', 'CONSULTANT', 'PC', 'BUILDER', 'TESTER'];
    const regions = [
        { value: 'all', label: 'All Regions' },
        { value: 'INDIA', label: 'IN - India' },
        { value: 'US', label: 'US - United States' },
        { value: 'PH', label: 'PH - Philippines' },
    ];

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading team directory...</p>
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
            <main className="team-page">
                <header className="page-header">
                    <div className="header-text">
                        <h1>Team Directory</h1>
                        <p>All team members across India, US and Philippines regions</p>
                    </div>
                    <div className="header-stats">
                        {REGIONS.map(region => (
                            <div key={region.value} className="region-stat">
                                <FlagIcon region={region.value} size={20} />
                                <span className="count">{users.filter(u => u.region === region.value && u.is_active).length}</span>
                            </div>
                        ))}
                    </div>
                </header>

                <div className="filters-bar">
                    <div className="search-box">
                        <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="11" cy="11" r="8" />
                            <path d="M21 21l-4.35-4.35" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search by name or email..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    <div className="filter-group">
                        <label>Role</label>
                        <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)}>
                            {roles.map((role) => (
                                <option key={role} value={role}>
                                    {role === 'all' ? 'All Roles' : role}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="filter-group">
                        <label>Region</label>
                        <select value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)}>
                            {regions.map((region) => (
                                <option key={region.value} value={region.value}>
                                    {region.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="view-toggle">
                        <button
                            className={viewMode === 'grid' ? 'active' : ''}
                            onClick={() => setViewMode('grid')}
                            title="Grid view"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <rect x="3" y="3" width="7" height="7" rx="1" />
                                <rect x="14" y="3" width="7" height="7" rx="1" />
                                <rect x="3" y="14" width="7" height="7" rx="1" />
                                <rect x="14" y="14" width="7" height="7" rx="1" />
                            </svg>
                        </button>
                        <button
                            className={viewMode === 'list' ? 'active' : ''}
                            onClick={() => setViewMode('list')}
                            title="List view"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="3" y1="6" x2="21" y2="6" />
                                <line x1="3" y1="12" x2="21" y2="12" />
                                <line x1="3" y1="18" x2="21" y2="18" />
                            </svg>
                        </button>
                    </div>
                </div>

                <div className="results-count">
                    Showing {filteredUsers.length} of {users.filter(u => u.is_active).length} members
                </div>

                {viewMode === 'grid' ? (
                    <div className="users-grid">
                        {filteredUsers.map((user, index) => (
                            <div
                                key={user.id}
                                className="user-card"
                                style={{ animationDelay: `${index * 30}ms` }}
                            >
                                <div className="card-accent" style={{ background: getRoleColor(user.role) }} />
                                <div className="card-content">
                                    <div className="user-avatar" style={{ background: getRoleColor(user.role) }}>
                                        {getInitials(user.name)}
                                    </div>
                                    <span className="user-region">
                                        <FlagIcon region={user.region || ''} size={16} />
                                        {getRegionCode(user.region || '')}
                                    </span>
                                    <h3>{user.name}</h3>
                                    <p className="user-email">{user.email}</p>
                                    <span className="user-role" style={{ color: getRoleColor(user.role) }}>
                                        {user.role}
                                    </span>
                                    <p className="user-dept">{user.department}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="users-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Department</th>
                                    <th>Region</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredUsers.map((user, index) => (
                                    <tr key={user.id} style={{ animationDelay: `${index * 20}ms` }}>
                                        <td className="cell-name">
                                            <div className="name-avatar" style={{ background: getRoleColor(user.role) }}>
                                                {getInitials(user.name)}
                                            </div>
                                            <span>{user.name}</span>
                                        </td>
                                        <td className="cell-email">{user.email}</td>
                                        <td>
                                            <span className="role-badge" style={{ color: getRoleColor(user.role) }}>
                                                {user.role}
                                            </span>
                                        </td>
                                        <td>{user.department}</td>
                                        <td>
                                            <span className="region-badge">
                                                <FlagIcon region={user.region || ''} size={16} />
                                                {getRegionCode(user.region || '')}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {filteredUsers.length === 0 && (
                    <div className="empty-state">
                        <div className="empty-icon">🔍</div>
                        <h3>No team members found</h3>
                        <p>Try adjusting your search or filters</p>
                    </div>
                )}
            </main>

            <style jsx>{`
                .team-page {
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
                
                .header-stats {
                    display: flex;
                    gap: var(--space-md);
                }
                
                .region-stat {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                }
                
                .region-code {
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--text-secondary);
                }
                
                .count {
                    font-size: 18px;
                    font-weight: 700;
                    color: var(--text-primary);
                }
                
                .filters-bar {
                    display: flex;
                    gap: var(--space-md);
                    align-items: flex-end;
                    margin-bottom: var(--space-md);
                    padding: var(--space-lg);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    flex-wrap: wrap;
                }
                
                .search-box {
                    flex: 1;
                    min-width: 250px;
                    position: relative;
                }
                
                .search-icon {
                    position: absolute;
                    left: 14px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: var(--text-hint);
                }
                
                .search-box input {
                    width: 100%;
                    padding: 12px 12px 12px 44px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 14px;
                }
                
                .search-box input:focus {
                    outline: none;
                    border-color: var(--accent-primary);
                }
                
                .filter-group {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-xs);
                }
                
                .filter-group label {
                    font-size: 11px;
                    color: var(--text-hint);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .filter-group select {
                    padding: 12px var(--space-md);
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 13px;
                    min-width: 140px;
                }
                
                .filter-group select option {
                    background: var(--bg-primary);
                    color: var(--text-primary);
                }
                
                .search-box input:focus,
                .filter-group select:focus {
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }
                
                .view-toggle {
                    display: flex;
                    background: var(--bg-input);
                    border-radius: var(--radius-md);
                    overflow: hidden;
                }
                
                .view-toggle button {
                    padding: 12px 14px;
                    color: var(--text-hint);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .view-toggle button:hover {
                    color: var(--text-secondary);
                }
                
                .view-toggle button.active {
                    background: var(--color-info-bg);
                    color: var(--accent-primary);
                }
                
                .view-toggle button:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                
                .results-count {
                    font-size: 13px;
                    color: var(--text-hint);
                    margin-bottom: var(--space-lg);
                }
                
                .users-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
                    gap: var(--space-md);
                }
                
                .user-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    overflow: hidden;
                    animation: fadeIn 0.3s ease forwards;
                    opacity: 0;
                    transition: all var(--transition-fast);
                }
                
                .user-card:hover {
                    border-color: var(--border-medium);
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                }
                
                .card-accent {
                    height: 4px;
                }
                
                .card-content {
                    padding: var(--space-lg);
                    text-align: center;
                    position: relative;
                }
                
                .user-avatar {
                    width: 64px;
                    height: 64px;
                    margin: 0 auto var(--space-md);
                    border-radius: var(--radius-full);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 700;
                    font-size: 20px;
                }
                
                .user-region {
                    position: absolute;
                    top: var(--space-md);
                    right: var(--space-md);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 4px 8px;
                    background: var(--bg-tertiary);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-sm);
                    color: var(--text-secondary);
                }
                
                .user-card h3 {
                    font-size: 15px;
                    margin-bottom: var(--space-xs);
                }
                
                .user-email {
                    font-size: 12px;
                    color: var(--text-hint);
                    margin-bottom: var(--space-sm);
                }
                
                .user-role {
                    display: inline-block;
                    font-size: 11px;
                    font-weight: 600;
                    margin-bottom: var(--space-sm);
                }
                
                .user-dept {
                    font-size: 12px;
                    color: var(--text-muted);
                }
                
                .users-table {
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
                
                .cell-name {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    font-weight: 600;
                    color: var(--text-primary);
                }
                
                .name-avatar {
                    width: 32px;
                    height: 32px;
                    border-radius: var(--radius-full);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 11px;
                    font-weight: 700;
                }
                
                .cell-email {
                    color: var(--text-muted);
                }
                
                .role-badge {
                    font-size: 12px;
                    font-weight: 600;
                }
                
                .region-badge {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                }
                
                .empty-state {
                    text-align: center;
                    padding: var(--space-2xl);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
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
            `}</style>
        </div>
    );
}
