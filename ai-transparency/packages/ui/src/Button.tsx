import React from 'react';

export function Button({ children, variant = 'primary' }: { children: React.ReactNode; variant?: 'primary' | 'secondary' }) {
  const style: React.CSSProperties = {
    borderRadius: 10,
    padding: '10px 16px',
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
    background: variant === 'primary' ? '#2563eb' : '#111827',
    color: '#ffffff'
  };

  return <button style={style}>{children}</button>;
}
