import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, CartesianGrid, AreaChart, Area, ReferenceLine,
} from 'recharts'
import { transactionsAPI } from '../../services/api'
import ScoreGauge from '../../components/ScoreGauge/ScoreGauge'
import type { TransactionStats, ScoreMonth } from '../../types'
import styles from './Analytics.module.css'

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

function toMonthStr(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function shiftMonth(m: string, delta: number): string {
  const [y, mo] = m.split('-').map(Number)
  return toMonthStr(new Date(y, mo - 1 + delta, 1))
}

function scoreColor(s: number) {
  if (s >= 75) return '#34d399'
  if (s >= 50) return '#fbbf24'
  return '#f87171'
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#1e2235', border: '1px solid #3a3f5c', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      {label && <div style={{ color: '#f1f5f9', fontWeight: 600, marginBottom: 4 }}>{label}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: '#cbd5e1' }}>
          <span style={{ color: p.color ?? '#f1f5f9' }}>■</span>{' '}
          {p.name} : {typeof p.value === 'number' ? p.value.toFixed(0) : p.value}{p.unit ?? ' €'}
        </div>
      ))}
    </div>
  )
}

function generateCoaching(history: ScoreMonth[], stats: TransactionStats | null): string[] {
  const messages: string[] = []
  if (!stats || !history.length) return messages

  const last = history[history.length - 1]
  const prev = history[history.length - 2]

  if (prev && last.score > prev.score + 5)
    messages.push(`📈 Score en hausse de ${last.score - prev.score} pts ce mois — continuez !`)
  else if (prev && last.score < prev.score - 5)
    messages.push(`📉 Score en baisse de ${prev.score - last.score} pts vs le mois dernier`)

  const avgSavRate = history.reduce((s, m) => s + m.savings_rate, 0) / history.length
  if (avgSavRate < 10)
    messages.push(`🎯 Taux d'épargne moyen : ${avgSavRate.toFixed(1)}% — visez 20% progressivement`)
  else if (avgSavRate >= 20)
    messages.push(`✅ Excellent taux d'épargne moyen : ${avgSavRate.toFixed(1)}% sur 6 mois`)

  const rule = stats.rule_503020
  if (rule.needs > 60)
    messages.push(`⚠️ Vos besoins représentent ${rule.needs}% de vos revenus — la norme est 50%`)
  if (rule.wants > 35)
    messages.push(`🛍️ Vos envies sont à ${rule.wants}% — réduire à 30% libèrerait ~${((rule.wants - 30) / 100 * stats.income).toFixed(0)} €/mois`)
  if (rule.savings < 10 && stats.income > 0)
    messages.push(`💡 Automatisez un virement épargne dès le jour du salaire pour atteindre 20%`)

  if (stats.by_category?.[0]) {
    const top = stats.by_category[0]
    const pct = (top.total / stats.expenses * 100).toFixed(0)
    messages.push(`🏆 ${top.category__icon} ${top.category__name} représente ${pct}% de vos dépenses ce mois`)
  }

  return messages.slice(0, 4)
}

