'use client';

import { useEffect, useMemo, useState } from 'react';
import { auditLogsAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, Th, Td } from '@/components/ui/table';

type AuditLog = {
    id: string;
    project_id?: string | null;
    actor_user_id: string;
    actor?: { id: string; name: string; email: string; role: string };
    action: string;
    payload_json: Record<string, any>;
    created_at: string;
};

export default function AuditLogsPage() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(50);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [actorFilter, setActorFilter] = useState('');
    const [actionFilter, setActionFilter] = useState('all');
    const [targetType, setTargetType] = useState('all');
    const [targetId, setTargetId] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    const isUuid = (value: string) =>
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);

    const actorIdInvalid = actorFilter.length > 0 && !isUuid(actorFilter);
    const targetIdInvalid =
        targetId.length > 0 && targetType === 'project' && !isUuid(targetId);

    const actions = useMemo(() => {
        const unique = new Set(logs.map((l) => l.action));
        return Array.from(unique);
    }, [logs]);

    const loadLogs = async () => {
        setLoading(true);
        setError('');
        try {
            const params: Record<string, any> = { page, page_size: pageSize };
            if (actorFilter) params.actor_id = actorFilter;
            if (actionFilter !== 'all') params.action = actionFilter;
            if (targetType !== 'all' && targetId) {
                params.target_type = targetType;
                params.target_id = targetId;
            } else if (targetId) {
                params.target = targetId;
            }
            if (startDate) params.start_date = new Date(startDate).toISOString();
            if (endDate) params.end_date = new Date(endDate).toISOString();
            const res = await auditLogsAPI.list(params);
            setLogs(res.data.items || []);
            setTotal(res.data.total || 0);
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Failed to load audit logs');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadLogs();
    }, [page]);

    const totalPages = Math.max(1, Math.ceil(total / pageSize));

    return (
        <RequireCapability cap="view_audit_logs">
        <div className="page-wrapper">
            <Navigation />
            <main className="container" style={{ padding: '2rem var(--space-lg)', maxWidth: '1600px', width: '100%', margin: '0 auto' }}>
                <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <PageHeader
                        title="Audit Logs"
                        purpose="Review system actions across users, configs, and workflows."
                        variant="page"
                    />
                    <button className="btn-primary" onClick={loadLogs} disabled={loading}>
                        Refresh
                    </button>
                </header>

                <Card style={{ marginBottom: '16px' }}>
                    <CardHeader>
                        <CardTitle>Filters</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                            <label style={{ fontSize: '12px', color: '#64748b' }}>
                                Actor (User ID)
                                <input
                                    value={actorFilter}
                                    onChange={(e) => setActorFilter(e.target.value)}
                                    placeholder="UUID"
                                    style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                                />
                                {actorIdInvalid && (
                                    <span style={{ display: 'block', marginTop: '6px', fontSize: '11px', color: '#ef4444' }}>
                                        Enter a valid UUID.
                                    </span>
                                )}
                            </label>
                            <label style={{ fontSize: '12px', color: '#64748b' }}>
                                Action Type
                                <select
                                    value={actionFilter}
                                    onChange={(e) => setActionFilter(e.target.value)}
                                    style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                                >
                                    <option value="all">All</option>
                                    {actions.map((action) => (
                                        <option key={action} value={action}>
                                            {action}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label style={{ fontSize: '12px', color: '#64748b' }}>
                                Target Type
                                <select
                                    value={targetType}
                                    onChange={(e) => setTargetType(e.target.value)}
                                    style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                                >
                                    <option value="all">Any</option>
                                    <option value="project">Project</option>
                                    <option value="template">Template</option>
                                    <option value="user">User</option>
                                </select>
                            </label>
                            <label style={{ fontSize: '12px', color: '#64748b' }}>
                                Target ID
                                <input
                                    value={targetId}
                                    onChange={(e) => setTargetId(e.target.value)}
                                    placeholder="Project/Template/User ID"
                                    style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                                />
                                {targetIdInvalid && (
                                    <span style={{ display: 'block', marginTop: '6px', fontSize: '11px', color: '#ef4444' }}>
                                        Project IDs must be valid UUIDs.
                                    </span>
                                )}
                            </label>
                            <label style={{ fontSize: '12px', color: '#64748b' }}>
                                Start Date
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                                />
                            </label>
                            <label style={{ fontSize: '12px', color: '#64748b' }}>
                                End Date
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                                />
                            </label>
                            <button
                                className="btn-secondary"
                                onClick={() => { setPage(1); loadLogs(); }}
                                disabled={loading || actorIdInvalid || targetIdInvalid}
                            >
                                Apply
                            </button>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Audit Logs</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {error && <p style={{ color: '#ef4444' }}>{error}</p>}
                        <Table>
                            <thead>
                                <tr>
                                    <Th>Timestamp</Th>
                                    <Th>Actor</Th>
                                    <Th>Action</Th>
                                    <Th>Target</Th>
                                    <Th>Details</Th>
                                </tr>
                            </thead>
                            <tbody>
                                {logs.map((log) => (
                                    <tr key={log.id}>
                                        <Td>{new Date(log.created_at).toLocaleString()}</Td>
                                        <Td>
                                            <div>{log.actor?.name || log.actor_user_id}</div>
                                            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{log.actor?.role || '—'}</div>
                                        </Td>
                                        <Td>{log.action}</Td>
                                        <Td>{log.project_id || log.payload_json?.template_id || log.payload_json?.user_id || '—'}</Td>
                                        <Td style={{ fontSize: '12px', color: '#64748b' }}>
                                            {Object.keys(log.payload_json || {}).length > 0 ? JSON.stringify(log.payload_json) : '—'}
                                        </Td>
                                    </tr>
                                ))}
                                {logs.length === 0 && !loading && (
                                    <tr>
                                        <Td colSpan={5} style={{ textAlign: 'center', color: '#64748b' }}>
                                            No audit logs found.
                                        </Td>
                                    </tr>
                                )}
                            </tbody>
                        </Table>
                        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', color: '#64748b' }}>
                                {total} total
                            </span>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <button
                                    className="btn-secondary"
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    disabled={page <= 1 || loading}
                                >
                                    Prev
                                </button>
                                <span style={{ fontSize: '12px', color: '#64748b' }}>
                                    Page {page} / {totalPages}
                                </span>
                                <button
                                    className="btn-secondary"
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    disabled={page >= totalPages || loading}
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </main>
        </div>
        </RequireCapability>
    );
}
