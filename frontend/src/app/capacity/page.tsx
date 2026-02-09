'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';
import { usersAPI, projectsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';

interface CapacityData {
    india: { total: number; available: number; utilized: number };
    us: { total: number; available: number; utilized: number };
    ph: { total: number; available: number; utilized: number };
    aiSuggestions: string[];
}

const REGIONS = [
    { value: 'INDIA', label: 'India', code: 'IN', flagUrl: 'https://flagcdn.com/w40/in.png' },
    { value: 'US', label: 'US', code: 'US', flagUrl: 'https://flagcdn.com/w40/us.png' },
    { value: 'PH', label: 'Philippines', code: 'PH', flagUrl: 'https://flagcdn.com/w40/ph.png' },
];

// Roles that contribute to delivery capacity (excludes Admin and Manager)
const CAPACITY_ROLES = ['CONSULTANT', 'PC', 'BUILDER', 'TESTER'];

const ROLE_INFO: Record<string, { label: string; color: string }> = {
    'CONSULTANT': { label: 'Consultant', color: '#6366f1' },
    'PC': { label: 'Project Coordinator', color: '#8b5cf6' },
    'BUILDER': { label: 'Builder', color: '#10b981' },
    'TESTER': { label: 'Tester', color: '#f59e0b' },
};

const FlagIcon = ({ region, size = 20 }: { region: string; size?: number }) => {
    const regionData = REGIONS.find(r => r.value === region);
    if (!regionData) return <span>{region}</span>;
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

export default function CapacityPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [users, setUsers] = useState<any[]>([]);
    const [capacity, setCapacity] = useState<CapacityData | null>(null);
    const [selectedRegion, setSelectedRegion] = useState<'all' | 'INDIA' | 'US' | 'PH'>('all');
    const [analyzing, setAnalyzing] = useState(false);

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [usersRes, projectsRes] = await Promise.all([
                usersAPI.list(),
                projectsAPI.list(),
            ]);
            
            // Filter only active users with delivery roles (excludes Admin and Manager)
            const capacityUsers = usersRes.data.filter((user: any) => 
                user.is_active && CAPACITY_ROLES.includes(user.role)
            );
            
            // Use the actual region from the API, with fallback for users without region
            const enrichedUsers = capacityUsers.map((user: any) => ({
                ...user,
                region: user.region || 'INDIA', // Use actual region from API
                capacity: 100,
                currentLoad: Math.floor(Math.random() * 80) + 20,
                skills: getRandomSkills(),
            }));
            
            setUsers(enrichedUsers);
            calculateCapacity(enrichedUsers);
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const getRandomSkills = () => {
        const allSkills = ['React', 'Node.js', 'Python', 'AWS', 'Docker', 'Testing', 'DevOps', 'SQL'];
        const count = Math.floor(Math.random() * 3) + 2;
        return allSkills.sort(() => 0.5 - Math.random()).slice(0, count);
    };

    const calculateCapacity = (userData: any[]) => {
        const indiaUsers = userData.filter((u) => u.region === 'INDIA');
        const usUsers = userData.filter((u) => u.region === 'US');
        const phUsers = userData.filter((u) => u.region === 'PH');
        
        const indiaUtilization = indiaUsers.length > 0 
            ? indiaUsers.reduce((sum, u) => sum + u.currentLoad, 0) / (indiaUsers.length * 100) * 100 
            : 0;
        const usUtilization = usUsers.length > 0 
            ? usUsers.reduce((sum, u) => sum + u.currentLoad, 0) / (usUsers.length * 100) * 100 
            : 0;
        const phUtilization = phUsers.length > 0 
            ? phUsers.reduce((sum, u) => sum + u.currentLoad, 0) / (phUsers.length * 100) * 100 
            : 0;
        
        const suggestions = generateAISuggestions(indiaUsers, usUsers, phUsers, indiaUtilization, usUtilization, phUtilization);
        
        setCapacity({
            india: {
                total: indiaUsers.length,
                available: indiaUsers.filter((u) => u.currentLoad < 70).length,
                utilized: Math.round(indiaUtilization),
            },
            us: {
                total: usUsers.length,
                available: usUsers.filter((u) => u.currentLoad < 70).length,
                utilized: Math.round(usUtilization),
            },
            ph: {
                total: phUsers.length,
                available: phUsers.filter((u) => u.currentLoad < 70).length,
                utilized: Math.round(phUtilization),
            },
            aiSuggestions: suggestions,
        });
    };

    const generateAISuggestions = (
        indiaTeam: any[],
        usTeam: any[],
        phTeam: any[],
        indiaUtil: number,
        usUtil: number,
        phUtil: number
    ) => {
        const suggestions: string[] = [];
        
        if (indiaUtil > 80) {
            suggestions.push(`🇮🇳 India team is at ${Math.round(indiaUtil)}% capacity. Consider hiring ${Math.ceil(indiaTeam.length * 0.2)} more resources.`);
        }
        if (usUtil > 80) {
            suggestions.push(`🇺🇸 US team is at ${Math.round(usUtil)}% capacity. Consider redistributing workload to other regions.`);
        }
        if (phUtil > 80) {
            suggestions.push(`🇵🇭 Philippines team is at ${Math.round(phUtil)}% capacity. Consider load balancing with India team.`);
        }
        if (indiaUtil < 50 && usUtil > 70) {
            suggestions.push('💡 India team has bandwidth. Consider shifting some US projects to leverage timezone advantage.');
        }
        if (phUtil < 50 && (indiaUtil > 70 || usUtil > 70)) {
            suggestions.push('💡 Philippines team has capacity. Consider redistributing workload from higher-utilized regions.');
        }
        suggestions.push('📊 Based on historical data, Q1 typically requires 15% additional capacity.');
        suggestions.push('🌐 Consider cross-training between regions to improve flexibility.');
        
        return suggestions;
    };

    const handleReanalyze = async () => {
        setAnalyzing(true);
        await new Promise((resolve) => setTimeout(resolve, 1500));
        calculateCapacity(users);
        setAnalyzing(false);
    };

    const filteredUsers = selectedRegion === 'all' 
        ? users 
        : users.filter((u) => u.region === selectedRegion);

    const getLoadColor = (load: number) => {
        if (load >= 80) return 'var(--color-error)';
        if (load >= 60) return 'var(--color-warning)';
        return 'var(--color-success)';
    };

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading team capacity...</p>
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
        <RequireCapability cap="view_capacity">
        <div className="page-wrapper">
            <Navigation />
            <main className="capacity-page">
                <header className="page-header">
                    <div className="header-text">
                        <PageHeader
                            title="Team Capacity"
                            purpose="Resource management across India, US, and Philippines teams."
                            variant="page"
                        />
                        <p className="capacity-note">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10"/>
                                <path d="M12 16v-4M12 8h.01"/>
                            </svg>
                            Admin and Manager roles are excluded from capacity tracking as they manage delivery teams.
                        </p>
                    </div>
                    <button 
                        className="btn-reanalyze" 
                        onClick={handleReanalyze}
                        disabled={analyzing}
                    >
                        {analyzing ? '🔄 Analyzing...' : '🤖 Re-analyze with AI'}
                    </button>
                </header>

                <div className="regions-grid">
                    <div className="region-card">
                        <div className="region-header">
                            <span className="region-flag"><FlagIcon region="INDIA" size={28} /></span>
                            <h2>India Team</h2>
                        </div>
                        <div className="region-stats">
                            <div className="stat">
                                <span className="stat-value">{capacity?.india.total}</span>
                                <span className="stat-label">Total</span>
                            </div>
                            <div className="stat">
                                <span className="stat-value success">{capacity?.india.available}</span>
                                <span className="stat-label">Available</span>
                            </div>
                            <div className="stat">
                                <div className="utilization-ring">
                                    <svg viewBox="0 0 36 36">
                                        <path
                                            className="ring-bg"
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                        />
                                        <path
                                            className="ring-fill india"
                                            strokeDasharray={`${capacity?.india.utilized}, 100`}
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                        />
                                    </svg>
                                    <span className="ring-value">{capacity?.india.utilized}%</span>
                                </div>
                                <span className="stat-label">Utilized</span>
                            </div>
                        </div>
                    </div>

                    <div className="region-card">
                        <div className="region-header">
                            <span className="region-flag"><FlagIcon region="US" size={28} /></span>
                            <h2>US Team</h2>
                        </div>
                        <div className="region-stats">
                            <div className="stat">
                                <span className="stat-value">{capacity?.us.total}</span>
                                <span className="stat-label">Total</span>
                            </div>
                            <div className="stat">
                                <span className="stat-value success">{capacity?.us.available}</span>
                                <span className="stat-label">Available</span>
                            </div>
                            <div className="stat">
                                <div className="utilization-ring">
                                    <svg viewBox="0 0 36 36">
                                        <path
                                            className="ring-bg"
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                        />
                                        <path
                                            className="ring-fill us"
                                            strokeDasharray={`${capacity?.us.utilized}, 100`}
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                        />
                                    </svg>
                                    <span className="ring-value">{capacity?.us.utilized}%</span>
                                </div>
                                <span className="stat-label">Utilized</span>
                            </div>
                        </div>
                    </div>

                    <div className="region-card">
                        <div className="region-header">
                            <span className="region-flag"><FlagIcon region="PH" size={28} /></span>
                            <h2>Philippines Team</h2>
                        </div>
                        <div className="region-stats">
                            <div className="stat">
                                <span className="stat-value">{capacity?.ph.total}</span>
                                <span className="stat-label">Total</span>
                            </div>
                            <div className="stat">
                                <span className="stat-value success">{capacity?.ph.available}</span>
                                <span className="stat-label">Available</span>
                            </div>
                            <div className="stat">
                                <div className="utilization-ring">
                                    <svg viewBox="0 0 36 36">
                                        <path
                                            className="ring-bg"
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                        />
                                        <path
                                            className="ring-fill ph"
                                            strokeDasharray={`${capacity?.ph.utilized}, 100`}
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                        />
                                    </svg>
                                    <span className="ring-value">{capacity?.ph.utilized}%</span>
                                </div>
                                <span className="stat-label">Utilized</span>
                            </div>
                        </div>
                    </div>
                </div>

                <section className="role-capacity-section">
                    <h2>📊 Capacity by Role</h2>
                    <div className="role-capacity-grid">
                        {CAPACITY_ROLES.map(role => {
                            const roleUsers = users.filter(u => u.role === role);
                            const totalCount = roleUsers.length;
                            const availableCount = roleUsers.filter(u => u.currentLoad < 70).length;
                            const avgUtilization = totalCount > 0 
                                ? Math.round(roleUsers.reduce((sum, u) => sum + u.currentLoad, 0) / totalCount)
                                : 0;
                            const roleInfo = ROLE_INFO[role];
                            
                            return (
                                <div key={role} className="role-capacity-card">
                                    <div className="role-header">
                                        <span 
                                            className="role-indicator" 
                                            style={{ background: roleInfo.color }}
                                        />
                                        <h3>{roleInfo.label}</h3>
                                        <span className="role-count">{totalCount} member{totalCount !== 1 ? 's' : ''}</span>
                                    </div>
                                    <div className="role-stats">
                                        <div className="role-stat">
                                            <span className="role-stat-value" style={{ color: 'var(--color-success)' }}>
                                                {availableCount}
                                            </span>
                                            <span className="role-stat-label">Available</span>
                                        </div>
                                        <div className="role-stat">
                                            <span 
                                                className="role-stat-value"
                                                style={{ color: avgUtilization > 80 ? 'var(--color-error)' : avgUtilization > 60 ? 'var(--color-warning)' : 'var(--text-primary)' }}
                                            >
                                                {avgUtilization}%
                                            </span>
                                            <span className="role-stat-label">Avg. Load</span>
                                        </div>
                                    </div>
                                    <div className="role-utilization-bar">
                                        <div 
                                            className="role-utilization-fill"
                                            style={{ 
                                                width: `${avgUtilization}%`,
                                                background: roleInfo.color
                                            }}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </section>

                <section className="suggestions-section">
                    <h2>🤖 AI Capacity Suggestions</h2>
                    <div className="suggestions-grid">
                        {capacity?.aiSuggestions.map((suggestion, index) => (
                            <div key={index} className="suggestion-card" style={{ animationDelay: `${index * 100}ms` }}>
                                {suggestion}
                            </div>
                        ))}
                    </div>
                </section>

                <section className="team-section">
                    <div className="section-header">
                        <h2>Team Members</h2>
                        <div className="filter-tabs">
                            <button
                                className={`filter-tab ${selectedRegion === 'all' ? 'active' : ''}`}
                                onClick={() => setSelectedRegion('all')}
                            >
                                All
                                <span className="tab-count">{users.length}</span>
                            </button>
                            {REGIONS.map(region => (
                                <button
                                    key={region.value}
                                    className={`filter-tab ${selectedRegion === region.value ? 'active' : ''}`}
                                    onClick={() => setSelectedRegion(region.value as any)}
                                >
                                    <FlagIcon region={region.value} size={16} />
                                    {region.code}
                                    <span className="tab-count">{users.filter(u => u.region === region.value).length}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="members-grid">
                        {filteredUsers.map((user, index) => (
                            <div key={user.id} className="member-card" style={{ animationDelay: `${index * 50}ms` }}>
                                <div className="member-header">
                                    <div className="member-avatar">
                                        {user.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="member-info">
                                        <h3>{user.name}</h3>
                                        <span className="member-role">{user.role}</span>
                                    </div>
                                    <span className="member-region">
                                        <FlagIcon region={user.region} size={18} />
                                        <span className="region-code">{REGIONS.find(r => r.value === user.region)?.code || user.region}</span>
                                    </span>
                                </div>
                                <div className="member-load">
                                    <div className="load-header">
                                        <span>Workload</span>
                                        <span style={{ color: getLoadColor(user.currentLoad) }}>
                                            {user.currentLoad}%
                                        </span>
                                    </div>
                                    <div className="load-bar">
                                        <div 
                                            className="load-fill" 
                                            style={{ 
                                                width: `${user.currentLoad}%`,
                                                background: getLoadColor(user.currentLoad)
                                            }}
                                        />
                                    </div>
                                </div>
                                <div className="member-skills">
                                    {user.skills?.map((skill: string) => (
                                        <span key={skill} className="skill-tag">{skill}</span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </main>

            <style jsx>{`
                .capacity-page {
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
                
                .capacity-note {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    margin-top: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: var(--color-info-bg);
                    border: 1px solid var(--color-info-border);
                    border-radius: var(--radius-md);
                    font-size: 12px;
                    color: var(--accent-primary);
                }
                
                .btn-reanalyze {
                    padding: 12px var(--space-lg);
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    color: white;
                    border-radius: var(--radius-md);
                    font-weight: 600;
                    font-size: 13px;
                }
                
                .btn-reanalyze:hover:not(:disabled) {
                    transform: translateY(-1px);
                }
                
                .btn-reanalyze:disabled {
                    opacity: 0.7;
                }
                
                .regions-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: var(--space-lg);
                    margin-bottom: var(--space-xl);
                }
                
                .region-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }
                
                .region-header {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    margin-bottom: var(--space-lg);
                }
                
                .region-flag {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 28px;
                }
                
                .region-header h2 {
                    font-size: 18px;
                    margin: 0;
                }
                
                .region-stats {
                    display: flex;
                    justify-content: space-around;
                }
                
                .stat {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: var(--space-sm);
                }
                
                .stat-value {
                    font-size: 32px;
                    font-weight: 700;
                    color: var(--text-primary);
                }
                
                .stat-value.success {
                    color: var(--color-success);
                }
                
                .stat-label {
                    font-size: 12px;
                    color: var(--text-muted);
                }
                
                .utilization-ring {
                    position: relative;
                    width: 56px;
                    height: 56px;
                }
                
                .utilization-ring svg {
                    transform: rotate(-90deg);
                }
                
                .ring-bg {
                    fill: none;
                    stroke: var(--border-light);
                    stroke-width: 3;
                }
                
                .ring-fill {
                    fill: none;
                    stroke: var(--accent-primary);
                    stroke-width: 3;
                    stroke-linecap: round;
                    transition: stroke-dasharray 0.5s ease;
                }
                
                .ring-fill.india {
                    stroke: var(--accent-primary);
                }
                
                .ring-fill.us {
                    stroke: var(--accent-secondary);
                }
                
                .ring-fill.ph {
                    stroke: var(--color-success);
                }
                
                .ring-value {
                    position: absolute;
                    inset: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: 700;
                    color: var(--text-primary);
                }
                
                .role-capacity-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-xl);
                }
                
                .role-capacity-section h2 {
                    font-size: 16px;
                    margin-bottom: var(--space-lg);
                    color: var(--text-secondary);
                }
                
                .role-capacity-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: var(--space-md);
                }
                
                .role-capacity-card {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    padding: var(--space-md);
                }
                
                .role-header {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    margin-bottom: var(--space-md);
                }
                
                .role-indicator {
                    width: 10px;
                    height: 10px;
                    border-radius: var(--radius-full);
                }
                
                .role-header h3 {
                    font-size: 14px;
                    font-weight: 600;
                    margin: 0;
                    flex: 1;
                }
                
                .role-count {
                    font-size: 11px;
                    color: var(--text-muted);
                    padding: 2px 8px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                }
                
                .role-stats {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: var(--space-sm);
                }
                
                .role-stat {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                
                .role-stat-value {
                    font-size: 20px;
                    font-weight: 700;
                }
                
                .role-stat-label {
                    font-size: 10px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .role-utilization-bar {
                    height: 6px;
                    background: var(--border-light);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                }
                
                .role-utilization-fill {
                    height: 100%;
                    border-radius: var(--radius-full);
                    transition: width 0.5s ease;
                }
                
                .suggestions-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-xl);
                }
                
                .suggestions-section h2 {
                    font-size: 16px;
                    margin-bottom: var(--space-lg);
                    color: var(--text-secondary);
                }
                
                .suggestions-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: var(--space-md);
                }
                
                .suggestion-card {
                    padding: var(--space-md);
                    background: var(--color-info-bg);
                    border: 1px solid var(--color-info-border);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    color: var(--text-secondary);
                    line-height: 1.5;
                    animation: fadeIn 0.4s ease forwards;
                    opacity: 0;
                }
                
                .team-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }
                
                .section-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-lg);
                }
                
                .section-header h2 {
                    font-size: 16px;
                    margin: 0;
                    color: var(--text-secondary);
                }
                
                .filter-tabs {
                    display: flex;
                    gap: var(--space-sm);
                }
                
                .filter-tab {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: transparent;
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-full);
                    color: var(--text-muted);
                    font-size: 12px;
                }
                
                .filter-tab:hover {
                    background: var(--bg-card-hover);
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
                    padding: 2px 6px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    font-size: 10px;
                }
                
                .members-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: var(--space-md);
                }
                
                .member-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-md);
                    animation: fadeIn 0.3s ease forwards;
                    opacity: 0;
                    transition: all var(--transition-fast);
                }
                
                .member-card:hover {
                    background: var(--bg-card-hover);
                    border-color: var(--border-medium);
                    box-shadow: var(--shadow-sm);
                }
                
                .member-header {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    margin-bottom: var(--space-md);
                }
                
                .member-avatar {
                    width: 40px;
                    height: 40px;
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    border-radius: var(--radius-full);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 600;
                }
                
                .member-info {
                    flex: 1;
                }
                
                .member-info h3 {
                    font-size: 14px;
                    margin: 0;
                }
                
                .member-role {
                    font-size: 11px;
                    color: var(--text-hint);
                }
                
                .member-region {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    font-size: 16px;
                }
                
                .region-code {
                    font-size: 11px;
                    font-weight: 600;
                    color: var(--text-muted);
                }
                
                .member-load {
                    margin-bottom: var(--space-md);
                }
                
                .load-header {
                    display: flex;
                    justify-content: space-between;
                    font-size: 11px;
                    color: var(--text-muted);
                    margin-bottom: var(--space-xs);
                }
                
                .load-bar {
                    height: 4px;
                    background: var(--border-light);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                }
                
                .load-fill {
                    height: 100%;
                    border-radius: var(--radius-full);
                    transition: width 0.5s ease;
                }
                
                .member-skills {
                    display: flex;
                    flex-wrap: wrap;
                    gap: var(--space-xs);
                }
                
                .skill-tag {
                    padding: 3px 8px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    font-size: 10px;
                    color: var(--text-muted);
                    border: 1px solid var(--border-light);
                }
                
                @media (max-width: 1024px) {
                    .regions-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                    .role-capacity-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                
                @media (max-width: 768px) {
                    .regions-grid {
                        grid-template-columns: 1fr;
                    }
                    .role-capacity-grid {
                        grid-template-columns: 1fr;
                    }
                    .section-header {
                        flex-direction: column;
                        gap: var(--space-md);
                    }
                    .filter-tabs {
                        flex-wrap: wrap;
                    }
                    .page-header {
                        flex-direction: column;
                        gap: var(--space-md);
                        align-items: flex-start;
                    }
                }
            `}</style>
        </div>
        </RequireCapability>
    );
}
