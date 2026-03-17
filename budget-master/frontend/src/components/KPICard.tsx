import React from 'react';

interface KPICardProps {
  title: string;
  value: string;
  icon: string;
  color?: string;
  trend?: number;
  subtitle?: string;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, icon, color = 'var(--accent-gold)', trend, subtitle }) => {
  return (
    <div className="card fade-in" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: color }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>{title}</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
          {subtitle && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{subtitle}</div>
          )}
          {trend !== undefined && (
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              marginTop: '8px',
              fontSize: '12px',
              color: trend >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
            }}>
              <span>{trend >= 0 ? '↑' : '↓'}</span>
              <span>{Math.abs(trend).toFixed(1)}%</span>
            </div>
          )}
        </div>
        <div style={{
          width: '48px',
          height: '48px',
          borderRadius: '12px',
          background: `${color}22`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '22px',
        }}>
          {icon}
        </div>
      </div>
    </div>
  );
};

export default KPICard;
