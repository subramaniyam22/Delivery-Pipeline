'use client';

import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';

const summaryCards = [
    { label: 'Projects Delivered', value: '—', helper: 'Historical delivery count' },
    { label: 'Avg. Cycle Time', value: '—', helper: 'From stage history' },
    { label: 'SLA Breaches', value: '—', helper: 'Last 30 days' },
    { label: 'Client Sentiment', value: '—', helper: 'Average score' },
];

const reportSections = [
    {
        title: 'Delivery Health',
        items: [
            'Stage throughput by week',
            'Blockers and escalations',
            'HITL approvals backlog',
        ],
    },
    {
        title: 'Client Insights',
        items: [
            'Repeat client rate',
            'Top client segments by volume',
            'Sentiment dips by template',
        ],
    },
    {
        title: 'Quality & Defects',
        items: [
            'Defect density by stage',
            'Rework rate',
            'QA pass ratio',
        ],
    },
];

export default function ReportsPage() {
    return (
        <RequireCapability cap="view_reports">
            <div className="page-wrapper">
                <Navigation />
                <main className="reports-page">
                    <PageHeader
                        title="Reports"
                        purpose="Operational and executive reporting across delivery, clients, and quality."
                        variant="page"
                    />

                    <div className="filters-bar">
                        <div className="filters">
                            <label>
                                Date range
                                <div className="date-row">
                                    <input type="date" />
                                    <span>to</span>
                                    <input type="date" />
                                </div>
                            </label>
                            <label>
                                Client
                                <select>
                                    <option>All</option>
                                </select>
                            </label>
                            <label>
                                Stage
                                <select>
                                    <option>All</option>
                                </select>
                            </label>
                            <label>
                                Template
                                <select>
                                    <option>All</option>
                                </select>
                            </label>
                        </div>
                        <div className="actions">
                            <button className="btn-secondary">Apply</button>
                            <button className="btn-secondary" disabled title="Coming soon">
                                Export CSV
                            </button>
                            <button className="btn-secondary" disabled title="Coming soon">
                                Export PDF
                            </button>
                        </div>
                    </div>

                    <div className="summary-grid">
                        {summaryCards.map((card) => (
                            <div key={card.label} className="summary-card">
                                <div className="summary-value">{card.value}</div>
                                <div className="summary-label">{card.label}</div>
                                <div className="summary-helper">{card.helper}</div>
                            </div>
                        ))}
                    </div>

                    <section className="report-list">
                        {reportSections.map((section) => (
                            <div key={section.title} className="report-card">
                                <h2>{section.title}</h2>
                                <ul>
                                    {section.items.map((item) => (
                                        <li key={item}>{item}</li>
                                    ))}
                                </ul>
                                <div className="placeholder">Data source not connected yet.</div>
                            </div>
                        ))}
                    </section>
                </main>

                <style jsx>{`
                    .reports-page {
                        max-width: 1600px;
                        margin: 0 auto;
                        padding: var(--space-xl) var(--space-lg);
                    }
                    .filters-bar {
                        display: flex;
                        align-items: flex-end;
                        justify-content: space-between;
                        gap: var(--space-md);
                        background: var(--bg-card);
                        border: 1px solid var(--border-light);
                        border-radius: var(--radius-lg);
                        padding: var(--space-md);
                        margin: var(--space-lg) 0;
                        flex-wrap: wrap;
                    }
                    .filters {
                        display: flex;
                        gap: var(--space-md);
                        flex-wrap: wrap;
                    }
                    .filters label {
                        font-size: 12px;
                        color: var(--text-hint);
                        display: flex;
                        flex-direction: column;
                        gap: 6px;
                    }
                    .filters select,
                    .filters input {
                        padding: 8px 10px;
                        border-radius: var(--radius-md);
                        border: 1px solid var(--border-medium);
                        background: var(--bg-input);
                        color: var(--text-primary);
                        font-size: 13px;
                    }
                    .date-row {
                        display: flex;
                        gap: 6px;
                        align-items: center;
                    }
                    .actions {
                        display: flex;
                        gap: 8px;
                    }
                    .btn-secondary {
                        padding: 8px 12px;
                        border-radius: var(--radius-md);
                        border: 1px solid var(--border-medium);
                        background: var(--bg-secondary);
                        color: var(--text-primary);
                        font-size: 12px;
                        cursor: pointer;
                    }
                    .btn-secondary:disabled {
                        opacity: 0.6;
                        cursor: not-allowed;
                    }
                    .summary-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                        gap: var(--space-md);
                        margin: var(--space-lg) 0;
                    }
                    .summary-card {
                        background: var(--bg-card);
                        border: 1px solid var(--border-light);
                        border-radius: var(--radius-lg);
                        padding: var(--space-lg);
                    }
                    .summary-value {
                        font-size: 20px;
                        font-weight: 700;
                        color: var(--text-primary);
                    }
                    .summary-label {
                        font-size: 13px;
                        color: var(--text-secondary);
                        margin-top: 6px;
                    }
                    .summary-helper {
                        font-size: 12px;
                        color: var(--text-hint);
                        margin-top: 6px;
                    }
                    .report-list {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                        gap: var(--space-lg);
                    }
                    .report-card {
                        background: var(--bg-card);
                        border: 1px solid var(--border-light);
                        border-radius: var(--radius-lg);
                        padding: var(--space-lg);
                    }
                    .report-card h2 {
                        margin: 0 0 10px 0;
                        font-size: 16px;
                        color: var(--text-primary);
                    }
                    .report-card ul {
                        list-style: none;
                        padding: 0;
                        margin: 0 0 12px 0;
                        display: grid;
                        gap: 6px;
                        color: var(--text-secondary);
                        font-size: 13px;
                    }
                    .placeholder {
                        font-size: 12px;
                        color: var(--text-hint);
                        background: var(--bg-secondary);
                        border: 1px dashed var(--border-light);
                        padding: 10px;
                        border-radius: var(--radius-md);
                    }
                `}</style>
            </div>
        </RequireCapability>
    );
}
