import React from 'react';

interface RuleStatusBadgeProps {
  actual: number;
  target: number;
  tolerance: number;
  label: string;
}

const RuleStatusBadge: React.FC<RuleStatusBadgeProps> = ({ actual, target, tolerance, label }) => {
  const diff = actual - target;
  const isOk = Math.abs(diff) <= tolerance;
  const isOver = diff > tolerance;

  let color = 'var(--accent-green)';
  let bg = 'rgba(34,197,94,0.15)';
  let statusText = 'OK';

  if (isOver) {
    color = 'var(--accent-red)';
    bg = 'rgba(239,68,68,0.15)';
    statusText = `+${diff.toFixed(1)}%`;
  } else if (!isOk) {
    color = 'var(--accent-orange)';
    bg = 'rgba(249,115,22,0.15)';
    statusText = `${diff.toFixed(1)}%`;
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-color)' }}>
      <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '14px', fontWeight: 600 }}>{actual.toFixed(1)}%</span>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>/ {target}%</span>
        <span style={{
          padding: '3px 10px',
          borderRadius: '20px',
          fontSize: '12px',
          fontWeight: 600,
          background: bg,
          color,
          minWidth: '60px',
          textAlign: 'center',
        }}>
          {isOk ? '✓ OK' : statusText}
        </span>
      </div>
    </div>
  );
};

export default RuleStatusBadge;
