import React from 'react';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger';

const colors: Record<BadgeVariant, string> = {
  default: '#e5e7eb',
  success: '#16a34a',
  warning: '#f59e0b',
  danger: '#dc2626',
};

export const Badge: React.FC<{ variant?: BadgeVariant; children: React.ReactNode }> = ({
  variant = 'default',
  children,
}) => (
  <span
    style={{
      background: colors[variant],
      color: variant === 'default' ? '#111827' : '#fff',
      padding: '4px 8px',
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 600,
    }}
  >
    {children}
  </span>
);
