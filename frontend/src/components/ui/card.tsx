import React from 'react';

export const Card: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ style, ...props }) => (
  <div
    {...props}
    style={{
      background: '#fff',
      border: '1px solid #e5e7eb',
      borderRadius: 10,
      padding: 16,
      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      ...style,
    }}
  />
);

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ style, ...props }) => (
  <div {...props} style={{ marginBottom: 12, ...style }} />
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({ style, ...props }) => (
  <h3 {...props} style={{ margin: 0, fontSize: 16, ...style }} />
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ style, ...props }) => (
  <div {...props} style={{ ...style }} />
);
