import styles from './RuleStatusBadge.module.css'

type Severity = 'green' | 'yellow' | 'orange' | 'red' | 'critical'

const LABELS: Record<Severity, string> = {
  green: '✅ Objectif atteint',
  yellow: '⚠️ Léger écart',
  orange: '🟠 Attention',
  red: '🔴 Alerte',
  critical: '🚨 Critique',
}

export default function RuleStatusBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`${styles.badge} ${styles[severity]}`}>
      {LABELS[severity]}
    </span>
  )
}
