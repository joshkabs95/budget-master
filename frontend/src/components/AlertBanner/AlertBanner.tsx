import { motion, AnimatePresence } from 'framer-motion'
import type { Insight } from '../../types'
import styles from './AlertBanner.module.css'

const COLOR: Record<string, string> = {
  green: 'var(--accent-green)',
  orange: 'var(--accent-orange)',
  red: 'var(--accent-red)',
}

export default function AlertBanner({ insights }: { insights: Insight[] }) {
  if (!insights.length) return null
  return (
    <div className={styles.list}>
      <AnimatePresence>
        {insights.map((ins, i) => (
          <motion.div
            key={i}
            className={styles.banner}
            style={{ '--c': COLOR[ins.severity] || 'var(--accent-orange)' } as React.CSSProperties}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <span className={styles.dot} />
            <span className={styles.msg}>{ins.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
