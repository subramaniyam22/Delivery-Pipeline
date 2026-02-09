import React from 'react';

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  tabs: { value: string; label: string }[];
}

export const Tabs: React.FC<TabsProps> = ({ value, onValueChange, tabs }) => (
  <div style={{ display: 'flex', gap: 8 }}>
    {tabs.map((tab) => (
      <button
        key={tab.value}
        onClick={() => onValueChange(tab.value)}
        style={{
          padding: '6px 12px',
          borderRadius: 6,
          border: '1px solid #e5e7eb',
          background: value === tab.value ? '#2563eb' : '#fff',
          color: value === tab.value ? '#fff' : '#111827',
          cursor: 'pointer',
        }}
      >
        {tab.label}
      </button>
    ))}
  </div>
);
