import { motion } from 'framer-motion'
import type { CompensationResult } from '../../types'
import styles from './CompensationPlanCard.module.css'

interface Props { data: CompensationResult }

const SEV_COLORS: Record<string, string> = {
  green: 'var(--accent-green)',
  yellow: '#eab308',
  orange: 'var(--accent-orange)',
  red: 'var(--accent-red)',
  critical: 'var(--accent-red)',
}

export default function CompensationPlanCard({ data }: Props) {
  if (data.status === 'green' || !data.plan) {
    return (
      <div className={styles.green}>
        <span>✅</span>
        <span>Règle 50/30/20 respectée — épargne dans la zone cible.</span>
      </div>
    )
  }
  const { plan } = data
  const color = SEV_COLORS[plan.severity] || 'var(--accent-orange)'

  return (
    <motion.div className={styles.card} style={{ '--sev': color } as React.CSSProperties}
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div className={styles.header}>
        <span className={styles.title}>Plan de compensation</span>
        <span className={styles.badge} style={{ color, background: `${color}22` }}>
          {plan.severity.toUpperCase()}
        </span>
      </div>
      <p className={styles.message}>{plan.message}</p>
      <div className={styles.steps}>
        {plan.monthly_amounts.map((step, i) => (
          <div key={i} className={styles.step}>
            <div className={styles.stepHeader}>
              <span>{step.lever === 'wants' ? '🎬 Envies' : '🏠 Besoins'}</span>
              {step.warning && <span className={styles.warning}>{step.warning}</span>}
            </div>
            <div className={styles.stepDetail}>
              Réduire de <strong>{step.cut.toFixed(1)}%</strong> → nouveau cible <strong>{step.new_target.toFixed(1)}%</strong>
              {step.monthly_euros !== undefined && (
                <span className={styles.euros}> (~{step.monthly_euros.toFixed(0)}€/mois)</span>
              )}
            </div>
          </div>
        ))}
      </div>
      {plan.suggestions.length > 0 && (
        <div className={styles.suggestions}>
          <div className={styles.sugTitle}>Suggestions basées sur tes dépenses :</div>
          {plan.suggestions.map((s, i) => (
            <div key={i} className={styles.suggestion}>
              <span>{s.icon} {s.category}</span>
              <span className={styles.sugAmt}>{s.suggestion}</span>
            </div>
          ))}
        </div>
      )}
      <div className={styles.footer}>
        Étalement recommandé : <strong>{plan.catchup_months} mois</strong>
      </div>
    </motion.div>
  )
}
