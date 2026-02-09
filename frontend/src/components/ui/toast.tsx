import React from 'react';

export const Toast: React.FC<{ message: string; type?: 'info' | 'success' | 'error' }> = ({
  message,
  type = 'info',
}) => {
  const colors: Record<string, string> = {
    info: '#2563eb',
    success: '#16a34a',
    error: '#dc2626',
  };
  return (
    <div
      style={{
        background: colors[type],
        color: '#fff',
        padding: '8px 12px',
        borderRadius: 8,
        fontSize: 13,
      }}
    >
      {message}
    </div>
  );
};
