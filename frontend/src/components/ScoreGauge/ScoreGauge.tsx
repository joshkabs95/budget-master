import { motion } from 'framer-motion'
import styles from './ScoreGauge.module.css'

interface Props { score: number; size?: number }

export default function ScoreGauge({ score, size = 120 }: Props) {
  const r = 40
  const circ = 2 * Math.PI * r
  const clamped = Math.max(0, Math.min(100, score))
  const offset = circ - (clamped / 100) * circ
  const color = clamped >= 70 ? 'var(--accent-green)' : clamped >= 40 ? 'var(--accent-orange)' : 'var(--accent-red)'

  return (
    <div className={styles.wrapper} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
        <motion.circle
          cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div className={styles.label}>
        <span className={styles.score} style={{ color }}>{clamped}</span>
        <span className={styles.max}>/100</span>
      </div>
    </div>
  )
}
