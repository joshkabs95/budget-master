import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
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

export default function Dashboard() {
  const [stats, setStats] = useState<TransactionStats | null>(null)
  const [compensation, setCompensation] = useState<CompensationResult | null>(null)
  const [summary, setSummary] = useState<SavingsSummary | null>(null)
  const [insights, setInsights] = useState<Insight[]>([])
  const [recentTxns, setRecentTxns] = useState<Transaction[]>([])
  const [cashflow, setCashflow] = useState<CashFlowMonth[]>([])

  useEffect(() => {
    transactionsAPI.stats({ month: currentMonth }).then(r => setStats(r.data))
    savingsAPI.compensation().then(r => setCompensation(r.data)).catch(() => {})
    savingsAPI.summary({ month: currentMonth }).then(r => setSummary(r.data)).catch(() => {})
    transactionsAPI.insights().then(r => setInsights(r.data)).catch(() => {})
    transactionsAPI.list({ month: currentMonth }).then(r => setRecentTxns((r.data.results ?? r.data).slice(0, 5))).catch(() => {})
    goalsAPI.cashflow(12).then(r => setCashflow(r.data)).catch(() => {})
  }, [])

  const ruleData = stats ? [
    { name: 'Besoins', value: stats.rule_503020.needs, target: 50, color: '#3b82f6' },
    { name: 'Envies', value: stats.rule_503020.wants, target: 30, color: '#a855f7' },
    { name: 'Épargne', value: stats.rule_503020.savings, target: 20, color: '#22c55e' },
  ] : []

  const pieData = stats?.by_category?.slice(0, 8).map(c => ({
    name: c.category__name ?? 'Autre',
    value: parseFloat(String(c.total)),
    color: c.category__color ?? '#6b6b7e',
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
        <span className={styles.month}>{new Date().toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}</span>
      </div>

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <KPICard label="Revenus" value={stats?.income ?? 0} icon="💰" color="var(--accent-green)" index={0} />
        <KPICard label="Dépenses" value={stats?.expenses ?? 0} icon="💳" color="var(--accent-red)" index={1} />
        <KPICard label="Solde" value={stats?.balance ?? 0} icon="⚖️" color="var(--accent-gold)" index={2} />
        <KPICard label="Épargne" value={stats?.savings ?? 0} icon="🏦" color="var(--accent-blue)" index={3} />
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>💡 Insights</h2>
          <AlertBanner insights={insights} />
        </section>
      )}

      <div className={styles.grid2}>
        {/* Rule 50/30/20 */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>⚖️ Règle 50/30/20</h2>
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
          <h2 className={styles.sectionTitle}>🏦 Épargne</h2>
          {summary?.accounts.map(acc => (
            <div key={acc.id} className={styles.savingRow}>
              <span className={styles.savingIcon} style={{ background: `${acc.color}22`, color: acc.color }}>{acc.icon}</span>
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
          <h2 className={styles.sectionTitle}>🍩 Répartition dépenses</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" paddingAngle={2}>
                  {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip formatter={(v: number) => `${v.toFixed(0)} €`} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.75rem' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className={styles.empty}>Aucune dépense ce mois</div>}
        </section>

        {/* Bar chart */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>📊 Évolution 6 mois</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trendData} barSize={14}>
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
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
          <h2 className={styles.sectionTitle}>📈 Projection trésorerie 12 mois</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={cashflowFormatted} barSize={16}>
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} formatter={(v: number) => `${v.toFixed(0)} €`} />
              <Bar dataKey="solde" radius={[3,3,0,0]}>
                {cashflowFormatted.map((entry, i) => <Cell key={i} fill={entry.alert ? 'var(--accent-red)' : 'var(--accent-blue)'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Recent transactions */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>🕐 Transactions récentes</h2>
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
