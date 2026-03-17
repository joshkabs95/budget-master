import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import styles from './KPICard.module.css'

interface Props {
  label: string
  value: number
  icon: string
  color: string
  prefix?: string
  suffix?: string
  trend?: number
  index?: number
}

function useCountUp(target: number, duration = 800) {
  const [current, setCurrent] = useState(0)
  useEffect(() => {
    const start = Date.now()
    const tick = () => {
      const elapsed = Date.now() - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCurrent(target * eased)
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [target, duration])
  return current
}

export default function KPICard({ label, value, icon, color, prefix = '', suffix = '€', trend, index = 0 }: Props) {
  const animated = useCountUp(value)
  const formatted = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(animated)

  return (
    <motion.div
      className={styles.card}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4, ease: 'easeOut' }}
      style={{ '--card-color': color } as React.CSSProperties}
    >
      <div className={styles.header}>
        <span className={styles.icon}>{icon}</span>
        {trend !== undefined && (
          <span className={`${styles.trend} ${trend >= 0 ? styles.positive : styles.negative}`}>
            {trend >= 0 ? '+' : ''}{trend.toFixed(1)}%
          </span>
        )}
      </div>
      <div className={styles.value}>{prefix}{formatted}{suffix}</div>
      <div className={styles.label}>{label}</div>
      <div className={styles.glow} />
    </motion.div>
  )
}
