import { useEffect, useState } from 'react'
import { savingsAPI } from '../../services/api'
import { useToast } from '../../context/ToastContext'
import type { SavingsSummary, SavingsAccount, CompensationResult } from '../../types'
import CompensationPlanCard from '../../components/CompensationPlanCard/CompensationPlanCard'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import Goals from '../Goals'
import styles from './Savings.module.css'

type Tab = 'accounts' | 'goals'

const ICONS = ['🏦', '💰', '💎', '🏠', '🚗', '✈️', '📈', '🎓', '👶', '🌍', '⚡', '🛡️', '🌱', '💊', '🎯']
const COLORS = ['#2dd4bf', '#3b82f6', '#a78bfa', '#f59e0b', '#ef4444', '#22c55e', '#ec4899', '#f97316', '#06b6d4', '#84cc16']

interface FormState {
  name: string
  icon: string
  color: string
  interest_rate: string
  target: string
  initial_balance: string
}

const defaultForm: FormState = { name: '', icon: '🏦', color: '#2dd4bf', interest_rate: '', target: '', initial_balance: '' }

export default function Savings() {
  const [tab, setTab] = useState<Tab>('accounts')
  const [summary, setSummary] = useState<SavingsSummary | null>(null)
  const [comp, setComp] = useState<CompensationResult | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(defaultForm)
  const [saving, setSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const { toast } = useToast()

  function reload() {
    savingsAPI.summary().then(r => setSummary(r.data))
    savingsAPI.compensation().then(r => setComp(r.data)).catch(() => {})
  }

  useEffect(() => { reload() }, [])

  function openAdd() {
    setEditing(null)
    setForm(defaultForm)
    setShowModal(true)
  }

  function openEdit(acc: SavingsSummary['accounts'][0]) {
    setEditing(acc.id)
    setForm({
      name: acc.name,
      icon: acc.icon,
      color: acc.color,
      interest_rate: acc.interest_rate != null ? String(acc.interest_rate) : '',
      target: acc.target != null ? String(acc.target) : '',
      initial_balance: acc.initial_balance != null ? String(acc.initial_balance) : '0',
    })
    setShowModal(true)
  }

  async function handleSave() {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        icon: form.icon,
        color: form.color,
        interest_rate: form.interest_rate ? parseFloat(form.interest_rate) : null,
        target: form.target ? parseFloat(form.target) : null,
        initial_balance: form.initial_balance ? parseFloat(form.initial_balance) : 0,
      }
      if (editing != null) {
        await savingsAPI.accounts.update(editing, payload)
      } else {
        await savingsAPI.accounts.create(payload)
      }
      setShowModal(false)
      toast(editing != null ? 'Compte modifié' : 'Compte créé')
      reload()
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    await savingsAPI.accounts.delete(id)
    setDeleteConfirm(null)
    toast('Compte supprimé', 'info')
    reload()
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Épargne</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {tab === 'accounts' && (
            <button className={styles.btnPrimary} onClick={openAdd}>+ Ajouter un compte</button>
          )}
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${tab === 'accounts' ? styles.tabActive : ''}`}
              onClick={() => setTab('accounts')}
            >🏦 Comptes</button>
            <button
              className={`${styles.tab} ${tab === 'goals' ? styles.tabActive : ''}`}
              onClick={() => setTab('goals')}
            >🎯 Objectifs</button>
          </div>
        </div>
      </div>

      {tab === 'accounts' && (
        <>
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
            <h2 className={styles.sectionTitle}>Comptes épargne</h2>
            <div className={styles.accGrid}>
              {summary?.accounts.map(acc => (
                <div key={acc.id} className={styles.accCard} style={{ '--ac': acc.color } as React.CSSProperties}>
                  <div className={styles.accActions}>
                    <button className={styles.accBtn} title="Modifier" onClick={() => openEdit(acc)}>✎</button>
                    <button className={styles.accBtn} title="Supprimer" onClick={() => setDeleteConfirm(acc.id)}>✕</button>
                  </div>
                  <div className={styles.accHeader}>
                    <span className={styles.accIcon} style={{ background: `${acc.color}22`, color: acc.color }}>{acc.icon}</span>
                    <div>
                      <div className={styles.accName}>{acc.name}</div>
                      {acc.interest_rate != null && <div className={styles.accRate}>{acc.interest_rate}% / an</div>}
                    </div>
                  </div>
                  <div className={styles.accBalance} style={{ color: acc.color }}>
                    {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(acc.balance)}
                  </div>
                  {acc.target != null ? (
                    <>
                      <ProgressBar value={acc.balance} max={acc.target} color={acc.color} showLabel />
                      <div className={styles.accTarget}>Plafond : {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(acc.target)}</div>
                    </>
                  ) : (
                    <div className={styles.accNoTarget}>Pas de plafond défini</div>
                  )}
                  {acc.month_contribution > 0 ? (
                    <div className={styles.accContrib}>
                      +{new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(acc.month_contribution)} ce mois
                    </div>
                  ) : (
                    <div className={styles.accContribNone}>Aucun versement ce mois</div>
                  )}
                </div>
              ))}
              {summary?.accounts.length === 0 && (
                <div className={styles.empty}>Aucun compte — cliquez sur "+ Ajouter un compte"</div>
              )}
            </div>
          </section>

          {/* Compensation */}
          {comp && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>⚙️ Règle adaptative</h2>
              <CompensationPlanCard data={comp} />
            </section>
          )}
        </>
      )}

      {tab === 'goals' && <Goals />}

      {/* Add / Edit modal */}
      {showModal && (
        <div className={styles.overlay} onClick={() => setShowModal(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalTitle}>{editing != null ? 'Modifier le compte' : 'Nouveau compte épargne'}</div>

            <div className={styles.form}>
              <div className={styles.field}>
                <label>Nom</label>
                <input className={styles.input} placeholder="ex : Livret A" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} autoFocus />
              </div>

              <div className={styles.field}>
                <label>Icône</label>
                <div className={styles.pickerRow}>
                  {ICONS.map(ic => (
                    <button key={ic} className={`${styles.pickerItem} ${form.icon === ic ? styles.pickerActive : ''}`} onClick={() => setForm(f => ({ ...f, icon: ic }))}>{ic}</button>
                  ))}
                </div>
              </div>

              <div className={styles.field}>
                <label>Couleur</label>
                <div className={styles.pickerRow}>
                  {COLORS.map(c => (
                    <button key={c} className={`${styles.colorDot} ${form.color === c ? styles.colorDotActive : ''}`} style={{ background: c }} onClick={() => setForm(f => ({ ...f, color: c }))} />
                  ))}
                </div>
              </div>

              <div className={styles.fieldRow}>
                <div className={styles.field}>
                  <label>Solde initial (€)</label>
                  <input className={styles.input} type="number" step="0.01" placeholder="0.00" value={form.initial_balance} onChange={e => setForm(f => ({ ...f, initial_balance: e.target.value }))} />
                </div>
                <div className={styles.field}>
                  <label>Taux d'intérêt (%/an)</label>
                  <input className={styles.input} type="number" step="0.01" placeholder="ex : 3.00" value={form.interest_rate} onChange={e => setForm(f => ({ ...f, interest_rate: e.target.value }))} />
                </div>
              </div>

              <div className={styles.field}>
                <label>Plafond / objectif (€) — optionnel</label>
                <input className={styles.input} type="number" step="0.01" placeholder="ex : 22950" value={form.target} onChange={e => setForm(f => ({ ...f, target: e.target.value }))} />
              </div>
            </div>

            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setShowModal(false)}>Annuler</button>
              <button className={styles.btnPrimary} onClick={handleSave} disabled={saving || !form.name.trim()}>
                {saving ? 'Enregistrement…' : editing != null ? 'Enregistrer' : 'Créer le compte'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {deleteConfirm != null && (
        <div className={styles.overlay} onClick={() => setDeleteConfirm(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()} style={{ maxWidth: 380 }}>
            <div className={styles.modalTitle}>Supprimer ce compte ?</div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              Cette action est irréversible. Les transactions liées à ce compte ne seront pas supprimées.
            </p>
            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setDeleteConfirm(null)}>Annuler</button>
              <button className={styles.btnDanger} onClick={() => handleDelete(deleteConfirm)}>Supprimer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
