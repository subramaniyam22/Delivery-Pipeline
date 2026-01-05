'use client';

import { Stage } from '@/lib/rbac';
import { Role } from '@/lib/auth';
import ArtifactUploader from './ArtifactUploader';

interface StagePanelProps {
    projectId: string;
    stage: Stage;
    userRole: Role;
    onAction?: () => void;
}

export default function StagePanel({
    projectId,
    stage,
    userRole,
    onAction,
}: StagePanelProps) {
    const canEdit = userRole === Role.ADMIN || userRole === Role.MANAGER;

    return (
        <div className="stage-panel">
            <h2>{stage} Stage</h2>

            {/* Onboarding Panel */}
            {stage === Stage.ONBOARDING &&
                (userRole === Role.CONSULTANT || canEdit) && (
                    <div>
                        <p>Update onboarding information and upload documents.</p>
                        <ArtifactUploader
                            projectId={projectId}
                            stage={Stage.ONBOARDING}
                            onUploadComplete={onAction}
                        />
                    </div>
                )}

            {/* Assignment Panel */}
            {stage === Stage.ASSIGNMENT && (userRole === Role.PC || canEdit) && (
                <div>
                    <p>Assign tasks to team members.</p>
                    <button onClick={onAction}>Publish Assignment Plan</button>
                </div>
            )}

            {/* Build Panel */}
            {stage === Stage.BUILD && (userRole === Role.BUILDER || canEdit) && (
                <div>
                    <p>Update build status and upload build artifacts.</p>
                    <ArtifactUploader
                        projectId={projectId}
                        stage={Stage.BUILD}
                        onUploadComplete={onAction}
                    />
                    <button onClick={onAction}>Mark Build Complete</button>
                </div>
            )}

            {/* Test Panel */}
            {stage === Stage.TEST && (userRole === Role.TESTER || canEdit) && (
                <div>
                    <p>Execute tests and upload test reports.</p>
                    <ArtifactUploader
                        projectId={projectId}
                        stage={Stage.TEST}
                        onUploadComplete={onAction}
                    />
                    <button onClick={onAction}>Mark Testing Complete</button>
                </div>
            )}

            {/* Admin/Manager Actions */}
            {canEdit && (
                <div className="admin-actions">
                    <h3>Admin Actions</h3>
                    <button onClick={onAction}>Advance Workflow</button>
                    {stage === Stage.BUILD && (
                        <button onClick={onAction}>Approve Build</button>
                    )}
                    <button onClick={onAction}>Send Back</button>
                </div>
            )}

            <style jsx>{`
        .stage-panel {
          border: 1px solid #ddd;
          padding: 20px;
          border-radius: 4px;
          margin: 20px 0;
        }
        button {
          background: #2196f3;
          color: white;
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          margin: 5px;
        }
        button:hover {
          background: #1976d2;
        }
        .admin-actions {
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid #ddd;
        }
      `}</style>
        </div>
    );
}
