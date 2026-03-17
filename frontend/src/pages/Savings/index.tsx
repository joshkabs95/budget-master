import { useEffect, useState } from 'react'
import { savingsAPI } from '../../services/api'
import type { SavingsSummary, CompensationResult } from '../../types'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import styles from './Savings.module.css'

export default function Savings() {
  const [summary, setSummary] = useState<SavingsSummary | null>(null)
  const [comp, setComp] = useState<CompensationResult | null>(null)

  useEffect(() => {
    savingsAPI.summary().then(r => setSummary(r.data))
    savingsAPI.compensation().then(r => setComp(r.data)).catch(() => {})
  }, [])

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Épargne</h1>

      {/* Summary KPIs */}
      {summary && (
        <div className={styles.kpiRow}>
          <div className={styles.kpi}>
            <div className={styles.kpiVal} style={{ color: 'var(--accent-blue)' }}>
              {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(summary.total_balance)}
            </div>
            <div className={styles.kpiLabel}>Total épargné</div>
          </div>
          <div className={styles.kpi}>
            <div className={styles.kpiVal} style={{ color: summary.savings_rate >= summary.target_rate ? 'var(--accent-green)' : 'var(--accent-orange)' }}>
              {summary.savings_rate.toFixed(1)}%
            </div>
            <div className={styles.kpiLabel}>Taux ce mois</div>
          </div>
          <div className={styles.kpi}>
            <div className={styles.kpiVal} style={{ color: 'var(--text-muted)' }}>{summary.avg_rate_6m.toFixed(1)}%</div>
            <div className={styles.kpiLabel}>Moy. 6 mois</div>
          </div>
          <div className={styles.kpi}>
            <div className={styles.kpiVal} style={{ color: 'var(--accent-gold)' }}>{summary.target_rate}%</div>
            <div className={styles.kpiLabel}>Cible</div>
          </div>
        </div>
      )}

      {/* Accounts */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>🏦 Comptes épargne</h2>
        <div className={styles.accGrid}>
          {summary?.accounts.map(acc => (
            <div key={acc.id} className={styles.accCard} style={{ '--ac': acc.color } as React.CSSProperties}>
              <div className={styles.accHeader}>
                <span className={styles.accIcon} style={{ background: `${acc.color}22`, color: acc.color }}>{acc.icon}</span>
                <div>
                  <div className={styles.accName}>{acc.name}</div>
                  {acc.interest_rate && <div className={styles.accRate}>{acc.interest_rate}% / an</div>}
                </div>
              </div>
              <div className={styles.accBalance} style={{ color: acc.color }}>
                {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(acc.balance)}
              </div>
              {acc.target && (
                <>
                  <ProgressBar value={acc.balance} max={acc.target} color={acc.color} showLabel />
                  <div className={styles.accTarget}>Plafond : {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(acc.target)}</div>
                </>
              )}
              <div className={styles.accContrib}>
                +{new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(acc.month_contribution)} ce mois
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Compensation */}
      {comp && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>⚙️ Règle adaptative</h2>
          <CompensationPlanCard data={comp} />
        </section>
      )}
    </div>
  )
}
