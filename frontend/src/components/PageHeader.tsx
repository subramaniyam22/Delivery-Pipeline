import React from 'react';

type PageHeaderProps = {
    title: string;
    purpose?: string;
    affects?: string;
    align?: 'left' | 'center';
    variant?: 'page' | 'section';
};

export default function PageHeader({
    title,
    purpose,
    affects,
    align = 'left',
    variant = 'page',
}: PageHeaderProps) {
    const textAlign = align === 'center' ? 'center' : 'left';
    const titleStyle =
        variant === 'section'
            ? { fontSize: '18px', fontWeight: 600, color: '#1e293b', margin: 0 }
            : { fontSize: '24px', fontWeight: 700, color: '#1e293b', margin: 0 };
    const TitleTag = variant === 'section' ? 'h2' : 'h1';
    return (
        <div style={{ display: 'grid', gap: '4px', textAlign }}>
            <TitleTag style={titleStyle}>{title}</TitleTag>
            {purpose && (
                <p style={{ color: '#64748b', margin: 0, fontSize: '14px' }}>{purpose}</p>
            )}
            {affects && (
                <p style={{ color: '#94a3b8', margin: 0, fontSize: '12px' }}>
                    {affects}
                </p>
            )}
        </div>
    );
}
