import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  PieChart as PieChartIcon, BarChart2, TrendingUp,
  Landmark, Lightbulb, Scale, CandlestickChart, RefreshCw, FileDown, Building2
} from 'lucide-react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { transactionsAPI, savingsAPI, goalsAPI, documentsAPI, accountsAPI, categoriesAPI } from '../../services/api'
import KPICard from '../../components/KPICard/KPICard'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import AlertBanner from '../../components/AlertBanner/AlertBanner'
import TransactionRow from '../../components/TransactionRow/TransactionRow'
import { Skeleton, SkeletonList } from '../../components/Skeleton/Skeleton'
import type { TransactionStats, CompensationResult, SavingsSummary, Insight, Transaction, CashFlowMonth, RecurringPattern, BankAccount } from '../../types'
import styles from './Dashboard.module.css'

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#1e2235', border: '1px solid #3a3f5c', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      {label && <div style={{ color: '#f1f5f9', fontWeight: 600, marginBottom: 4 }}>{label}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: '#cbd5e1' }}>
          <span style={{ color: p.color ?? '#f1f5f9' }}>■</span>{' '}
          {p.name} : {typeof p.value === 'number' ? p.value.toFixed(0) : p.value} €
        </div>
      ))}
    </div>
  )
}

function PieTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div style={{ background: '#1e2235', border: '1px solid #3a3f5c', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{p.name}</span>
      <span style={{ color: '#cbd5e1' }}> : {Number(p.value).toFixed(0)} €</span>
    </div>
  )
}

const RISK_CONFIG = {
  low:    { label: 'Risque faible',  color: 'var(--accent-green)',  bg: 'rgba(52,211,153,0.12)'  },
  medium: { label: 'Risque modéré', color: 'var(--accent-orange)', bg: 'rgba(251,146,60,0.12)'  },
  high:   { label: 'Risque élevé',   color: 'var(--accent-red)',    bg: 'rgba(248,113,113,0.12)' },
}

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

