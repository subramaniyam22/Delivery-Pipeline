import React, { useEffect, useState } from 'react';

interface NotificationToastProps {
    message: string;
    type?: 'info' | 'urgent';
    onClose: () => void;
}

const NotificationToast: React.FC<NotificationToastProps> = ({ message, type = 'info', onClose }) => {
    useEffect(() => {
        if (type === 'urgent') return; // Persistent for urgent

        const timer = setTimeout(() => {
            onClose();
        }, 5000);
        return () => clearTimeout(timer);
    }, [type, onClose]);

    const bgColor = type === 'urgent' ? '#ef4444' : '#3b82f6';

    return (
        <div style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: 'white',
            borderLeft: `4px solid ${bgColor}`,
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
            padding: '16px',
            borderRadius: '8px',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'start',
            gap: '12px',
            maxWidth: '400px',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <div style={{
                color: bgColor,
                fontSize: '20px'
            }}>
                {type === 'urgent' ? '⚠️' : 'ℹ️'}
            </div>
            <div style={{ flex: 1 }}>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: 600, color: '#1e293b' }}>
                    {type === 'urgent' ? 'Urgent Alert' : 'Notification'}
                </h4>
                <p style={{ margin: 0, fontSize: '14px', color: '#64748b', lineHeight: '1.4' }}>
                    {message}
                </p>
            </div>
            <button
                onClick={onClose}
                style={{
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    fontSize: '20px',
                    padding: '4px',
                    lineHeight: '1',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.color = '#475569';
                    e.currentTarget.style.background = '#f1f5f9';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.color = '#94a3b8';
                    e.currentTarget.style.background = 'none';
                }}
            >
                ×
            </button>
            <style jsx global>{`
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default NotificationToast;