export default function Analytics() {
  const [activeMonth, setActiveMonth] = useState(currentMonth)
  const [stats, setStats] = useState<TransactionStats | null>(null)
  const [history, setHistory] = useState<ScoreMonth[]>([])
  const [score, setScore] = useState(0)
  const [weekday, setWeekday] = useState<any[]>([])
  const activeYear = activeMonth.slice(0, 4)

  useEffect(() => {
    transactionsAPI.stats({ month: activeMonth }).then(r => {
      const s = r.data
      setStats(s)
      if (s.income > 0) {
        const budgetScore = Math.max(0, 100 - Math.abs(s.rule_503020.needs - 50) * 1.5 - Math.abs(s.rule_503020.wants - 30) * 1.5)
        const savScore = Math.min(100, (s.savings_rate / 20) * 100)
        setScore(Math.round(budgetScore * 0.5 + savScore * 0.5))
      } else {
        setScore(0)
      }
    })
  }, [activeMonth])

  useEffect(() => {
    transactionsAPI.scoreHistory().then(r => setHistory(r.data)).catch(() => {})
    transactionsAPI.weekdayStats(3).then(r => setWeekday(r.data)).catch(() => {})
  }, [])

  const coaching = generateCoaching(history, stats)

  // Trend (Revenus vs Dépenses 6 mois)
  const trendMap: Record<string, Record<string, number>> = {}
  stats?.trend?.forEach(t => {
    const m = typeof t.month === 'string' ? t.month.slice(0, 7) : new Date(t.month).toISOString().slice(0, 7)
    if (!trendMap[m]) trendMap[m] = {}
    trendMap[m][t.type] = (trendMap[m][t.type] ?? 0) + parseFloat(String(t.total))
  })
  const incomeExpData = Object.entries(trendMap).slice(-6).map(([m, v]) => ({
    month: m.slice(5),
    Revenus: Math.round(v.income ?? 0),
    Dépenses: Math.round(v.expense ?? 0),
    Net: Math.round((v.income ?? 0) - (v.expense ?? 0) - (v.saving ?? 0)),
  }))

  const pieData = stats?.by_category?.slice(0, 6).map(c => ({
    name: c.category__name ?? 'Autre',
    value: Math.round(parseFloat(String(c.total))),
    color: c.category__color ?? '#6b6b7e',
    icon: c.category__icon ?? '',
  })) ?? []

  const historyScoreData = history.map(h => ({ ...h, month: h.month.slice(5) }))

  // Épargne cumulée
  let cumSavings = 0
  const cumulativeData = history.map(h => {
    const saved = h.income * (h.savings_rate / 100)
    cumSavings += saved
    return { month: h.month.slice(5), cumulé: Math.round(cumSavings), mensuel: Math.round(saved) }
  })

  // Heatmap jour de semaine — max for intensity scale
  const maxWeekday = Math.max(...weekday.map(d => d.avg), 1)

  const currentScore = history[history.length - 1]?.score ?? score
  const prevScore = history[history.length - 2]?.score ?? null
  const scoreDelta = prevScore !== null ? currentScore - prevScore : null

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Analytics</h1>
        <div className={styles.monthNav}>
          <button className={styles.monthBtn} onClick={() => setActiveMonth(m => shiftMonth(m, -1))}>‹</button>
          <span className={styles.month}>
            {new Date(activeMonth + '-15').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
          </span>
          <button
            className={styles.monthBtn}
            onClick={() => setActiveMonth(m => shiftMonth(m, +1))}
            disabled={activeMonth >= currentMonth}
          >›</button>
        </div>
      </div>

      {/* Score + Coaching */}
      <div className={styles.grid2}>
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Score financier</h2>
          <div className={styles.scoreCenter}>
            <ScoreGauge score={score} size={130} />
            <div className={styles.scoreInfo}>
              {scoreDelta !== null && (
                <div className={styles.scoreDelta} style={{ color: scoreDelta >= 0 ? '#34d399' : '#f87171' }}>
                  {scoreDelta >= 0 ? '▲' : '▼'} {Math.abs(scoreDelta)} pts vs mois dernier
                </div>
              )}
              <div className={styles.scoreBreakdown}>
                <div>Budget <span style={{ color: scoreColor(Math.max(0, 100 - Math.abs((stats?.rule_503020.needs ?? 50) - 50) * 1.5)) }}>
                  {Math.max(0, 100 - Math.abs((stats?.rule_503020.needs ?? 50) - 50) * 1.5).toFixed(0)}/100
                </span></div>
                <div>Épargne <span style={{ color: scoreColor(Math.min(100, (stats?.savings_rate ?? 0) / 20 * 100)) }}>
                  {Math.min(100, Math.round((stats?.savings_rate ?? 0) / 20 * 100))}/100
                </span></div>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Coaching</h2>
          {coaching.length > 0
            ? <div className={styles.coachList}>
                {coaching.map((m, i) => <div key={i} className={styles.coachMsg}>{m}</div>)}
              </div>
            : <div className={styles.empty}>Pas assez de données ce mois</div>
          }
        </section>
      </div>

      {/* Score 6 mois */}
      {historyScoreData.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Évolution du score (6 mois)</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={historyScoreData} barSize={28}>
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip content={ChartTooltip} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]} name="Score">
                {historyScoreData.map((e, i) => <Cell key={i} fill={scoreColor(e.score)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Revenus vs Dépenses + Net */}
      {incomeExpData.length > 0 && (
        <div className={styles.grid2}>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Revenus vs Dépenses (6 mois)</h2>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={incomeExpData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={44} />
                <Tooltip content={ChartTooltip} />
                <Line type="monotone" dataKey="Revenus" stroke="#34d399" strokeWidth={2} dot={{ r: 3, fill: '#34d399' }} />
                <Line type="monotone" dataKey="Dépenses" stroke="#f87171" strokeWidth={2} dot={{ r: 3, fill: '#f87171' }} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Solde net mensuel</h2>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={incomeExpData}>
                <defs>
                  <linearGradient id="netGradPos" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="netGradNeg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={44} />
                <Tooltip content={ChartTooltip} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 2" />
                <Area
                  type="monotone" dataKey="Net" name="Net"
                  stroke="#00D4AA" strokeWidth={2}
                  fill="url(#netGradPos)"
                  dot={(props: any) => {
                    const { cx, cy, payload } = props
                    return <circle key={cx} cx={cx} cy={cy} r={3} fill={payload.Net >= 0 ? '#34d399' : '#f87171'} />
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </section>
        </div>
      )}

      {/* Taux épargne + Épargne cumulée */}
      <div className={styles.grid2}>
        {historyScoreData.length > 0 && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Taux d'épargne mensuel</h2>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={historyScoreData} barSize={28}>
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" width={36} />
                <Tooltip content={ChartTooltip} />
                <ReferenceLine y={20} stroke="rgba(0,212,170,0.35)" strokeDasharray="4 2" label={{ value: 'Cible 20%', fill: '#00D4AA', fontSize: 10, position: 'insideTopRight' }} />
                <Bar dataKey="savings_rate" radius={[4, 4, 0, 0]} name="Épargne" unit="%">
                  {historyScoreData.map((e, i) => (
                    <Cell key={i} fill={e.savings_rate >= 20 ? '#34d399' : e.savings_rate >= 10 ? '#fbbf24' : '#f87171'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </section>
        )}

        {cumulativeData.length > 0 && cumulativeData.some(d => d.cumulé > 0) && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Épargne cumulée (6 mois)</h2>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={cumulativeData}>
                <defs>
                  <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={50} tickFormatter={v => `${v}€`} />
                <Tooltip content={ChartTooltip} />
                <Area type="monotone" dataKey="cumulé" name="Cumulé" stroke="#60a5fa" strokeWidth={2} fill="url(#cumGrad)" dot={{ r: 3, fill: '#60a5fa' }} />
                <Bar dataKey="mensuel" name="Mensuel" fill="#a78bfa" fillOpacity={0.5} radius={[2, 2, 0, 0]} />
              </AreaChart>
            </ResponsiveContainer>
          </section>
        )}
      </div>

      {/* Heatmap jour de semaine */}
      {weekday.length > 0 && weekday.some(d => d.count > 0) && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Dépenses par jour de la semaine <span className={styles.sectionSub}>(3 derniers mois)</span></h2>
          <div className={styles.heatmapRow}>
            {weekday.map((d, i) => {
              const intensity = d.avg / maxWeekday
              const isWeekend = i >= 5
              return (
                <div key={d.day} className={styles.heatCell}>
                  <div
                    className={styles.heatBar}
                    style={{
                      height: `${Math.max(8, intensity * 80)}px`,
                      background: isWeekend
                        ? `rgba(167,139,250,${0.2 + intensity * 0.8})`
                        : `rgba(0,212,170,${0.2 + intensity * 0.8})`,
                    }}
                  />
                  <div className={styles.heatLabel}>{d.day}</div>
                  <div className={styles.heatAvg} style={{ color: isWeekend ? '#a78bfa' : '#00d4aa' }}>
                    {d.avg > 0 ? `${d.avg.toFixed(0)} €` : '—'}
                  </div>
                  <div className={styles.heatCount}>{d.count} txn</div>
                </div>
              )
            })}
          </div>
          <div className={styles.heatLegend}>
            <span style={{ color: '#00d4aa' }}>● Semaine</span>
            <span style={{ color: '#a78bfa' }}>● Week-end</span>
            <span style={{ color: '#64748b' }}>Montant moyen par transaction</span>
          </div>
        </section>
      )}

      {/* Dépenses par catégorie */}
      {pieData.length > 0 && (
        <div className={styles.grid2}>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Dépenses par catégorie</h2>
            <ResponsiveContainer width="100%" height={pieData.length * 42}>
              <BarChart data={pieData} layout="vertical" barSize={14} margin={{ left: 8, right: 16 }}>
                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#e2e8f0', fontSize: 12 }} axisLine={false} tickLine={false} width={100} />
                <Tooltip content={ChartTooltip} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} name="Montant">
                  {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </section>

          {/* Top dépenses */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Top dépenses ce mois</h2>
            <div className={styles.topList}>
              {pieData.map((c, i) => {
                const pct = stats?.income ? (c.value / stats.income * 100) : 0
                return (
                  <div key={i} className={styles.topRow}>
                    <span className={styles.topRank}>{i + 1}</span>
                    <span className={styles.topName}>{c.icon} {c.name}</span>
                    <div className={styles.topBar}>
                      <div className={styles.topBarFill} style={{ width: `${Math.min(100, pct * 1.5)}%`, background: c.color }} />
                    </div>
                    <span className={styles.topAmt}>{c.value} €</span>
                    <span className={styles.topPct} style={{ color: c.color }}>{pct.toFixed(1)}%</span>
                  </div>
                )
              })}
            </div>
          </section>
        </div>
      )}

      {/* Bilan annuel */}
      {history.length > 0 && (() => {
        const yearData = history.filter(h => h.month.startsWith(activeYear))
        if (yearData.length === 0) return null
        const totalIncome   = yearData.reduce((s, h) => s + h.income, 0)
        const totalExpenses = yearData.reduce((s, h) => s + h.expenses, 0)
        const totalSavings  = yearData.reduce((s, h) => s + h.income * (h.savings_rate / 100), 0)
        const avgRate       = yearData.reduce((s, h) => s + h.savings_rate, 0) / yearData.length
        const balance       = totalIncome - totalExpenses - totalSavings
        const fmt = (v: number) => v.toLocaleString('fr-FR', { maximumFractionDigits: 0 }) + ' €'
        const annualBarData = yearData.map(h => ({
          month: h.month.slice(5),
          Revenus:  Math.round(h.income),
          Dépenses: Math.round(h.expenses),
          Épargne:  Math.round(h.income * (h.savings_rate / 100)),
        }))
        return (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Bilan {activeYear}</h2>
            <div className={styles.annualKpis}>
              <div className={styles.annualKpi}><span className={styles.annualVal} style={{ color: 'var(--accent-green)' }}>{fmt(totalIncome)}</span><span className={styles.annualLabel}>Revenus totaux</span></div>
              <div className={styles.annualKpi}><span className={styles.annualVal} style={{ color: 'var(--accent-red)' }}>{fmt(totalExpenses)}</span><span className={styles.annualLabel}>Dépenses totales</span></div>
              <div className={styles.annualKpi}><span className={styles.annualVal} style={{ color: 'var(--accent-blue)' }}>{fmt(totalSavings)}</span><span className={styles.annualLabel}>Épargne totale</span></div>
              <div className={styles.annualKpi}><span className={styles.annualVal} style={{ color: avgRate >= 20 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>{avgRate.toFixed(1)}%</span><span className={styles.annualLabel}>Taux moyen</span></div>
              <div className={styles.annualKpi}><span className={styles.annualVal} style={{ color: balance >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{balance >= 0 ? '+' : ''}{fmt(balance)}</span><span className={styles.annualLabel}>Solde net</span></div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={annualBarData} barSize={12} margin={{ top: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
                <Tooltip content={ChartTooltip} />
                <Bar dataKey="Revenus"  fill="#34d399" radius={[3,3,0,0]} />
                <Bar dataKey="Dépenses" fill="#f87171" radius={[3,3,0,0]} />
                <Bar dataKey="Épargne"  fill="#60a5fa" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </section>
        )
      })()}
    </div>
  )
}
