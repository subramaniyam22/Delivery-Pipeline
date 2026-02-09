import React from 'react';

export const Table: React.FC<React.TableHTMLAttributes<HTMLTableElement>> = ({ style, ...props }) => (
  <table
    {...props}
    style={{
      width: '100%',
      borderCollapse: 'collapse',
      ...style,
    }}
  />
);

export const Th: React.FC<React.ThHTMLAttributes<HTMLTableCellElement>> = ({ style, ...props }) => (
  <th
    {...props}
    style={{
      textAlign: 'left',
      borderBottom: '1px solid #e5e7eb',
      padding: '8px 10px',
      fontSize: 12,
      color: '#6b7280',
      ...style,
    }}
  />
);

export const Td: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({ style, ...props }) => (
  <td
    {...props}
    style={{
      borderBottom: '1px solid #f3f4f6',
      padding: '8px 10px',
      fontSize: 13,
      color: '#111827',
      ...style,
    }}
  />
);
