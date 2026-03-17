import React from 'react';
import { CompensationPlan } from '../types';

interface Props {
  plan: CompensationPlan;
}

const severityConfig = {
  green: { color: 'var(--accent-green)', icon: '✅', label: 'Objectif atteint', bg: 'rgba(34,197,94,0.1)' },
  yellow: { color: '#eab308', icon: '⚠️', label: 'Léger écart', bg: 'rgba(234,179,8,0.1)' },
  orange: { color: 'var(--accent-orange)', icon: '🟡', label: 'Écart modéré', bg: 'rgba(249,115,22,0.1)' },
  red: { color: 'var(--accent-red)', icon: '🔴', label: 'Besoins compressés', bg: 'rgba(239,68,68,0.1)' },
  critical: { color: 'var(--accent-red)', icon: '🚨', label: 'Écart non couvrable', bg: 'rgba(239,68,68,0.15)' },
  no_rule: { color: 'var(--text-muted)', icon: 'ℹ️', label: 'Aucune règle configurée', bg: 'rgba(107,107,126,0.1)' },
};

const CompensationPlanCard: React.FC<Props> = ({ plan }) => {
  if (!plan) return null;

  const status = plan.status as keyof typeof severityConfig || 'no_rule';
  const config = severityConfig[status] || severityConfig.no_rule;

  if (status === 'green') {
    return (
      <div className="card" style={{ borderLeft: `3px solid ${config.color}`, background: config.bg }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>{config.icon}</span>
          <div>
            <div style={{ fontWeight: 600, color: config.color }}>Règle 50/30/20 respectée</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Votre taux d'épargne atteint l'objectif ce mois-ci.</div>
          </div>
        </div>
      </div>
    );
  }

  const p = plan.plan;
  if (!p) return null;

  return (
    <div className="card fade-in" style={{ borderLeft: `3px solid ${config.color}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span style={{ fontSize: '24px' }}>{config.icon}</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: '16px', color: config.color }}>
            Plan de compensation — {config.label}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Rattrapage sur {p.catchup_months} mois
          </div>
        </div>
      </div>

      {p.steps.map((step, i) => (
        <div key={i} style={{
          background: 'var(--bg-elevated)',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '8px',
          border: step.lever === 'needs' ? '1px solid rgba(239,68,68,0.3)' : '1px solid var(--border-color)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                {step.lever === 'wants' ? '🎮 Envies' : '🏠 Besoins'}
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: '13px', marginLeft: '8px' }}>
                Réduire de {step.cut.toFixed(1)}%
              </span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ color: 'var(--accent-orange)', fontWeight: 600 }}>
                → {step.new_target.toFixed(1)}%
              </div>
              {step.monthly_euros !== undefined && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  ≈ {step.monthly_euros.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })} économisés
                </div>
              )}
            </div>
          </div>
          {step.warning && (
            <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>⚠️</span> {step.warning}
            </div>
          )}
        </div>
      ))}

      {p.uncoverable_gap > 0 && (
        <div style={{ marginTop: '8px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', fontSize: '13px', color: 'var(--accent-red)' }}>
          🚨 Écart non couvrable : {p.uncoverable_gap.toFixed(1)}% — envisagez d'augmenter vos revenus
        </div>
      )}

      {p.suggestions && p.suggestions.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>
            💡 Suggestions concrètes
          </div>
          {p.suggestions.map((s, i) => (
            <div key={i} style={{ fontSize: '13px', color: 'var(--text-primary)', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
              {s.suggestion}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CompensationPlanCard;
