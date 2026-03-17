import { useEffect, useState } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { transactionsAPI } from '../../services/api'
import ScoreGauge from '../../components/ScoreGauge/ScoreGauge'
import type { TransactionStats } from '../../types'
import styles from './Analytics.module.css'

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

export default function Analytics() {
  const [stats, setStats] = useState<TransactionStats | null>(null)
  const [score, setScore] = useState(0)

  useEffect(() => {
    transactionsAPI.stats({ month: currentMonth }).then(r => {
      setStats(r.data)
      // Compute simple score
      const s = r.data
      if (s.income > 0) {
        const savRate = s.savings_rate
        const budgetScore = Math.max(0, 100 - Math.abs(s.rule_503020.needs - 50) * 2 - Math.abs(s.rule_503020.wants - 30) * 2)
        const savingsScore = Math.min(100, (savRate / 20) * 100)
        setScore(Math.round(budgetScore * 0.4 + savingsScore * 0.4 + 20))
      }
    })
  }, [])

  const trendMap: Record<string, Record<string, number>> = {}
  stats?.trend?.forEach(t => {
    const m = typeof t.month === 'string' ? t.month.slice(0, 7) : new Date(t.month).toISOString().slice(0, 7)
    if (!trendMap[m]) trendMap[m] = {}
    trendMap[m][t.type] = (trendMap[m][t.type] ?? 0) + parseFloat(String(t.total))
  })
  const trendArr = Object.entries(trendMap).slice(-12).map(([m, v]) => ({
    month: m.slice(5),
    savings_rate: v.income ? parseFloat(((v.saving ?? 0) / v.income * 100).toFixed(1)) : 0,
  }))

  const pieData = stats?.by_category?.slice(0, 6).map(c => ({
    name: c.category__name ?? 'Autre',
    value: parseFloat(String(c.total)),
    color: c.category__color ?? '#6b6b7e',
  })) ?? []

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Analytics</h1>

      <div className={styles.grid2}>
        {/* Score */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>🏆 Score financier</h2>
          <div className={styles.scoreCenter}>
            <ScoreGauge score={score} size={140} />
            <div className={styles.scoreBreakdown}>
              <div>Respect budget <span>40%</span></div>
              <div>Règle épargne <span>40%</span></div>
              <div>Objectifs <span>20%</span></div>
            </div>
          </div>
        </section>

        {/* Pie */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>🍩 Répartition</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={2}>
                {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Pie>
              <Tooltip formatter={(v: number) => `${v.toFixed(0)} €`} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.75rem' }} />
            </PieChart>
          </ResponsiveContainer>
        </section>
      </div>

      {/* Savings rate trend */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>📈 Taux d'épargne mensuel</h2>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={trendArr} barSize={20}>
            <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} formatter={(v: number) => `${v} %`} />
            <Bar dataKey="savings_rate" radius={[4,4,0,0]}>
              {trendArr.map((e, i) => <Cell key={i} fill={e.savings_rate >= 20 ? 'var(--accent-green)' : e.savings_rate >= 15 ? 'var(--accent-orange)' : 'var(--accent-red)'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      {/* Top categories */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>🏆 Top dépenses</h2>
        <div className={styles.topList}>
          {stats?.by_category?.slice(0, 5).map((c, i) => (
            <div key={i} className={styles.topRow}>
              <span className={styles.topRank}>{i + 1}</span>
              <span style={{ color: c.category__color }}>{c.category__icon} {c.category__name}</span>
              <span className={styles.topAmt}>{parseFloat(String(c.total)).toFixed(0)} €</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
