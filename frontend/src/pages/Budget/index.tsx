import { useEffect, useState } from 'react'
import { transactionsAPI, savingsAPI, categoriesAPI } from '../../services/api'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import type { TransactionStats, CompensationResult, Category } from '../../types'
import styles from './Budget.module.css'

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

export default function Budget() {
  const [stats, setStats] = useState<TransactionStats | null>(null)
  const [comp, setComp] = useState<CompensationResult | null>(null)
  const [cats, setCats] = useState<Category[]>([])

  useEffect(() => {
    transactionsAPI.stats({ month: currentMonth }).then(r => setStats(r.data))
    savingsAPI.compensation().then(r => setComp(r.data)).catch(() => {})
    categoriesAPI.list().then(r => setCats(r.data.results ?? r.data))
  }, [])

  const catMap = Object.fromEntries(stats?.by_category?.map(c => [c.category__id, c]) ?? [])

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Budget — Règle 50/30/20</h1>

      {/* Buckets overview */}
      <div className={styles.bucketsGrid}>
        {[
          { key: 'needs', label: 'Besoins', target: 50, color: 'var(--accent-blue)', icon: '🏠' },
          { key: 'wants', label: 'Envies', target: 30, color: 'var(--accent-purple)', icon: '🎬' },
          { key: 'savings', label: 'Épargne', target: 20, color: 'var(--accent-green)', icon: '🏦' },
        ].map(b => {
          const real = stats?.rule_503020[b.key as keyof typeof stats.rule_503020] ?? 0
          const gap = real - b.target
          return (
            <div key={b.key} className={styles.bucketCard} style={{ '--bc': b.color } as React.CSSProperties}>
              <div className={styles.bucketHeader}>
                <span className={styles.bucketIcon}>{b.icon}</span>
                <span className={styles.bucketLabel}>{b.label}</span>
                <span className={styles.bucketTarget}>{b.target}%</span>
              </div>
              <div className={styles.bucketReal} style={{ color: b.color }}>{real.toFixed(1)}%</div>
              <ProgressBar value={real} max={100} color={b.color} />
              <div className={styles.bucketGap} style={{ color: Math.abs(gap) <= 5 ? 'var(--accent-green)' : gap > 0 ? 'var(--accent-red)' : 'var(--accent-orange)' }}>
                {gap > 0 ? '+' : ''}{gap.toFixed(1)}% vs cible
              </div>
            </div>
          )
        })}
      </div>

      {/* Compensation plan */}
      {comp && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>🔄 Plan de compensation</h2>
          <CompensationPlanCard data={comp} />
        </section>
      )}

      {/* Category cards */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>📂 Par catégorie</h2>
        <div className={styles.catGrid}>
          {cats.filter(c => c.type === 'expense' && c.budget_limit).map(c => {
            const spent = parseFloat(String(catMap[c.id]?.total ?? 0))
            const limit = parseFloat(String(c.budget_limit ?? 0))
            const pct = limit > 0 ? (spent / limit) * 100 : 0
            return (
              <div key={c.id} className={styles.catCard}>
                <div className={styles.catHeader}>
                  <span style={{ color: c.color }}>{c.icon} {c.name}</span>
                  <span className={styles.catBucket} style={{ background: `${c.color}22`, color: c.color }}>{c.rule_bucket}</span>
                </div>
                <ProgressBar value={pct} color={c.color} showLabel />
                <div className={styles.catAmounts}>
                  <span style={{ color: pct >= 100 ? 'var(--accent-red)' : pct >= 80 ? 'var(--accent-orange)' : 'var(--text-muted)' }}>
                    {spent.toFixed(0)} €
                  </span>
                  <span> / {limit.toFixed(0)} €</span>
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
