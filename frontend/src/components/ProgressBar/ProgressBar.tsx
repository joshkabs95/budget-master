import { motion } from 'framer-motion'
import styles from './ProgressBar.module.css'

interface Props {
  value: number
  max?: number
  color?: string
  showLabel?: boolean
  height?: number
  animated?: boolean
}

function getColor(pct: number, color?: string): string {
  if (color) return color
  if (pct >= 100) return 'var(--accent-red)'
  if (pct >= 80) return 'var(--accent-orange)'
  return 'var(--accent-green)'
}

export default function ProgressBar({ value, max = 100, color, showLabel = false, height = 6, animated = true }: Props) {
  const pct = Math.min((value / max) * 100, 100)
  const barColor = getColor(pct, color)

  return (
    <div className={styles.wrapper}>
      <div className={styles.track} style={{ height }}>
        <motion.div
          className={styles.fill}
          style={{ backgroundColor: barColor, height: '100%' }}
          initial={animated ? { width: 0 } : { width: `${pct}%` }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      {showLabel && <span className={styles.label}>{pct.toFixed(0)}%</span>}
    </div>
  )
}
