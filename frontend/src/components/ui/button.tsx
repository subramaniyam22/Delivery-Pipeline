import React from 'react';

type ButtonVariant = 'default' | 'secondary' | 'ghost';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantStyles: Record<ButtonVariant, React.CSSProperties> = {
  default: { backgroundColor: '#2563eb', color: '#fff' },
  secondary: { backgroundColor: '#e5e7eb', color: '#111827' },
  ghost: { backgroundColor: 'transparent', color: '#2563eb' },
};

export const Button: React.FC<ButtonProps> = ({ variant = 'default', style, ...props }) => {
  return (
    <button
      {...props}
      style={{
        padding: '8px 14px',
        borderRadius: 6,
        border: '1px solid #e5e7eb',
        cursor: 'pointer',
        fontWeight: 600,
        ...variantStyles[variant],
        ...style,
      }}
    />
  );
};
