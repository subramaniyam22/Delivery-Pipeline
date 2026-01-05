'use client';

import { Stage } from '@/lib/rbac';

interface ProjectTimelineProps {
    currentStage: Stage;
}

const stages = [
    { key: Stage.ONBOARDING, label: 'Onboarding' },
    { key: Stage.ASSIGNMENT, label: 'Assignment' },
    { key: Stage.BUILD, label: 'Build' },
    { key: Stage.TEST, label: 'Test' },
    { key: Stage.DEFECT_VALIDATION, label: 'Defect Validation' },
    { key: Stage.COMPLETE, label: 'Complete' },
];

export default function ProjectTimeline({ currentStage }: ProjectTimelineProps) {
    const currentIndex = stages.findIndex((s) => s.key === currentStage);

    return (
        <div className="timeline">
            {stages.map((stage, index) => {
                const isActive = stage.key === currentStage;
                const isCompleted = index < currentIndex;

                return (
                    <div key={stage.key} className="timeline-item">
                        <div
                            className={`timeline-marker ${isActive ? 'active' : isCompleted ? 'completed' : 'pending'
                                }`}
                        >
                            {index + 1}
                        </div>
                        <div className="timeline-label">{stage.label}</div>
                    </div>
                );
            })}

            <style jsx>{`
        .timeline {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px 0;
          position: relative;
        }
        .timeline::before {
          content: '';
          position: absolute;
          top: 35px;
          left: 0;
          right: 0;
          height: 2px;
          background: #e0e0e0;
          z-index: 0;
        }
        .timeline-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          z-index: 1;
          flex: 1;
        }
        .timeline-marker {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          background: white;
          border: 2px solid #e0e0e0;
          margin-bottom: 10px;
        }
        .timeline-marker.active {
          background: #2196f3;
          color: white;
          border-color: #2196f3;
        }
        .timeline-marker.completed {
          background: #4caf50;
          color: white;
          border-color: #4caf50;
        }
        .timeline-label {
          font-size: 12px;
          text-align: center;
          max-width: 100px;
        }
      `}</style>
        </div>
    );
}
