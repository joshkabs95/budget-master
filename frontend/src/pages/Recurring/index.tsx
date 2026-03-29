import { useEffect, useState } from 'react'
import { transactionsAPI, categoriesAPI } from '../../services/api'
import type { Transaction, Category } from '../../types'
import styles from './Recurring.module.css'

interface DetectedPattern {
  label: string
  category: string
  category_icon: string
  type: 'expense' | 'income'
  avg_amount: number
  months_seen: number
  frequency: string
  confidence: 'high' | 'medium'
}

const RECURRENCE_LABELS: Record<string, string> = {
  monthly: 'Mensuel',
  weekly: 'Hebdomadaire',
  yearly: 'Annuel',
}

const TYPE_LABELS: Record<string, string> = {
  expense: 'Dépense',
  income: 'Revenu',
  saving: 'Épargne',
}

function fmt(amount: number | string) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(Number(amount))
}

function nextOccurrence(txn: Transaction): string {
  const d = new Date(txn.date)
  const today = new Date()
  if (txn.recurrence === 'monthly') {
    const next = new Date(today.getFullYear(), today.getMonth(), d.getDate())
    if (next <= today) next.setMonth(next.getMonth() + 1)
    return next.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
  }
  if (txn.recurrence === 'yearly') {
    const next = new Date(today.getFullYear(), d.getMonth(), d.getDate())
    if (next <= today) next.setFullYear(next.getFullYear() + 1)
    return next.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
  }
  if (txn.recurrence === 'weekly') {
    const next = new Date(today)
    const diff = (d.getDay() - today.getDay() + 7) % 7 || 7
    next.setDate(today.getDate() + diff)
    return next.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'short' })
  }
  return '—'
}

