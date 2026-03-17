import { useEffect, useState } from 'react'
import { LayoutGrid, TrendingUp, RefreshCw, Folder } from 'lucide-react'
import { transactionsAPI, savingsAPI, categoriesAPI, forecastAPI } from '../../services/api'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import ForecastChart from '../../components/ForecastChart'
import type { TransactionStats, CompensationResult, Category } from '../../types'
import styles from './Budget.module.css'

function SectionTitle({ icon: Icon, label }: { icon: any; label: string }) {
  return (
    <div className={styles.sectionHeader}>
      <Icon size={13} strokeWidth={2} className={styles.sectionIcon} />
      <h2 className={styles.sectionTitle}>{label}</h2>
    </div>
  )
}

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

function SegmentedBudgetBar({ needs, wants, savings, income }: { needs: number, wants: number, savings: number, income: number }) {
  if (income <= 0) return null
  const needsPct  = Math.min(100, (needs  / income) * 100)
  const wantsPct  = Math.min(100 - needsPct, (wants  / income) * 100)
  const savingsPct = Math.min(100 - needsPct - wantsPct, (savings / income) * 100)
  const unallocated = Math.max(0, 100 - needsPct - wantsPct - savingsPct)
  return (
    <div style={{ display: 'flex', height: 10, borderRadius: 6, overflow: 'hidden', gap: 2, margin: '1rem 0' }}>
      <div style={{ width: `${needsPct}%`, background: '#60A5FA', borderRadius: 4 }} title={`Besoins ${needsPct.toFixed(1)}%`} />
      <div style={{ width: `${wantsPct}%`, background: '#A78BFA', borderRadius: 4 }} title={`Envies ${wantsPct.toFixed(1)}%`} />
      <div style={{ width: `${savingsPct}%`, background: '#34D399', borderRadius: 4 }} title={`Épargne ${savingsPct.toFixed(1)}%`} />
      {unallocated > 0.5 && <div style={{ width: `${unallocated}%`, background: 'rgba(255,255,255,0.08)', borderRadius: 4 }} title={`Non alloué ${unallocated.toFixed(1)}%`} />}
    </div>
  )
}

export default function Budget() {
  const [stats, setStats] = useState<TransactionStats | null>(null)
  const [comp, setComp] = useState<CompensationResult | null>(null)
  const [cats, setCats] = useState<Category[]>([])
  const [forecast, setForecast] = useState<any>(null)

  useEffect(() => {
    transactionsAPI.stats({ month: currentMonth }).then(r => setStats(r.data))
    savingsAPI.compensation({ month: currentMonth }).then(r => setComp(r.data)).catch(() => {})
    categoriesAPI.list().then(r => setCats(r.data.results ?? r.data))
    forecastAPI.budget(6).then(r => setForecast(r.data)).catch(() => {})
  }, [])

  const catMap = Object.fromEntries(stats?.by_category?.map(c => [c.category__id, c]) ?? [])

  // Aggregate projected buckets for the segmented bar (use first forecast month)
  const firstForecast = forecast?.months?.[0]

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

      {/* Segmented budget bar (current month) */}
      {stats && (
        <section className={styles.section}>
          <SectionTitle icon={LayoutGrid} label="Répartition du mois" />
          <SegmentedBudgetBar
            needs={(stats.rule_503020?.needs ?? 0) / 100 * (stats.income ?? 0)}
            wants={(stats.rule_503020?.wants ?? 0) / 100 * (stats.income ?? 0)}
            savings={stats.savings ?? 0}
            income={stats.income ?? 0}
          />
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span><span style={{ color: '#60A5FA' }}>■</span> Besoins</span>
            <span><span style={{ color: '#A78BFA' }}>■</span> Envies</span>
            <span><span style={{ color: '#34D399' }}>■</span> Épargne</span>
            <span><span style={{ color: 'rgba(255,255,255,0.2)' }}>■</span> Non alloué</span>
          </div>
        </section>
      )}

      {/* Forecast chart */}
      {forecast && forecast.history?.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={TrendingUp} label="Projection 6 mois" />
          {forecast.worst_forecast_alert && forecast.worst_forecast_alert !== 'green' && (
            <div style={{
              padding: '0.5rem 0.75rem',
              borderRadius: 6,
              marginBottom: '0.75rem',
              fontSize: '0.8rem',
              background: forecast.worst_forecast_alert === 'red' || forecast.worst_forecast_alert === 'critical'
                ? 'rgba(239,68,68,0.12)' : 'rgba(251,146,60,0.12)',
              color: forecast.worst_forecast_alert === 'red' || forecast.worst_forecast_alert === 'critical'
                ? 'var(--accent-red)' : 'var(--accent-orange)',
              border: `1px solid ${forecast.worst_forecast_alert === 'red' || forecast.worst_forecast_alert === 'critical'
                ? 'rgba(239,68,68,0.25)' : 'rgba(251,146,60,0.25)'}`,
            }}>
              Alerte prévisionnelle : {forecast.worst_forecast_alert}
              {forecast.residual_surplus < 0 && ` — Surplus résiduel : ${forecast.residual_surplus.toFixed(0)} €`}
            </div>
          )}
          <ForecastChart
            history={forecast.history}
            forecast={forecast.months}
            height={240}
          />
          {firstForecast && (
            <div style={{ marginTop: '0.75rem' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Projection mois prochain — confiance {(firstForecast.confidence * 100).toFixed(0)}%
              </p>
              <SegmentedBudgetBar
                needs={firstForecast.needs}
                wants={firstForecast.wants}
                savings={firstForecast.savings}
                income={firstForecast.income}
              />
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <span><span style={{ color: '#60A5FA' }}>■</span> Besoins {firstForecast.needs_pct}%</span>
                <span><span style={{ color: '#A78BFA' }}>■</span> Envies {firstForecast.wants_pct}%</span>
                <span><span style={{ color: '#34D399' }}>■</span> Épargne {firstForecast.savings_pct}%</span>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Compensation plan */}
      {comp && (
        <section className={styles.section}>
          <SectionTitle icon={RefreshCw} label="Plan de compensation" />
          <CompensationPlanCard data={comp} />
        </section>
      )}

      {/* Category cards */}
      <section className={styles.section}>
        <SectionTitle icon={Folder} label="Par catégorie" />
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
