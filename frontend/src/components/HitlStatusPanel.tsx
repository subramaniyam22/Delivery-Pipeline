'use client';

import { useState } from 'react';
import { hasCapability } from '@/lib/rbac';

type PendingApproval = {
    stage?: string;
    type?: string;
    created_at?: string;
    approver_roles?: string[];
};

type HitlStatusPanelProps = {
    project: any;
    currentUser: any;
    onApprove?: (stage: string) => Promise<void>;
};

export default function HitlStatusPanel({ project, currentUser, onApprove }: HitlStatusPanelProps) {
    const [showApprovals, setShowApprovals] = useState(false);
    const [approving, setApproving] = useState(false);

    const approvals: PendingApproval[] = project?.pending_approvals || [];
    const count = project?.pending_approvals_count ?? approvals.length;
    if (!count) return null;

    const stage = approvals[0]?.stage || project?.current_stage;
    const role = currentUser?.role;
    const isAdminManager = role === 'ADMIN' || role === 'MANAGER';
    const canApprove = isAdminManager && hasCapability(currentUser, 'approve_hitl');
    const canSeeActions = canApprove;
    const message =
        role === 'BUILDER' || role === 'TESTER'
            ? 'Blocked by approval. Waiting for Manager/Admin.'
            : role === 'CONSULTANT' || role === 'PC'
                ? 'Approval required to proceed. Contact Manager/Admin or request approval.'
                : 'Approval pending.';

    const handleApprove = async () => {
        if (!stage || !onApprove) return;
        setApproving(true);
        try {
            await onApprove(stage);
        } finally {
            setApproving(false);
        }
    };

    return (
        <div className="hitl-status-panel">
            <div className="approval-notice">
                {message} This project is waiting for approval to proceed to{' '}
                <strong>{stage || 'the next stage'}</strong>.
            </div>
            <button
                className="approval-link"
                type="button"
                onClick={() => setShowApprovals((prev) => !prev)}
            >
                {showApprovals ? 'Hide approvals' : 'View approvals'}
            </button>
            {showApprovals && (
                <div className="approval-panel">
                    {(approvals.length === 0) ? (
                        <div className="approval-empty">No approvals pending.</div>
                    ) : (
                        <div className="approval-list">
                            {approvals.map((item, idx) => (
                                <div key={`${item.stage}-${item.created_at || idx}`} className="approval-item">
                                    <div className="approval-stage">{item.stage}</div>
                                    <div className="approval-meta">
                                        <span>
                                            Requested:{' '}
                                            {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                                        </span>
                                        <span>
                                            Approvers: {(item.approver_roles || ['ADMIN', 'MANAGER']).join(', ')}
                                        </span>
                                    <span>
                                        Type: {item.type || 'HITL gate'}
                                    </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                    {canSeeActions && (
                        <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                            <button
                                className="btn-advance"
                                onClick={handleApprove}
                                disabled={approving || !onApprove}
                                title={!onApprove ? 'Coming soon' : undefined}
                                style={!onApprove ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}
                            >
                                {approving ? 'Approving...' : 'Approve'}
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
