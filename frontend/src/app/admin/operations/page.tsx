'use client';

import { useEffect, useMemo, useState } from 'react';
import { jobsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';

type JobRun = {
    id: string;
    project_id: string;
    stage: string;
    status: string;
    attempts: number;
    max_attempts: number;
    started_at?: string;
    finished_at?: string;
    created_at: string;
};

const statusOptions = ['QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'NEEDS_HUMAN', 'CANCELED'];
const stageOptions = ['SALES', 'ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE'];

export default function OperationsPage() {
    const [jobs, setJobs] = useState<JobRun[]>([]);
    const [stuckJobs, setStuckJobs] = useState<JobRun[]>([]);
    const [statusFilter, setStatusFilter] = useState('');
    const [stageFilter, setStageFilter] = useState('');
    const [projectId, setProjectId] = useState('');
    const [loading, setLoading] = useState(true);
    const [actionBusy, setActionBusy] = useState<string | null>(null);

    const loadJobs = async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (statusFilter) params.status_filter = statusFilter;
            if (stageFilter) params.stage = stageFilter;
            if (projectId) params.project_id = projectId;
            const [jobsResp, stuckResp] = await Promise.all([
                jobsAPI.listAdmin(Object.keys(params).length ? params : undefined),
                jobsAPI.listStuck(),
            ]);
            setJobs(jobsResp.data || []);
            setStuckJobs(stuckResp.data || []);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadJobs();
    }, []);

    const stuckIds = useMemo(() => new Set(stuckJobs.map(job => job.id)), [stuckJobs]);

    const handleRetry = async (jobId: string) => {
        setActionBusy(jobId);
        try {
            await jobsAPI.retry(jobId);
            await loadJobs();
        } finally {
            setActionBusy(null);
        }
    };

    const handleCancel = async (jobId: string) => {
        setActionBusy(jobId);
        try {
            await jobsAPI.cancel(jobId);
            await loadJobs();
        } finally {
            setActionBusy(null);
        }
    };

    return (
        <RequireCapability cap="view_operations">
        <div className="page-wrapper">
            <Navigation />
            <main className="page-container">
            <div className="page-header">
                <PageHeader
                    title="Operations"
                    purpose="Monitor job queue health, retries, and stuck runs."
                    variant="page"
                />
                <button className="btn-primary" onClick={loadJobs} disabled={loading}>
                    Refresh
                </button>
            </div>

            <div className="filter-card">
                <div className="filters">
                    <div className="field">
                        <label>Status</label>
                        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                            <option value="">All</option>
                            {statusOptions.map(option => (
                                <option key={option} value={option}>{option}</option>
                            ))}
                        </select>
                    </div>
                    <div className="field">
                        <label>Stage</label>
                        <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)}>
                            <option value="">All</option>
                            {stageOptions.map(option => (
                                <option key={option} value={option}>{option}</option>
                            ))}
                        </select>
                    </div>
                    <div className="field">
                        <label>Project ID</label>
                        <input
                            value={projectId}
                            onChange={(e) => setProjectId(e.target.value)}
                            placeholder="UUID"
                        />
                    </div>
                    <button className="btn-secondary" onClick={loadJobs} disabled={loading}>
                        Apply Filters
                    </button>
                </div>
            </div>

            <div className="table-card">
                <div className="table-header">
                    <h2>Job Queue</h2>
                    <span>{jobs.length} jobs</span>
                </div>
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Stage</th>
                                <th>Project</th>
                                <th>Attempts</th>
                                <th>Created</th>
                                <th>Started</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {jobs.map(job => (
                                <tr key={job.id} className={stuckIds.has(job.id) ? 'stuck' : ''}>
                                    <td>
                                        <span className={`pill status-${job.status.toLowerCase()}`}>
                                            {job.status}
                                        </span>
                                    </td>
                                    <td>{job.stage}</td>
                                    <td className="mono">{job.project_id}</td>
                                    <td>{job.attempts}/{job.max_attempts}</td>
                                    <td>{job.created_at ? new Date(job.created_at).toLocaleString() : '-'}</td>
                                    <td>{job.started_at ? new Date(job.started_at).toLocaleString() : '-'}</td>
                                    <td>
                                        <div className="actions">
                                            <button
                                                className="btn-tertiary"
                                                onClick={() => handleRetry(job.id)}
                                                disabled={actionBusy === job.id}
                                            >
                                                Retry
                                            </button>
                                            <button
                                                className="btn-danger"
                                                onClick={() => handleCancel(job.id)}
                                                disabled={actionBusy === job.id}
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {jobs.length === 0 && (
                                <tr>
                                    <td colSpan={7} className="empty">No jobs found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="table-card">
                <div className="table-header">
                    <h2>Stuck Jobs</h2>
                    <span>{stuckJobs.length} flagged</span>
                </div>
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Stage</th>
                                <th>Project</th>
                                <th>Started</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stuckJobs.map(job => (
                                <tr key={job.id}>
                                    <td>{job.status}</td>
                                    <td>{job.stage}</td>
                                    <td className="mono">{job.project_id}</td>
                                    <td>{job.started_at ? new Date(job.started_at).toLocaleString() : '-'}</td>
                                </tr>
                            ))}
                            {stuckJobs.length === 0 && (
                                <tr>
                                    <td colSpan={4} className="empty">No stuck jobs.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
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
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 24px;
                }
                .filter-card,
                .table-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                }
                .filters {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                    align-items: end;
                }
                .field label {
                    display: block;
                    font-size: 12px;
                    margin-bottom: 6px;
                    color: #6b7280;
                }
                .field input,
                .field select {
                    width: 100%;
                    padding: 8px 10px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
                .btn-primary,
                .btn-secondary,
                .btn-tertiary,
                .btn-danger {
                    padding: 8px 12px;
                    border-radius: 8px;
                    border: none;
                    cursor: pointer;
                    font-weight: 600;
                }
                .btn-primary {
                    background: #2563eb;
                    color: white;
                }
                .btn-secondary {
                    background: #e5e7eb;
                }
                .btn-tertiary {
                    background: #f3f4f6;
                }
                .btn-danger {
                    background: #ef4444;
                    color: white;
                }
                .table-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 12px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    text-align: left;
                    padding: 10px;
                    border-bottom: 1px solid #f3f4f6;
                    font-size: 13px;
                }
                .table-wrap {
                    overflow-x: auto;
                }
                .pill {
                    display: inline-flex;
                    padding: 4px 8px;
                    border-radius: 999px;
                    font-size: 11px;
                    font-weight: 600;
                }
                .status-queued { background: #e0f2fe; color: #0369a1; }
                .status-running { background: #fef3c7; color: #92400e; }
                .status-success { background: #dcfce7; color: #166534; }
                .status-failed { background: #fee2e2; color: #991b1b; }
                .status-needs_human { background: #ede9fe; color: #5b21b6; }
                .status-canceled { background: #f3f4f6; color: #6b7280; }
                .actions {
                    display: flex;
                    gap: 8px;
                }
                .stuck {
                    background: #fff7ed;
                }
                .mono {
                    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                    font-size: 12px;
                }
                .empty {
                    text-align: center;
                    color: #9ca3af;
                }
            `}</style>
            </main>
        </div>
        </RequireCapability>
    );
}
