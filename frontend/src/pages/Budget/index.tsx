import { useEffect, useState } from 'react'
import { LayoutGrid, TrendingUp, RefreshCw, Folder, FlaskConical, Star, Mail } from 'lucide-react'
import { transactionsAPI, savingsAPI, categoriesAPI, forecastAPI, envelopesAPI } from '../../services/api'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import ForecastChart from '../../components/ForecastChart'
import Modal from '../../components/Modal/Modal'
import type { TransactionStats, CompensationResult, Category, SimulationResult, WantsData, Envelope } from '../../types'
import styles from './Budget.module.css'

const RISK_COLORS = { low: 'var(--accent-green)', medium: 'var(--accent-orange)', high: 'var(--accent-red)' }
const RISK_LABELS = { low: '🟢 Faible', medium: '🟡 Modéré', high: '🔴 Élevé' }

function SectionTitle({ icon: Icon, label, right }: { icon: any; label: string; right?: React.ReactNode }) {
  return (
    <div className={styles.sectionHeader}>
      <Icon size={13} strokeWidth={2} className={styles.sectionIcon} />
      <h2 className={styles.sectionTitle}>{label}</h2>
      {right && <div style={{ marginLeft: 'auto' }}>{right}</div>}
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
  const [showSim, setShowSim] = useState(false)
  const [simReductions, setSimReductions] = useState<Record<string, number>>({})
  const [simExtraSavings, setSimExtraSavings] = useState(0)
  const [simResult, setSimResult] = useState<SimulationResult | null>(null)
  const [simLoading, setSimLoading] = useState(false)
  const [wantsData, setWantsData] = useState<WantsData | null>(null)
  const [editingScores, setEditingScores] = useState<Record<string, number>>({})
  const [scoresSaving, setScoresSaving] = useState(false)

  // Envelopes state
  const [envelopes, setEnvelopes] = useState<Envelope[]>([])
  // Quick-add/subtract expense on envelope
  const [addingExpCatId, setAddingExpCatId] = useState<number | null>(null)
  const [addingExpAmount, setAddingExpAmount] = useState('')
  const [addingExpLabel, setAddingExpLabel] = useState('')
  const [addingExpSign, setAddingExpSign] = useState<1 | -1>(1)
  const [showAddEnv, setShowAddEnv] = useState(false)
  const [newEnvCat, setNewEnvCat] = useState<number | ''>('')
  const [newEnvAmount, setNewEnvAmount] = useState('')

  const loadEnvelopes = () =>
    envelopesAPI.list(currentMonth).then(r => setEnvelopes(r.data.results ?? r.data)).catch(() => {})

  useEffect(() => {
    transactionsAPI.stats({ month: currentMonth }).then(r => setStats(r.data))
    savingsAPI.compensation({ month: currentMonth }).then(r => setComp(r.data)).catch(() => {})
    categoriesAPI.list().then(r => setCats(r.data.results ?? r.data))
    forecastAPI.budget(6).then(r => setForecast(r.data)).catch(() => {})
    forecastAPI.wants().then(r => {
      setWantsData(r.data)
      const scores: Record<string, number> = {}
      r.data.envelopes.forEach((e: any) => { scores[String(e.category_id)] = e.score })
      setEditingScores(scores)
    }).catch(() => {})
    loadEnvelopes()
  }, [])

  const saveWantsScores = async () => {
    setScoresSaving(true)
    try {
      const { data } = await forecastAPI.updateWantsScores(editingScores)
      setWantsData(data)
    } finally {
      setScoresSaving(false)
    }
  }

  const runSimulation = async () => {
    setSimLoading(true)
    try {
      const { data } = await forecastAPI.simulate({ reductions: simReductions, extra_savings: simExtraSavings })
      setSimResult(data)
    } finally {
      setSimLoading(false)
    }
  }

  const saveEnvelope = async (categoryId: number, amount: number) => {
    const { data } = await envelopesAPI.upsert(categoryId, currentMonth, amount)
    setEnvelopes(prev => {
      const idx = prev.findIndex(e => Number(e.category) === categoryId)
      if (idx >= 0) { const next = [...prev]; next[idx] = data; return next }
      return [...prev, data].sort((a, b) =>
        (a.category_detail?.name ?? '').localeCompare(b.category_detail?.name ?? '')
      )
    })
  }

  const addExpense = async (categoryId: number) => {
    const amount = parseFloat(addingExpAmount)
    if (!amount || amount <= 0) { setAddingExpCatId(null); return }
    const today = new Date().toISOString().slice(0, 10)
    await transactionsAPI.create({
      label: addingExpLabel || (addingExpSign === 1 ? 'Dépense manuelle' : 'Remboursement'),
      amount: amount * addingExpSign,
      date: today,
      type: 'expense',
      category: categoryId,
    })
    setAddingExpCatId(null)
    setAddingExpAmount('')
    setAddingExpLabel('')
    setAddingExpSign(1)
    loadEnvelopes()
    transactionsAPI.stats({ month: currentMonth }).then(r => setStats(r.data))
  }

  const addEnvelope = async () => {
    if (!newEnvCat || !newEnvAmount) return
    await saveEnvelope(Number(newEnvCat), parseFloat(newEnvAmount))
    setShowAddEnv(false)
    setNewEnvCat('')
    setNewEnvAmount('')
  }

  const budgetedCatIds = new Set(envelopes.map(e => Number(e.category)))
  const unbugdetedCats = cats.filter(c => c.type === 'expense' && !budgetedCatIds.has(c.id))
  const catMap = Object.fromEntries(stats?.by_category?.map(c => [c.category__id, c]) ?? [])
  const firstForecast = forecast?.months?.[0]

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Budget — Règle 50/30/20</h1>
        <button className={styles.btnSim} onClick={() => { setShowSim(true); setSimResult(null); setSimReductions({}); setSimExtraSavings(0) }}>
          <FlaskConical size={14} /> Simuler
        </button>
      </div>

      {/* Buckets overview */}
      <div className={styles.bucketsGrid}>
        {[
          { key: 'needs', label: 'Besoins', target: 50, color: 'var(--accent-blue)', icon: '🏠' },
          { key: 'wants', label: 'Envies', target: 30, color: 'var(--accent-purple)', icon: '🎬' },
          { key: 'savings', label: 'Épargne', target: 20, color: 'var(--accent-green)', icon: '🏦' },
        ].map(b => {
          const real = stats?.rule_503020[b.key as keyof typeof stats.rule_503020] ?? 0
          const gap = real - b.target
          const euros = Math.round((real / 100) * (stats?.income ?? 0))
          return (
            <div key={b.key} className={styles.bucketCard} style={{ '--bc': b.color } as React.CSSProperties}>
              <div className={styles.bucketHeader}>
                <span className={styles.bucketIcon}>{b.icon}</span>
                <span className={styles.bucketLabel}>{b.label}</span>
                <span className={styles.bucketTarget}>{b.target}%</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                <div className={styles.bucketReal} style={{ color: b.color }}>{real.toFixed(1)}%</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{euros.toLocaleString('fr-FR')} €</div>
              </div>
              <ProgressBar value={real} max={100} color={b.color} />
              <div className={styles.bucketGap} style={{ color: Math.abs(gap) <= 5 ? 'var(--accent-green)' : gap > 0 ? 'var(--accent-red)' : 'var(--accent-orange)' }}>
                {gap > 0 ? '+' : ''}{gap.toFixed(1)}% vs cible
              </div>
            </div>
          )
        })}
      </div>

      {/* Segmented budget bar */}
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

      {/* ── ENVELOPPES ── */}
      <section className={styles.section}>
        <SectionTitle
          icon={Mail}
          label={`Enveloppes — ${currentMonth.replace('-', ' / ')}`}
          right={
            unbugdetedCats.length > 0 && (
              <button className={styles.btnEnvAdd} onClick={() => setShowAddEnv(true)}>
                + Enveloppe
              </button>
            )
          }
        />

        {envelopes.length === 0 ? (
          <div className={styles.envEmpty}>
            Aucune enveloppe configurée pour ce mois.
            {unbugdetedCats.length > 0 && (
              <button onClick={() => setShowAddEnv(true)}>Configurer maintenant →</button>
            )}
          </div>
        ) : (
          <div className={styles.envGrid}>
            {envelopes.map(e => {
              const allocated = Math.round(parseFloat(String(e.allocated)))
              const spent = Math.round(parseFloat(String(e.spent)))
              const remaining = allocated - spent
              const rawPct = allocated > 0 ? (spent / allocated) * 100 : 0
              const pct = Math.min(100, rawPct)
              const cat = e.category_detail
              if (!cat) return null
              const overBudget = rawPct > 100
              const nearLimit = rawPct >= 75 && rawPct <= 100
              const barColor = overBudget ? 'var(--accent-red)' : nearLimit ? 'var(--accent-orange)' : 'var(--accent-green)'
              const spentColor = overBudget ? 'var(--accent-red)' : 'var(--text-muted)'
              return (
                <div key={e.id} className={styles.envCard}>
                  <div className={styles.envHeader}>
                    <span style={{ color: cat.color }}>{cat.icon} {cat.name}</span>
                    <span className={styles.catBucket} style={{ background: `${cat.color}22`, color: cat.color }}>{cat.rule_bucket}</span>
                  </div>

                  <ProgressBar value={pct} color={barColor} />

                  {addingExpCatId === e.category ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.5rem' }}>
                      <button
                        onClick={() => setAddingExpSign(s => s === 1 ? -1 : 1)}
                        title={addingExpSign === 1 ? 'Dépense — cliquer pour remboursement' : 'Remboursement — cliquer pour dépense'}
                        style={{
                          width: 28, height: 28, borderRadius: '50%', border: 'none', cursor: 'pointer',
                          fontWeight: 900, fontSize: '1rem', lineHeight: 1,
                          background: addingExpSign === 1 ? 'var(--accent-red)' : 'var(--accent-green)',
                          color: '#fff', flexShrink: 0,
                        }}
                      >{addingExpSign === 1 ? '+' : '−'}</button>
                      <input
                        type="number" autoFocus placeholder="0" className={styles.envInput}
                        value={addingExpAmount}
                        onChange={ev => setAddingExpAmount(ev.target.value)}
                        onKeyDown={ev => { if (ev.key === 'Enter') addExpense(Number(e.category)); if (ev.key === 'Escape') setAddingExpCatId(null) }}
                        style={{ width: 70, textAlign: 'right' }}
                      />
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>€</span>
                      <button onClick={() => addExpense(Number(e.category))} style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontWeight: 700, fontSize: '0.8rem' }}>✓</button>
                      <button onClick={() => { setAddingExpCatId(null); setAddingExpAmount('') }} style={{ background: 'transparent', color: 'var(--text-muted)', border: 'none', cursor: 'pointer', fontSize: '0.85rem' }}>✕</button>
                    </div>
                  ) : (
                    <div className={styles.envFooter}>
                      <span
                        style={{ color: spentColor, fontSize: '0.75rem', cursor: 'pointer', borderBottom: '1px dashed currentColor' }}
                        onClick={() => { setAddingExpCatId(Number(e.category)); setAddingExpAmount(''); setAddingExpLabel('') }}
                        title="Ajouter une dépense"
                      >
                        {spent.toFixed(0)} € / {allocated.toFixed(0)} €
                      </span>
                      <span style={{ color: barColor, fontWeight: 700, fontSize: '0.8rem' }}>
                        {overBudget ? `−${Math.abs(remaining).toFixed(0)} € dépassé` : `+${remaining.toFixed(0)} € restant`}
                      </span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {envelopes.length > 0 && (() => {
          const totalSpent = envelopes.reduce((s, e) => s + Math.round(parseFloat(String(e.spent))), 0)
          const totalAllocated = envelopes.reduce((s, e) => s + Math.round(parseFloat(String(e.allocated))), 0)
          const totalRemaining = totalAllocated - totalSpent
          const totalColor = totalRemaining < 0 ? 'var(--accent-red)' : totalRemaining === 0 ? 'var(--accent-orange)' : 'var(--accent-green)'
          return (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', padding: '0.6rem 1rem', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL ENVELOPPES</span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {totalSpent} € / {totalAllocated} €
              </span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: totalColor }}>
                {totalRemaining < 0 ? `−${Math.abs(totalRemaining)}` : `+${totalRemaining}`} € restant
              </span>
            </div>
          )
        })()}
      </section>

      {/* Forecast chart */}
      {forecast && forecast.history?.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={TrendingUp} label="Projection 6 mois" />
          {forecast.worst_forecast_alert && forecast.worst_forecast_alert !== 'green' && (
            <div style={{
              padding: '0.5rem 0.75rem', borderRadius: 6, marginBottom: '0.75rem', fontSize: '0.8rem',
              background: forecast.worst_forecast_alert === 'red' || forecast.worst_forecast_alert === 'critical' ? 'rgba(239,68,68,0.12)' : 'rgba(251,146,60,0.12)',
              color: forecast.worst_forecast_alert === 'red' || forecast.worst_forecast_alert === 'critical' ? 'var(--accent-red)' : 'var(--accent-orange)',
              border: `1px solid ${forecast.worst_forecast_alert === 'red' || forecast.worst_forecast_alert === 'critical' ? 'rgba(239,68,68,0.25)' : 'rgba(251,146,60,0.25)'}`,
            }}>
              Alerte prévisionnelle : {forecast.worst_forecast_alert}
              {forecast.residual_surplus < 0 && ` — Surplus résiduel : ${forecast.residual_surplus.toFixed(0)} €`}
            </div>
          )}
          <ForecastChart history={forecast.history} forecast={forecast.months} height={240} />
          {firstForecast && (
            <div style={{ marginTop: '0.75rem' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Projection mois prochain — confiance {(firstForecast.confidence * 100).toFixed(0)}%
              </p>
              <SegmentedBudgetBar needs={firstForecast.needs} wants={firstForecast.wants} savings={firstForecast.savings} income={firstForecast.income} />
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

      {/* Wants envelopes (legacy priority scores) */}
      {wantsData && wantsData.envelopes.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={Star} label={`Priorités Envies — budget ${wantsData.wants_budget.toFixed(0)} €`} />
          <div className={styles.catGrid}>
            {wantsData.envelopes.map(e => {
              const statusColor = e.status === 'green' ? 'var(--accent-green)' : e.status === 'yellow' ? 'var(--accent-orange)' : 'var(--accent-red)'
              return (
                <div key={e.category_id} className={styles.catCard}>
                  <div className={styles.catHeader}>
                    <span>{e.label}</span>
                    <span className={styles.catBucket} style={{ background: `${statusColor}22`, color: statusColor }}>
                      {e.spent.toFixed(0)} / {e.envelope.toFixed(0)} €
                    </span>
                  </div>
                  <ProgressBar value={e.spent} max={e.envelope} color={statusColor} showLabel />
                  <div className={styles.catAmounts} style={{ marginTop: '0.5rem', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Priorité</span>
                    <div style={{ display: 'flex', gap: 3 }}>
                      {[1,2,3,4,5].map(s => (
                        <button key={s} onClick={() => setEditingScores(p => ({ ...p, [String(e.category_id)]: s }))}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 1,
                            color: (editingScores[String(e.category_id)] ?? e.score) >= s ? 'var(--accent-orange)' : 'var(--text-muted)',
                            fontSize: '0.9rem' }}>★</button>
                      ))}
                    </div>
                  </div>
                  {(e as any).coaching && (
                    <div style={{
                      marginTop: '0.5rem', fontSize: '0.72rem', color: 'var(--accent-orange)',
                      background: 'rgba(251,146,60,0.08)', border: '1px solid rgba(251,146,60,0.2)',
                      borderRadius: 6, padding: '0.375rem 0.625rem', lineHeight: 1.4,
                    }}>
                      💡 {(e as any).coaching}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <button className={styles.btnSim} onClick={saveWantsScores} disabled={scoresSaving} style={{ marginTop: '0.75rem' }}>
            {scoresSaving ? 'Sauvegarde...' : '💾 Sauvegarder les priorités'}
          </button>
        </section>
      )}

      {/* Category cards (budget_limit based) */}
      {cats.some(c => c.type === 'expense' && c.budget_limit) && (
        <section className={styles.section}>
          <SectionTitle icon={Folder} label="Limites par catégorie" />
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
      )}

      {/* What-If simulation modal */}
      <Modal open={showSim} onClose={() => setShowSim(false)} title="💡 Simulation What-If" width={640}>
        <div className={styles.simBody}>
          <p className={styles.simDesc}>Ajustez vos dépenses et voyez l'impact en temps réel sur votre budget.</p>
          <div className={styles.simSection}>
            <div className={styles.simSectionTitle}>Réduire les dépenses par catégorie</div>
            {simResult?.before.by_category.slice(0, 8).map(cat => (
              <div key={cat.id} className={styles.simRow}>
                <span className={styles.simCatLabel}>
                  <span style={{ color: cat.color }}>{cat.icon}</span> {cat.name}
                  <span className={styles.simCatCurrent}>{cat.total.toFixed(0)} €</span>
                </span>
                <div className={styles.simInputRow}>
                  <input type="range" min={0} max={Math.round(cat.total)} step={5}
                    value={simReductions[cat.id] ?? 0}
                    onChange={e => setSimReductions(p => ({ ...p, [cat.id]: +e.target.value }))}
                    className={styles.simRange} />
                  <span className={styles.simReductionVal}>-{simReductions[cat.id] ?? 0} €</span>
                </div>
              </div>
            ))}
            {!simResult && <p className={styles.simHint}>Lancez la simulation pour accéder aux sliders</p>}
          </div>
          <div className={styles.simSection}>
            <div className={styles.simSectionTitle}>Épargne supplémentaire</div>
            <div className={styles.simRow}>
              <span className={styles.simCatLabel}>🏦 Épargner en plus</span>
              <div className={styles.simInputRow}>
                <input type="number" min={0} step={10} value={simExtraSavings}
                  onChange={e => setSimExtraSavings(+e.target.value)}
                  className={styles.simInput} placeholder="0 €" />
              </div>
            </div>
          </div>
          <button className={styles.btnSimRun} onClick={runSimulation} disabled={simLoading}>
            {simLoading ? 'Calcul...' : '▶ Lancer la simulation'}
          </button>
          {simResult && (
            <div className={styles.simResults}>
              <div className={styles.simCompare}>
                <div className={styles.simCard}>
                  <div className={styles.simCardTitle}>Situation actuelle</div>
                  <div className={styles.simStat}>Dépenses <strong>{simResult.before.expenses.toFixed(0)} €</strong></div>
                  <div className={styles.simStat}>Épargne <strong>{simResult.before.savings.toFixed(0)} €</strong></div>
                  <div className={styles.simStat}>Balance <strong>{simResult.before.balance.toFixed(0)} €</strong></div>
                  <div className={styles.simStat}>Taux épargne <strong>{simResult.impact.savings_rate_before}%</strong></div>
                  <div className={styles.simStat}>Risque <strong style={{ color: RISK_COLORS[simResult.before.risk] }}>{RISK_LABELS[simResult.before.risk]}</strong></div>
                </div>
                <div className={styles.simCard} style={{ borderColor: 'var(--accent)' }}>
                  <div className={styles.simCardTitle} style={{ color: 'var(--accent)' }}>Après simulation</div>
                  <div className={styles.simStat}>Dépenses <strong>{simResult.after.expenses.toFixed(0)} €</strong></div>
                  <div className={styles.simStat}>Épargne <strong>{simResult.after.savings.toFixed(0)} €</strong></div>
                  <div className={styles.simStat}>Balance <strong style={{ color: simResult.after.balance >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{simResult.after.balance.toFixed(0)} €</strong></div>
                  <div className={styles.simStat}>Taux épargne <strong style={{ color: simResult.impact.savings_rate_after >= 20 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>{simResult.impact.savings_rate_after}%</strong></div>
                  <div className={styles.simStat}>Risque <strong style={{ color: RISK_COLORS[simResult.after.risk] }}>{RISK_LABELS[simResult.after.risk]}</strong></div>
                </div>
              </div>
              <div className={styles.simImpact}>
                <span>💰 Économies : <strong style={{ color: 'var(--accent-green)' }}>+{simResult.impact.expense_reduction.toFixed(0)} €</strong></span>
                <span>📈 Épargne gain : <strong style={{ color: 'var(--accent-green)' }}>+{simResult.impact.savings_gain.toFixed(0)} €</strong></span>
                <span>🎯 Risque : <strong>{simResult.impact.risk_change}</strong></span>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Add envelope modal */}
      <Modal open={showAddEnv} onClose={() => setShowAddEnv(false)} title="Nouvelle enveloppe">
        <div className={styles.simBody}>
          <div className={styles.simSection}>
            <div className={styles.simSectionTitle}>Catégorie</div>
            <select value={newEnvCat} onChange={e => setNewEnvCat(e.target.value === '' ? '' : Number(e.target.value))}
              className={styles.simInput} style={{ width: '100%' }}>
              <option value="">— Choisir une catégorie —</option>
              {unbugdetedCats.map(c => (
                <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
              ))}
            </select>
          </div>
          <div className={styles.simSection}>
            <div className={styles.simSectionTitle}>Montant alloué (€)</div>
            <input type="number" min={0} step={5} value={newEnvAmount}
              onChange={e => setNewEnvAmount(e.target.value)}
              className={styles.simInput} style={{ width: '100%' }} placeholder="ex: 50" />
          </div>
          <button className={styles.btnSimRun} onClick={addEnvelope} disabled={!newEnvCat || !newEnvAmount}>
            Créer l'enveloppe
          </button>
        </div>
      </Modal>
    </div>
  )
}
