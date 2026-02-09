'use client';

import { useEffect, useMemo, useState } from 'react';
import { metricsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';
import {
    BarChart,
    Bar,
    ResponsiveContainer,
    XAxis,
    YAxis,
    Tooltip,
    Legend,
    PieChart,
    Pie,
    Cell,
} from 'recharts';

type MetricsResponse = {
    success_rate_by_stage: Record<string, number>;
    quality_metrics: {
        self_review_pass_rate: number;
        qa_pass_rate: number;
        defect_escape_count: number;
        avg_client_sentiment: number;
    };
};

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444'];

export default function QualityDashboardPage() {
    const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const response = await metricsAPI.get();
                setMetrics(response.data);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    const stageData = useMemo(() => {
        if (!metrics) return [];
        return Object.entries(metrics.success_rate_by_stage || {}).map(([stage, value]) => ({
            stage,
            successRate: value,
        }));
    }, [metrics]);

    const qualityCards = useMemo(() => {
        if (!metrics) return [];
        return [
            {
                label: 'Self Review Pass Rate',
                value: `${metrics.quality_metrics.self_review_pass_rate}%`,
            },
            {
                label: 'QA Pass Rate',
                value: `${metrics.quality_metrics.qa_pass_rate}%`,
            },
            {
                label: 'Defect Escape Count',
                value: metrics.quality_metrics.defect_escape_count,
            },
            {
                label: 'Avg Client Sentiment',
                value: metrics.quality_metrics.avg_client_sentiment,
            },
        ];
    }, [metrics]);

    const sentimentPie = useMemo(() => {
        if (!metrics) return [];
        const sentiment = metrics.quality_metrics.avg_client_sentiment || 0;
        return [
            { name: 'Avg Sentiment', value: sentiment },
            { name: 'Remaining', value: Math.max(0, 5 - sentiment) },
        ];
    }, [metrics]);

    return (
        <RequireCapability cap="view_quality">
        <div className="page-wrapper">
            <Navigation />
            <main className="page-container">
            <div className="page-header">
                <PageHeader
                    title="Quality Dashboard"
                    purpose="Track quality health, test pass rates, and sentiment."
                    variant="page"
                />
            </div>

            <div className="card-grid">
                {qualityCards.map(card => (
                    <div key={card.label} className="metric-card">
                        <span className="label">{card.label}</span>
                        <span className="value">{card.value}</span>
                    </div>
                ))}
            </div>

            <div className="chart-grid">
                <div className="chart-card">
                    <h2>Stage Success Rate</h2>
                    {loading ? (
                        <div className="empty">Loading...</div>
                    ) : (
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={stageData}>
                                <XAxis dataKey="stage" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="successRate" fill="#6366f1" name="Success Rate (%)" />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
                <div className="chart-card">
                    <h2>Client Sentiment (Avg)</h2>
                    {loading ? (
                        <div className="empty">Loading...</div>
                    ) : (
                        <ResponsiveContainer width="100%" height={280}>
                            <PieChart>
                                <Pie data={sentimentPie} dataKey="value" innerRadius={60} outerRadius={90}>
                                    {sentimentPie.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </div>

            <style jsx>{`
                .page-container {
                    padding: 24px;
                    max-width: 1600px;
                    width: 100%;
                    margin: 0 auto;
                }
                .page-header {
                    margin-bottom: 24px;
                }
                .card-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 16px;
                    margin-bottom: 24px;
                }
                .metric-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                }
                .metric-card .label {
                    font-size: 12px;
                    color: #6b7280;
                }
                .metric-card .value {
                    font-size: 22px;
                    font-weight: 700;
                }
                .chart-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                    gap: 16px;
                }
                .chart-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                }
                .chart-card h2 {
                    margin-bottom: 12px;
                    font-size: 16px;
                }
                .empty {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 240px;
                    color: #9ca3af;
                }
            `}</style>
            </main>
        </div>
        </RequireCapability>
    );
}
