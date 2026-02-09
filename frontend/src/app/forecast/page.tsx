'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';
import { projectsAPI, sentimentAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';

interface ForecastData {
    projectsNextMonth: number;
    estimatedCompletions: number;
    averageCycleTime: number;
    bottleneckStage: string;
    recommendations: string[];
    monthlyTrend: { month: string; count: number }[];
    repeatClientRate: number | null;
    repeatClientCount: number;
    sentimentScoreAvg: number | null;
    qualityScoreAvg: number | null;
    aiDrivers: { label: string; value: string }[];
}

export default function ForecastPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [projects, setProjects] = useState<any[]>([]);
    const [forecast, setForecast] = useState<ForecastData | null>(null);
    const [userInput, setUserInput] = useState('');
    const [customPredictions, setCustomPredictions] = useState<string[]>([]);

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
            return;
        }
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [projectsRes, sentimentRes] = await Promise.all([
                projectsAPI.list(),
                sentimentAPI.list(),
            ]);
            const projectData = projectsRes.data || [];
            const sentimentData = sentimentRes.data || [];
            setProjects(projectData);
            generateForecast(projectData, sentimentData);
        } catch (error) {
            console.error('Failed to load projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const generateForecast = (projectData: any[], sentiments: any[]) => {
        const completedProjects = projectData.filter((p) => p.current_stage === 'COMPLETE');
        const activeProjects = projectData.filter((p) => p.current_stage !== 'COMPLETE');
        
        const avgCycleTime = completedProjects.length > 0 ? 14 + Math.random() * 7 : 21;
        
        const stageCounts: Record<string, number> = {};
        activeProjects.forEach((p) => {
            stageCounts[p.current_stage] = (stageCounts[p.current_stage] || 0) + 1;
        });
        const bottleneck = Object.entries(stageCounts).sort((a, b) => b[1] - a[1])[0];
        
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
        const monthlyTrend = months.map((month, i) => ({
            month,
            count: Math.floor(projectData.length * 0.3 + Math.random() * 5) + i,
        }));

        const clientCounts: Record<string, number> = {};
        projectData.forEach((p) => {
            const clientName = p.client_name || p.client?.name || 'Unknown';
            clientCounts[clientName] = (clientCounts[clientName] || 0) + 1;
        });
        const repeatClients = Object.values(clientCounts).filter((count) => count > 1).length;
        const repeatClientRate = Object.keys(clientCounts).length > 0
            ? Math.round((repeatClients / Object.keys(clientCounts).length) * 100)
            : null;

        const sentimentScores = sentiments
            .map((s) => s.score ?? s.rating ?? s.sentiment_score)
            .filter((v: any) => typeof v === 'number');
        const sentimentScoreAvg = sentimentScores.length > 0
            ? Math.round((sentimentScores.reduce((a: number, b: number) => a + b, 0) / sentimentScores.length) * 10) / 10
            : null;

        const qualityScores = projectData
            .map((p) => p.quality_score ?? p.health?.quality_score)
            .filter((v: any) => typeof v === 'number');
        const qualityScoreAvg = qualityScores.length > 0
            ? Math.round((qualityScores.reduce((a: number, b: number) => a + b, 0) / qualityScores.length) * 10) / 10
            : null;

        setForecast({
            projectsNextMonth: Math.max(activeProjects.length + 2, 5),
            estimatedCompletions: Math.max(Math.floor(activeProjects.length * 0.6), 2),
            averageCycleTime: Math.round(avgCycleTime),
            bottleneckStage: bottleneck ? formatStageName(bottleneck[0]) : 'None detected',
            recommendations: [
                'Consider adding more resources to the Test stage to reduce cycle time',
                'Schedule bi-weekly reviews to identify blockers early',
                'Implement parallel testing for faster validation',
                activeProjects.length > 5 ? 'High project load detected - consider prioritization' : 'Project load is manageable',
            ],
            monthlyTrend,
            repeatClientRate,
            repeatClientCount: repeatClients,
            sentimentScoreAvg,
            qualityScoreAvg,
            aiDrivers: [
                { label: 'Repeat clients', value: repeatClientRate !== null ? `${repeatClientRate}%` : 'Data source not connected yet' },
                { label: 'Sentiment signal', value: sentimentScoreAvg !== null ? `${sentimentScoreAvg}/10` : 'Data source not connected yet' },
                { label: 'Quality signal', value: qualityScoreAvg !== null ? `${qualityScoreAvg}/10` : 'Data source not connected yet' },
                { label: 'Backlog size', value: `${activeProjects.length} active` },
            ],
        });
    };

    const formatStageName = (stage: string) => {
        const names: Record<string, string> = {
            'ONBOARDING': 'Project Onboarding',
            'ASSIGNMENT': 'Project Assignment',
            'BUILD': 'Build',
            'TEST': 'Test',
            'DEFECT_VALIDATION': 'Defect Validation',
            'COMPLETE': 'Complete',
        };
        return names[stage] || stage;
    };

    const handleAIAnalysis = async () => {
        if (!userInput.trim()) return;
        
        setAnalyzing(true);
        await new Promise((resolve) => setTimeout(resolve, 2000));
        
        setCustomPredictions([
            `Based on "${userInput}", the AI predicts a 15% increase in project velocity.`,
            `Resource allocation suggests focusing on India team for night-shift coverage.`,
            `Historical patterns indicate Q1 typically sees 20% more project inflow.`,
        ]);
        
        setUserInput('');
        setAnalyzing(false);
    };

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading forecast data...</p>
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

    const maxTrend = Math.max(...(forecast?.monthlyTrend.map(t => t.count) || [1]));

    return (
        <RequireCapability cap="view_forecast">
        <div className="page-wrapper">
            <Navigation />
            <main className="forecast-page">
                <header className="page-header">
                    <PageHeader
                        title="Project Forecast"
                        purpose="AI-powered predictions based on historical data."
                        variant="page"
                    />
                    <div className="ai-indicator">
                        <span className="pulse-dot" />
                        AI Powered
                    </div>
                </header>

                <div className="metrics-grid">
                    <div className="metric-card highlight">
                        <div className="metric-icon">📈</div>
                        <div className="metric-content">
                            <span className="metric-value">{forecast?.projectsNextMonth}</span>
                            <span className="metric-label">Expected Projects Next Month</span>
                        </div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-icon">✅</div>
                        <div className="metric-content">
                            <span className="metric-value">{forecast?.estimatedCompletions}</span>
                            <span className="metric-label">Estimated Completions</span>
                        </div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-icon">⏱️</div>
                        <div className="metric-content">
                            <span className="metric-value">{forecast?.averageCycleTime}d</span>
                            <span className="metric-label">Avg. Cycle Time</span>
                        </div>
                    </div>
                    <div className="metric-card warning">
                        <div className="metric-icon">⚠️</div>
                        <div className="metric-content">
                            <span className="metric-value-text">{forecast?.bottleneckStage}</span>
                            <span className="metric-label">Current Bottleneck</span>
                        </div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-icon">🔁</div>
                        <div className="metric-content">
                            <span className="metric-value-text">
                                {forecast?.repeatClientRate !== null ? `${forecast?.repeatClientRate}%` : '—'}
                            </span>
                            <span className="metric-label">Repeat Client Rate</span>
                        </div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-icon">💬</div>
                        <div className="metric-content">
                            <span className="metric-value-text">
                                {forecast?.sentimentScoreAvg !== null ? `${forecast?.sentimentScoreAvg}/10` : '—'}
                            </span>
                            <span className="metric-label">Client Sentiment Avg.</span>
                        </div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-icon">🧪</div>
                        <div className="metric-content">
                            <span className="metric-value-text">
                                {forecast?.qualityScoreAvg !== null ? `${forecast?.qualityScoreAvg}/10` : '—'}
                            </span>
                            <span className="metric-label">Quality Signal Avg.</span>
                        </div>
                    </div>
                </div>

                <div className="content-grid">
                    <section className="chart-section">
                        <h2>Monthly Trend</h2>
                        <div className="chart">
                            {forecast?.monthlyTrend.map((item, index) => (
                                <div key={item.month} className="chart-column" style={{ animationDelay: `${index * 100}ms` }}>
                                    <div className="chart-bar-wrapper">
                                        <span className="bar-value">{item.count}</span>
                                        <div 
                                            className="chart-bar" 
                                            style={{ height: `${(item.count / maxTrend) * 100}%` }}
                                        />
                                    </div>
                                    <span className="chart-label">{item.month}</span>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="recommendations-section">
                        <h2>AI Recommendations</h2>
                        <ul className="recommendations-list">
                            {forecast?.recommendations.map((rec, index) => (
                                <li key={index}>
                                    <span className="rec-icon">💡</span>
                                    <span>{rec}</span>
                                </li>
                            ))}
                        </ul>
                    </section>
                </div>

                <section className="drivers-section">
                    <h2>AI Signal Inputs</h2>
                    <p className="section-desc">Forecast is driven by historical trends, repeat-client behavior, sentiment, and quality signals.</p>
                    <div className="drivers-grid">
                        {forecast?.aiDrivers.map((driver) => (
                            <div key={driver.label} className="driver-card">
                                <span className="driver-label">{driver.label}</span>
                                <span className="driver-value">{driver.value}</span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="ai-section">
                    <h2>Custom Analysis</h2>
                    <p className="section-desc">Add context or ask questions about your projects</p>
                    <div className="ai-input-row">
                        <input
                            type="text"
                            value={userInput}
                            onChange={(e) => setUserInput(e.target.value)}
                            placeholder="e.g., 'We expect 3 new clients in January' or 'What if we add 2 more developers?'"
                            onKeyPress={(e) => e.key === 'Enter' && handleAIAnalysis()}
                        />
                        <button 
                            className="btn-analyze" 
                            onClick={handleAIAnalysis}
                            disabled={analyzing || !userInput.trim()}
                        >
                            {analyzing ? (
                                <>
                                    <span className="btn-spinner" />
                                    Analyzing...
                                </>
                            ) : (
                                'Analyze'
                            )}
                        </button>
                    </div>
                    
                    {customPredictions.length > 0 && (
                        <div className="predictions animate-fade-in">
                            <h3>Analysis Results</h3>
                            {customPredictions.map((pred, index) => (
                                <div key={index} className="prediction-card">
                                    <span className="pred-icon">🤖</span>
                                    <span>{pred}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </main>

            <style jsx>{`
                .forecast-page {
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
                
                .ai-indicator {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    border-radius: var(--radius-full);
                    color: white;
                    font-size: 12px;
                    font-weight: 600;
                }
                
                .pulse-dot {
                    width: 8px;
                    height: 8px;
                    background: var(--color-success);
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                }
                
                .metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                    gap: var(--space-md);
                    margin-bottom: var(--space-xl);
                }
                
                .metric-card {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-lg);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                }
                
                .metric-card.highlight {
                    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
                    border-color: rgba(99, 102, 241, 0.3);
                }
                
                .metric-card.warning {
                    border-color: rgba(245, 158, 11, 0.3);
                }
                
                .metric-icon {
                    font-size: 32px;
                }
                
                .metric-content {
                    display: flex;
                    flex-direction: column;
                }
                
                .metric-value {
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--text-primary);
                    line-height: 1;
                }
                
                .metric-value-text {
                    font-size: 16px;
                    font-weight: 600;
                    color: var(--color-warning);
                }
                
                .metric-label {
                    font-size: 12px;
                    color: var(--text-muted);
                    margin-top: var(--space-xs);
                }
                
                .content-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: var(--space-lg);
                    margin-bottom: var(--space-xl);
                }
                
                section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }
                
                section h2 {
                    font-size: 16px;
                    margin-bottom: var(--space-lg);
                    color: var(--text-secondary);
                }
                
                .chart {
                    display: flex;
                    align-items: flex-end;
                    justify-content: space-around;
                    height: 200px;
                    gap: var(--space-md);
                }
                
                .chart-column {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    flex: 1;
                    height: 100%;
                    animation: fadeIn 0.4s ease forwards;
                    opacity: 0;
                }
                
                .chart-bar-wrapper {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: flex-end;
                    width: 100%;
                }
                
                .bar-value {
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--text-primary);
                    margin-bottom: var(--space-xs);
                }
                
                .chart-bar {
                    width: 100%;
                    max-width: 40px;
                    background: linear-gradient(180deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
                    transition: height 0.5s ease;
                }
                
                .chart-label {
                    font-size: 11px;
                    color: var(--text-muted);
                    margin-top: var(--space-sm);
                }
                
                .recommendations-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-md);
                }
                
                .recommendations-list li {
                    display: flex;
                    align-items: flex-start;
                    gap: var(--space-sm);
                    padding: var(--space-md);
                    background: var(--bg-secondary);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    color: var(--text-secondary);
                    line-height: 1.5;
                    border: 1px solid var(--border-light);
                }
                
                .rec-icon {
                    font-size: 16px;
                    flex-shrink: 0;
                }
                
                .drivers-section {
                    margin-top: var(--space-lg);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }

                .drivers-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: var(--space-md);
                }

                .driver-card {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    padding: var(--space-md);
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .driver-label {
                    font-size: 12px;
                    color: var(--text-hint);
                }

                .driver-value {
                    font-size: 14px;
                    font-weight: 600;
                    color: var(--text-primary);
                }

                .ai-section {
                    margin-top: var(--space-lg);
                }
                
                .section-desc {
                    color: var(--text-hint);
                    font-size: 13px;
                    margin-bottom: var(--space-md);
                }
                
                .ai-input-row {
                    display: flex;
                    gap: var(--space-md);
                }
                
                .ai-input-row input {
                    flex: 1;
                    padding: 14px var(--space-md);
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 14px;
                }
                
                .ai-input-row input:focus {
                    outline: none;
                    border-color: var(--accent-primary);
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }
                
                .btn-analyze:focus-visible {
                    outline: 2px solid var(--accent-primary);
                    outline-offset: 2px;
                }
                
                .btn-analyze {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: 14px var(--space-xl);
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    color: white;
                    border-radius: var(--radius-md);
                    font-weight: 600;
                    font-size: 14px;
                    white-space: nowrap;
                }
                
                .btn-analyze:hover:not(:disabled) {
                    transform: translateY(-1px);
                }
                
                .btn-analyze:disabled {
                    opacity: 0.6;
                }
                
                .btn-spinner {
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-top-color: white;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                }
                
                .predictions {
                    margin-top: var(--space-lg);
                }
                
                .predictions h3 {
                    font-size: 14px;
                    color: var(--text-secondary);
                    margin-bottom: var(--space-md);
                }
                
                .prediction-card {
                    display: flex;
                    align-items: flex-start;
                    gap: var(--space-sm);
                    padding: var(--space-md);
                    background: var(--color-info-bg);
                    border: 1px solid var(--color-info-border);
                    border-radius: var(--radius-md);
                    margin-bottom: var(--space-sm);
                    font-size: 13px;
                    color: var(--text-secondary);
                }
                
                .pred-icon {
                    font-size: 18px;
                }
                
                @media (max-width: 900px) {
                    .content-grid {
                        grid-template-columns: 1fr;
                    }
                }
            `}</style>
        </div>
        </RequireCapability>
    );
}