function toMonthStr(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function shiftMonth(m: string, delta: number): string {
  const [y, mo] = m.split('-').map(Number)
  return toMonthStr(new Date(y, mo - 1 + delta, 1))
}

function SectionTitle({ icon: Icon, label }: { icon: any; label: string }) {
  return (
    <div className={styles.sectionHeader}>
      <Icon size={13} strokeWidth={2} className={styles.sectionIcon} />
      <h2 className={styles.sectionTitle}>{label}</h2>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<TransactionStats | null>(null)
  const [compensation, setCompensation] = useState<CompensationResult | null>(null)
  const [summary, setSummary] = useState<SavingsSummary | null>(null)
  const [insights, setInsights] = useState<Insight[]>([])
  const [recentTxns, setRecentTxns] = useState<Transaction[]>([])
  const [cashflow, setCashflow] = useState<CashFlowMonth[]>([])
  const [recurring, setRecurring] = useState<RecurringPattern[]>([])
  const [activeMonth, setActiveMonth] = useState(currentMonth)
  const [exportingPDF, setExportingPDF] = useState(false)
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([])
  const [bankTotal, setBankTotal] = useState(0)
  const [dashLoading, setDashLoading] = useState(true)
  const [showQuickAdd, setShowQuickAdd] = useState(false)
  const [quickForm, setQuickForm] = useState({ label: '', amount: '', type: 'expense', category: '' })
  const [quickCats, setQuickCats] = useState<any[]>([])
  const [quickSaving, setQuickSaving] = useState(false)

  async function handleQuickAdd() {
    if (!quickForm.label.trim() || !quickForm.amount) return
    setQuickSaving(true)
    try {
      await transactionsAPI.create({
        label: quickForm.label.trim(),
        amount: parseFloat(quickForm.amount),
        type: quickForm.type,
        category: quickForm.category || null,
        date: new Date().toISOString().slice(0, 10),
        source: 'manual',
      })
      setQuickForm({ label: '', amount: '', type: 'expense', category: '' })
      setShowQuickAdd(false)
      reload()
    } finally {
      setQuickSaving(false)
    }
  }

  async function handleExportPDF() {
    setExportingPDF(true)
    try {
      const res = await documentsAPI.downloadPDF(activeMonth)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `budget-master-${activeMonth}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExportingPDF(false)
    }
  }

  useEffect(() => {
    transactionsAPI.list({}).then(r => {
      const all: Transaction[] = r.data.results ?? r.data
      const month = all.length > 0 ? toMonthStr(new Date(all[0].date)) : currentMonth
      setActiveMonth(month)
    })
    transactionsAPI.insights().then(r => setInsights(r.data)).catch(() => {})
    goalsAPI.cashflow(12).then(r => setCashflow(r.data)).catch(() => {})
    transactionsAPI.recurringDetected().then(r => setRecurring(r.data)).catch(() => {})
    accountsAPI.list().then(r => setBankAccounts(r.data.results ?? r.data)).catch(() => {})
    accountsAPI.summary().then(r => setBankTotal(r.data.total_balance ?? 0)).catch(() => {})
    categoriesAPI.list().then(r => setQuickCats(r.data.results ?? r.data)).catch(() => {})
  }, [])

  function reload() {
    if (!activeMonth) return
    setDashLoading(true)
    Promise.all([
      transactionsAPI.stats({ month: activeMonth }).then(r => setStats(r.data)),
      savingsAPI.compensation({ month: activeMonth }).then(r => setCompensation(r.data)).catch(() => {}),
      savingsAPI.summary({ month: activeMonth }).then(r => setSummary(r.data)).catch(() => {}),
      transactionsAPI.list({ month: activeMonth }).then(r => setRecentTxns((r.data.results ?? r.data).slice(0, 5))).catch(() => {}),
    ]).finally(() => setDashLoading(false))
  }

  useEffect(() => { reload() }, [activeMonth])

  const ruleData = stats ? [
    { name: 'Besoins', value: stats.rule_503020.needs, target: 50, color: '#60A5FA' },
    { name: 'Envies', value: stats.rule_503020.wants, target: 30, color: '#A78BFA' },
    { name: 'Épargne', value: stats.rule_503020.savings, target: 20, color: '#34D399' },
  ] : []

  const pieData = stats?.by_category?.slice(0, 8).map(c => ({
    name: c.category__name ?? 'Autre',
    value: parseFloat(String(c.total)),
    color: c.category__color ?? '#6b7280',
  })) ?? []

  const trendMap: Record<string, Record<string, number>> = {}
  stats?.trend?.forEach(t => {
    const m = typeof t.month === 'string' ? t.month.slice(0, 7) : new Date(t.month).toISOString().slice(0, 7)
    if (!trendMap[m]) trendMap[m] = {}
    trendMap[m][t.type] = (trendMap[m][t.type] ?? 0) + parseFloat(String(t.total))
  })
  const trendData = Object.entries(trendMap).slice(-6).map(([month, v]) => ({
    month: month.slice(5),
    Revenus: v.income ?? 0,
    Dépenses: v.expense ?? 0,
    Épargne: v.saving ?? 0,
  }))

  const cashflowFormatted = cashflow.map(m => ({
    month: m.month.slice(5),
    solde: m.running_balance,
    alert: m.alert,
  }))

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Dashboard</h1>
        <div className={styles.headerRight}>
          {stats?.risk && (() => {
            const rc = RISK_CONFIG[stats.risk]
            return (
              <span className={styles.riskBadge} style={{ color: rc.color, background: rc.bg }}>
                {rc.label}
              </span>
            )
          })()}
          <button
            onClick={() => setShowQuickAdd(true)}
            style={{ display:'flex', alignItems:'center', gap:'0.4rem', background:'var(--accent)', color:'#000', border:'none', borderRadius:'var(--radius-md)', padding:'0.4rem 0.875rem', fontSize:'0.8rem', fontWeight:700, cursor:'pointer' }}
          >+ Ajouter</button>
          <button
            onClick={handleExportPDF}
            disabled={exportingPDF}
            style={{ display:'flex', alignItems:'center', gap:'0.4rem', background:'rgba(0,212,170,0.1)', color:'var(--accent)', border:'1px solid rgba(0,212,170,0.25)', borderRadius:'var(--radius-md)', padding:'0.4rem 0.875rem', fontSize:'0.8rem', fontWeight:600, cursor:'pointer' }}
          >
            <FileDown size={14} />
            {exportingPDF ? 'Export…' : 'PDF'}
          </button>
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
      </div>

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        {dashLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <Skeleton width="50%" height="0.75rem" />
                <Skeleton width="70%" height="1.5rem" />
              </div>
            ))
          : <>
              <KPICard label="Revenus" value={stats?.income ?? 0} icon="↑" color="var(--accent-green)" index={0} />
              <KPICard label="Dépenses" value={stats?.expenses ?? 0} icon="↓" color="var(--accent-red)" index={1} />
              <KPICard label="Solde" value={stats?.balance ?? 0} icon="=" color="var(--accent)" index={2} />
              <KPICard label="Épargne" value={stats?.savings ?? 0} icon="◎" color="var(--accent-blue)" index={3} />
            </>
        }
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={Lightbulb} label="Insights" />
          <AlertBanner insights={insights} />
        </section>
      )}

      <div className={styles.grid2}>
        {/* Rule 50/30/20 */}
        <section className={styles.section}>
          <SectionTitle icon={Scale} label="Règle 50 / 30 / 20" />
          <div className={styles.ruleTable}>
            <div className={styles.ruleHeader}>
              <span>Bucket</span><span>Cible</span><span>Réel</span><span>Écart</span>
            </div>
            {ruleData.map(r => {
              const gap = r.value - r.target
              const ok = Math.abs(gap) <= 5
              return (
                <div key={r.name} className={styles.ruleRow}>
                  <span style={{ color: r.color }}>{r.name}</span>
                  <span>{r.target}%</span>
                  <span>{r.value.toFixed(1)}%</span>
                  <span style={{ color: ok ? 'var(--accent-green)' : gap > 0 ? 'var(--accent-red)' : 'var(--accent-orange)' }}>
                    {gap > 0 ? '+' : ''}{gap.toFixed(1)}%
                  </span>
                </div>
              )
            })}
          </div>
          {compensation && <div style={{ marginTop: '1rem' }}><CompensationPlanCard data={compensation} /></div>}
        </section>

        {/* Savings accounts */}
        <section className={styles.section}>
          <SectionTitle icon={Landmark} label="Épargne" />
          {summary?.accounts.map(acc => (
            <div key={acc.id} className={styles.savingRow}>
              <span className={styles.savingIcon} style={{ background: `${acc.color}18`, color: acc.color }}>{acc.icon}</span>
              <div className={styles.savingInfo}>
                <div className={styles.savingName}>{acc.name}</div>
                {acc.target && (
                  <div className={styles.savingBar}>
                    <div className={styles.savingFill} style={{ width: `${Math.min((acc.balance / acc.target) * 100, 100)}%`, background: acc.color }} />
                  </div>
                )}
              </div>
              <div className={styles.savingBalance}>
                {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(acc.balance)}
              </div>
            </div>
          ))}
          {summary && (
            <div className={styles.savingTotal}>
              Total : <strong>{new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(summary.total_balance)}</strong>
              <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)' }}>· taux moy. {summary.avg_rate_6m.toFixed(1)}%</span>
            </div>
          )}
        </section>
      </div>

      <div className={styles.grid2}>
        {/* Pie chart */}
        <section className={styles.section}>
          <SectionTitle icon={PieChartIcon} label="Répartition dépenses" />
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={210}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={52} outerRadius={80} dataKey="value" paddingAngle={2}>
                  {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip content={PieTooltip} />
                <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: '0.8rem', paddingTop: '0.75rem', color: 'var(--text-primary)' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className={styles.empty}>Aucune dépense ce mois</div>}
        </section>

        {/* Bar chart */}
        <section className={styles.section}>
          <SectionTitle icon={BarChart2} label="Évolution 6 mois" />
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={trendData} barSize={12} barGap={2}>
              <XAxis dataKey="month" tick={{ fill: 'var(--text-secondary)', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
              <Tooltip content={CustomTooltip} />
              <Bar dataKey="Revenus" fill="var(--accent-green)" radius={[3,3,0,0]} />
              <Bar dataKey="Dépenses" fill="var(--accent-red)" radius={[3,3,0,0]} />
              <Bar dataKey="Épargne" fill="var(--accent-blue)" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      {/* Cash flow projection */}
      {cashflow.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={CandlestickChart} label="Projection trésorerie 12 mois" />
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={cashflowFormatted} barSize={14}>
              <XAxis dataKey="month" tick={{ fill: 'var(--text-secondary)', fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
              <Tooltip content={CustomTooltip} />
              <Bar dataKey="solde" radius={[3,3,0,0]}>
                {cashflowFormatted.map((entry, i) => {
                  let color: string
                  if (entry.solde >= 0) color = 'var(--accent-green)'
                  else if (entry.solde >= -500) color = 'var(--accent-orange)'
                  else color = 'var(--accent-red)'
                  return <Cell key={i} fill={color} />
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Recurring patterns */}
      {recurring.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={RefreshCw} label="Dépenses récurrentes détectées" />
          <div className={styles.recurringGrid}>
            {recurring.slice(0, 6).map((r, i) => (
              <div key={i} className={styles.recurringItem}>
                <span className={styles.recurringIcon}>{r.category_icon || '🔄'}</span>
                <div className={styles.recurringInfo}>
                  <div className={styles.recurringLabel}>{r.label}</div>
                  <div className={styles.recurringMeta}>{r.category} · {r.frequency}</div>
                </div>
                <div className={styles.recurringAmt}>
                  ~{new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(r.avg_amount)}
                  <span className={styles.confidenceDot} style={{ background: r.confidence === 'high' ? 'var(--accent-green)' : 'var(--accent-orange)' }} title={r.confidence === 'high' ? 'Confiance haute' : 'Confiance moyenne'} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Bank accounts */}
      {bankAccounts.length > 0 && (
        <section className={styles.section}>
          <SectionTitle icon={Building2} label="Comptes bancaires" />
          <div className={styles.bankGrid}>
            {bankAccounts.map(acc => (
              <div key={acc.id} className={styles.bankCard}>
                <div className={styles.bankIcon} style={{ background: `${acc.color}18`, color: acc.color }}>{acc.icon}</div>
                <div className={styles.bankInfo}>
                  <div className={styles.bankName}>{acc.name}</div>
                  {acc.bank_name && <div className={styles.bankSub}>{acc.bank_name}</div>}
                </div>
                <div className={styles.bankBalance} style={{ color: acc.balance >= 0 ? '#34d399' : '#f87171' }}>
                  {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(acc.balance)}
                </div>
              </div>
            ))}
          </div>
          {bankAccounts.length > 1 && (
            <div className={styles.bankTotal}>
              Total comptes : <strong style={{ color: bankTotal >= 0 ? '#34d399' : '#f87171' }}>
                {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(bankTotal)}
              </strong>
            </div>
          )}
        </section>
      )}

      {/* Recent transactions */}
      <section className={styles.section}>
        <SectionTitle icon={TrendingUp} label="Transactions récentes" />
        <div className={styles.txnList}>
          {dashLoading
            ? <SkeletonList count={5} />
            : recentTxns.length > 0
              ? recentTxns.map(t => <TransactionRow key={t.id} transaction={t} />)
              : <div className={styles.empty}>Aucune transaction ce mois</div>
          }
        </div>
      </section>

      {/* Quick-add modal */}
      {showQuickAdd && (
        <div className={styles.qaOverlay} onClick={() => setShowQuickAdd(false)}>
          <div className={styles.qaModal} onClick={e => e.stopPropagation()}>
            <div className={styles.qaTitle}>Nouvelle transaction</div>
            <div className={styles.qaToggle}>
              {(['expense','income','saving'] as const).map(t => (
                <button
                  key={t}
                  className={`${styles.qaToggleBtn} ${quickForm.type === t ? styles.qaToggleActive : ''}`}
                  onClick={() => setQuickForm(f => ({ ...f, type: t }))}
                  style={quickForm.type === t ? { borderColor: t==='income' ? 'var(--accent-green)' : t==='saving' ? 'var(--accent-blue)' : 'var(--accent-red)', color: t==='income' ? 'var(--accent-green)' : t==='saving' ? 'var(--accent-blue)' : 'var(--accent-red)' } : {}}
                >
                  {t === 'expense' ? 'Dépense' : t === 'income' ? 'Revenu' : 'Épargne'}
                </button>
              ))}
            </div>
            <input
              className={styles.qaInput}
              placeholder="Libellé"
              value={quickForm.label}
              onChange={e => setQuickForm(f => ({ ...f, label: e.target.value }))}
              autoFocus
            />
            <div className={styles.qaRow}>
              <input
                className={styles.qaInput}
                type="number"
                step="0.01"
                placeholder="Montant (€)"
                value={quickForm.amount}
                onChange={e => setQuickForm(f => ({ ...f, amount: e.target.value }))}
              />
              <select
                className={styles.qaInput}
                value={quickForm.category}
                onChange={e => setQuickForm(f => ({ ...f, category: e.target.value }))}
              >
                <option value="">Catégorie…</option>
                {quickCats.filter((c: any) => c.type !== 'income' || quickForm.type === 'income').map((c: any) => (
                  <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                ))}
              </select>
            </div>
            <div className={styles.qaFooter}>
              <button className={styles.qaCancel} onClick={() => setShowQuickAdd(false)}>Annuler</button>
              <button
                className={styles.qaSubmit}
                onClick={handleQuickAdd}
                disabled={quickSaving || !quickForm.label.trim() || !quickForm.amount}
              >{quickSaving ? '…' : 'Enregistrer'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
