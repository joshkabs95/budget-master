import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  PieChart as PieChartIcon, BarChart2, TrendingUp,
  Landmark, Lightbulb, Scale, CandlestickChart
} from 'lucide-react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { transactionsAPI, savingsAPI, goalsAPI } from '../../services/api'
import KPICard from '../../components/KPICard/KPICard'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import AlertBanner from '../../components/AlertBanner/AlertBanner'
import TransactionRow from '../../components/TransactionRow/TransactionRow'
import type { TransactionStats, CompensationResult, SavingsSummary, Insight, Transaction, CashFlowMonth } from '../../types'
import styles from './Dashboard.module.css'

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
  const [activeMonth, setActiveMonth] = useState(currentMonth)

  useEffect(() => {
    transactionsAPI.list({}).then(r => {
      const all: Transaction[] = r.data.results ?? r.data
      const month = all.length > 0 ? toMonthStr(new Date(all[0].date)) : currentMonth
      setActiveMonth(month)
    })
    transactionsAPI.insights().then(r => setInsights(r.data)).catch(() => {})
    goalsAPI.cashflow(12).then(r => setCashflow(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!activeMonth) return
    transactionsAPI.stats({ month: activeMonth }).then(r => setStats(r.data))
    savingsAPI.compensation({ month: activeMonth }).then(r => setCompensation(r.data)).catch(() => {})
    savingsAPI.summary({ month: activeMonth }).then(r => setSummary(r.data)).catch(() => {})
    transactionsAPI.list({ month: activeMonth }).then(r => setRecentTxns((r.data.results ?? r.data).slice(0, 5))).catch(() => {})
  }, [activeMonth])

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

  const tooltipStyle = {
    background: 'var(--bg-overlay)',
    border: '1px solid var(--border-hover)',
    borderRadius: 8,
    fontSize: 12,
    boxShadow: 'var(--shadow-md)',
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Dashboard</h1>
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

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <KPICard label="Revenus" value={stats?.income ?? 0} icon="↑" color="var(--accent-green)" index={0} />
        <KPICard label="Dépenses" value={stats?.expenses ?? 0} icon="↓" color="var(--accent-red)" index={1} />
        <KPICard label="Solde" value={stats?.balance ?? 0} icon="=" color="var(--accent)" index={2} />
        <KPICard label="Épargne" value={stats?.savings ?? 0} icon="◎" color="var(--accent-blue)" index={3} />
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
                <Tooltip formatter={(v: number) => `${v.toFixed(0)} €`} contentStyle={tooltipStyle} />
                <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: '0.72rem', paddingTop: '0.5rem' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className={styles.empty}>Aucune dépense ce mois</div>}
        </section>

        {/* Bar chart */}
        <section className={styles.section}>
          <SectionTitle icon={BarChart2} label="Évolution 6 mois" />
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={trendData} barSize={12} barGap={2}>
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={tooltipStyle} />
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
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v.toFixed(0)} €`} />
              <Bar dataKey="solde" radius={[3,3,0,0]}>
                {cashflowFormatted.map((entry, i) => (
                  <Cell key={i} fill={entry.alert ? 'var(--accent-red)' : entry.solde >= 0 ? 'var(--accent)' : 'var(--accent-orange)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Recent transactions */}
      <section className={styles.section}>
        <SectionTitle icon={TrendingUp} label="Transactions récentes" />
        <div className={styles.txnList}>
          {recentTxns.length > 0
            ? recentTxns.map(t => <TransactionRow key={t.id} transaction={t} />)
            : <div className={styles.empty}>Aucune transaction ce mois</div>
          }
        </div>
      </section>
    </div>
  )
}