export default function Recurring() {
  const [patterns, setPatterns] = useState<DetectedPattern[]>([])
  const [confirmed, setConfirmed] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ label: '', amount: '', type: 'expense', recurrence: 'monthly', category: '', date: '' })
  const [saving, setSaving] = useState(false)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  async function reload() {
    setLoading(true)
    try {
      const [p, c, cats] = await Promise.all([
        transactionsAPI.recurringDetected(),
        transactionsAPI.recurringList(),
        categoriesAPI.list(),
      ])
      setPatterns(p.data)
      setConfirmed(c.data.results ?? c.data)
      setCategories(cats.data.results ?? cats.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, [])

  async function confirmPattern(pattern: DetectedPattern) {
    // Find a matching transaction to mark as recurring
    const { data } = await transactionsAPI.list({ page_size: 50 })
    const txns: Transaction[] = data.results ?? data
    const match = txns.find(t =>
      t.label.toLowerCase() === pattern.label.toLowerCase() && t.type === pattern.type
    )
    if (!match) return
    await transactionsAPI.patch(match.id, { is_recurring: true, recurrence: pattern.frequency })
    reload()
  }

  async function handleAdd() {
    if (!addForm.label || !addForm.amount) return
    setSaving(true)
    try {
      await transactionsAPI.create({
        label: addForm.label,
        amount: parseFloat(addForm.amount),
        type: addForm.type,
        recurrence: addForm.recurrence,
        is_recurring: true,
        category: addForm.category || null,
        date: addForm.date || new Date().toISOString().slice(0, 10),
      })
      setShowAdd(false)
      setAddForm({ label: '', amount: '', type: 'expense', recurrence: 'monthly', category: '', date: '' })
      reload()
    } finally {
      setSaving(false)
    }
  }

  async function handleRemoveRecurring(txn: Transaction) {
    await transactionsAPI.patch(txn.id, { is_recurring: false, recurrence: '' })
    setDeleteId(null)
    reload()
  }

  const confirmedLabels = new Set(confirmed.map(t => t.label.toLowerCase()))
  const unconfirmedPatterns = patterns.filter(p => !confirmedLabels.has(p.label.toLowerCase()))

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Transactions récurrentes</h1>
        <button className={styles.btnPrimary} onClick={() => setShowAdd(true)}>+ Ajouter</button>
      </div>

      {/* Auto-detected patterns */}
      {unconfirmedPatterns.length > 0 && (
        <section className={styles.section}>
          <div className={styles.sectionTitle}>
            🔍 Patterns détectés automatiquement
            <span className={styles.sectionBadge}>{unconfirmedPatterns.length}</span>
          </div>
          <p className={styles.sectionDesc}>
            Ces transactions apparaissent régulièrement. Confirmez-les pour les suivre en tant que récurrentes.
          </p>
          <div className={styles.patternGrid}>
            {unconfirmedPatterns.map((p, i) => (
              <div key={i} className={styles.patternCard}>
                <div className={styles.patternTop}>
                  <span className={styles.patternIcon}>{p.category_icon || '🔄'}</span>
                  <div className={styles.patternInfo}>
                    <div className={styles.patternLabel}>{p.label}</div>
                    <div className={styles.patternMeta}>{p.category || 'Sans catégorie'} · {RECURRENCE_LABELS[p.frequency]}</div>
                  </div>
                  <span className={`${styles.confidenceBadge} ${p.confidence === 'high' ? styles.confHigh : styles.confMed}`}>
                    {p.confidence === 'high' ? '↑ Haute' : '~ Moyenne'}
                  </span>
                </div>
                <div className={styles.patternBottom}>
                  <div>
                    <span className={styles.patternAmt}>{fmt(p.avg_amount)}</span>
                    <span className={styles.patternFreq}> / mois · {p.months_seen} mois consécutifs</span>
                  </div>
                  <button className={styles.btnConfirm} onClick={() => confirmPattern(p)}>Confirmer</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Confirmed recurring */}
      <section className={styles.section}>
        <div className={styles.sectionTitle}>
          ✅ Récurrentes confirmées
          <span className={styles.sectionBadge}>{confirmed.length}</span>
        </div>
        {loading ? (
          <div className={styles.empty}>Chargement…</div>
        ) : confirmed.length === 0 ? (
          <div className={styles.empty}>Aucune transaction récurrente confirmée</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Libellé</th>
                <th>Type</th>
                <th>Montant</th>
                <th>Fréquence</th>
                <th>Prochaine occurrence</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {confirmed.map(txn => (
                <tr key={txn.id}>
                  <td>
                    <div className={styles.txnLabel}>
                      <span className={styles.txnIcon}>{txn.category_detail?.icon || '🔄'}</span>
                      {txn.label}
                    </div>
                    {txn.category_detail && <div className={styles.txnCat}>{txn.category_detail.name}</div>}
                  </td>
                  <td>
                    <span className={`${styles.typeBadge} ${styles[`type_${txn.type}`]}`}>
                      {TYPE_LABELS[txn.type]}
                    </span>
                  </td>
                  <td className={txn.type === 'income' ? styles.amtIncome : styles.amtExpense}>
                    {txn.type === 'income' ? '+' : '-'}{fmt(txn.amount)}
                  </td>
                  <td>{RECURRENCE_LABELS[txn.recurrence || ''] || '—'}</td>
                  <td className={styles.nextDate}>{txn.recurrence ? nextOccurrence(txn) : '—'}</td>
                  <td>
                    <button
                      className={styles.btnRemove}
                      title="Retirer de la liste récurrente"
                      onClick={() => setDeleteId(txn.id)}
                    >✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Add modal */}
      {showAdd && (
        <div className={styles.overlay} onClick={() => setShowAdd(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalTitle}>Nouvelle récurrente</div>
            <div className={styles.form}>
              <div className={styles.field}>
                <label>Libellé</label>
                <input className={styles.input} placeholder="ex : Loyer" value={addForm.label} onChange={e => setAddForm(f => ({ ...f, label: e.target.value }))} autoFocus />
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.field}>
                  <label>Montant (€)</label>
                  <input className={styles.input} type="number" step="0.01" placeholder="0.00" value={addForm.amount} onChange={e => setAddForm(f => ({ ...f, amount: e.target.value }))} />
                </div>
                <div className={styles.field}>
                  <label>Type</label>
                  <select className={styles.input} value={addForm.type} onChange={e => setAddForm(f => ({ ...f, type: e.target.value }))}>
                    <option value="expense">Dépense</option>
                    <option value="income">Revenu</option>
                    <option value="saving">Épargne</option>
                  </select>
                </div>
              </div>
              <div className={styles.fieldRow}>
                <div className={styles.field}>
                  <label>Fréquence</label>
                  <select className={styles.input} value={addForm.recurrence} onChange={e => setAddForm(f => ({ ...f, recurrence: e.target.value }))}>
                    <option value="monthly">Mensuel</option>
                    <option value="weekly">Hebdomadaire</option>
                    <option value="yearly">Annuel</option>
                  </select>
                </div>
                <div className={styles.field}>
                  <label>Date de référence</label>
                  <input className={styles.input} type="date" value={addForm.date} onChange={e => setAddForm(f => ({ ...f, date: e.target.value }))} />
                </div>
              </div>
              <div className={styles.field}>
                <label>Catégorie</label>
                <select className={styles.input} value={addForm.category} onChange={e => setAddForm(f => ({ ...f, category: e.target.value }))}>
                  <option value="">Sans catégorie</option>
                  {categories.map(c => (
                    <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setShowAdd(false)}>Annuler</button>
              <button className={styles.btnPrimary} onClick={handleAdd} disabled={saving || !addForm.label || !addForm.amount}>
                {saving ? 'Création…' : 'Créer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Remove confirm */}
      {deleteId != null && (
        <div className={styles.overlay} onClick={() => setDeleteId(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()} style={{ maxWidth: 380 }}>
            <div className={styles.modalTitle}>Retirer de la liste ?</div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              La transaction ne sera pas supprimée, elle sera simplement retirée du suivi récurrent.
            </p>
            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setDeleteId(null)}>Annuler</button>
              <button
                className={styles.btnDanger}
                onClick={() => {
                  const txn = confirmed.find(t => t.id === deleteId)
                  if (txn) handleRemoveRecurring(txn)
                }}
              >Retirer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
