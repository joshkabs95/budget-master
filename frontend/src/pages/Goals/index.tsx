import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { goalsAPI, savingsAPI } from '../../services/api'
import Modal from '../../components/Modal/Modal'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import ConfettiCelebration from '../../components/ConfettiCelebration/ConfettiCelebration'
import { useToast } from '../../context/ToastContext'
import type { Goal, SavingsAccount, CashFlowMonth } from '../../types'
import styles from './Goals.module.css'

function goalStatus(g: Goal): { label: string; color: string; bg: string } {
  if (g.progress >= 100) return { label: '✅ Atteint', color: '#22c55e', bg: 'rgba(34,197,94,0.12)' }
  if (g.deadline) {
    const daysLeft = Math.ceil((new Date(g.deadline).getTime() - Date.now()) / 86400000)
    if (daysLeft < 0) return { label: '⚠️ En retard', color: '#ef4444', bg: 'rgba(239,68,68,0.12)' }
    const needed = g.monthly_required
    const target = parseFloat(g.target_amount)
    const current = g.current_amount
    const monthsLeft = daysLeft / 30
    if (needed > 0 && monthsLeft > 0) {
      const projectedShortfall = (target - current) - needed * monthsLeft
      if (projectedShortfall > target * 0.15) return { label: '🟡 À surveiller', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' }
    }
    if (daysLeft < 30) return { label: '⏰ Bientôt', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' }
  }
  return { label: '📈 En cours', color: '#60a5fa', bg: 'rgba(59,130,246,0.12)' }
}

const HORIZONS = [
  { key: '', label: 'Tous' },
  { key: 'short', label: 'Court < 3 mois' },
  { key: 'medium', label: 'Moyen 3-12 mois' },
  { key: 'long', label: 'Long > 12 mois' },
]

const TYPES = [
  { key: '', label: 'Tous' },
  { key: 'savings', label: 'Épargne' },
  { key: 'expense', label: 'Dépenses futures' },
]

const HORIZON_COLORS: Record<string, string> = {
  short: 'var(--accent-orange)',
  medium: 'var(--accent-blue)',
  long: 'var(--accent-purple)',
}

const BLANK_GOAL = { name: '', type: 'savings', target_amount: '', current_amount: '0', deadline: '', icon: '🎯', color: '#a855f7', savings_account: '' }

export default function Goals() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [cashflow, setCashflow] = useState<CashFlowMonth[]>([])
  const [savingsAccounts, setSavingsAccounts] = useState<SavingsAccount[]>([])
  const [horizon, setHorizon] = useState('')
  const [type, setType] = useState('')
  const [contribute, setContribute] = useState<Goal | null>(null)
  const [amount, setAmount] = useState('')
  const [confetti, setConfetti] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newGoal, setNewGoal] = useState({ ...BLANK_GOAL })
  const [editGoal, setEditGoal] = useState<Goal | null>(null)
  const [editForm, setEditForm] = useState({ name: '', type: 'savings', target_amount: '', current_amount: '', deadline: '', icon: '🎯', color: '#a855f7', savings_account: '' })
  const [deleteGoal, setDeleteGoal] = useState<Goal | null>(null)
  const { toast } = useToast()

  const load = () => {
    goalsAPI.list({ horizon: horizon || undefined, type: type || undefined }).then(r => setGoals(r.data.results ?? r.data))
  }

  useEffect(() => { load() }, [horizon, type])
  useEffect(() => { goalsAPI.cashflow(24).then(r => setCashflow(r.data)).catch(() => {}) }, [])
  useEffect(() => { savingsAPI.accounts.list().then(r => setSavingsAccounts(r.data.results ?? r.data)) }, [])

  const doContribute = async () => {
    if (!contribute) return
    const a = parseFloat(amount)
    if (!a) return
    const { data } = await goalsAPI.contribute(contribute.id, a)
    if (data.progress >= 100) {
      setConfetti(true)
      toast(`🎉 Objectif "${contribute.name}" atteint !`)
    } else {
      const accName = contribute.savings_account_detail?.name
      toast(accName ? `+${a.toFixed(0)} € versés sur ${accName}` : `+${a.toFixed(0)} € versés sur "${contribute.name}"`)
    }
    setContribute(null)
    setAmount('')
    load()
  }

  const doAdd = async () => {
    await goalsAPI.create({
      ...newGoal,
      target_amount: parseFloat(newGoal.target_amount),
      current_amount: newGoal.savings_account ? 0 : parseFloat(newGoal.current_amount),
      savings_account: newGoal.savings_account || null,
    })
    setShowAdd(false)
    setNewGoal({ ...BLANK_GOAL })
    toast('Objectif créé')
    load()
  }

  const openEdit = (g: Goal) => {
    setEditGoal(g)
    setEditForm({
      name: g.name,
      type: g.type,
      target_amount: String(parseFloat(g.target_amount)),
      current_amount: String(g.current_amount),
      deadline: g.deadline,
      icon: g.icon,
      color: g.color,
      savings_account: g.savings_account ? String(g.savings_account) : '',
    })
  }

  const doEdit = async () => {
    if (!editGoal) return
    await goalsAPI.update(editGoal.id, {
      ...editForm,
      target_amount: parseFloat(editForm.target_amount),
      current_amount: editForm.savings_account ? 0 : parseFloat(editForm.current_amount),
      savings_account: editForm.savings_account || null,
    })
    setEditGoal(null)
    toast('Objectif modifié')
    load()
  }

  const doDelete = async () => {
    if (!deleteGoal) return
    await goalsAPI.delete(deleteGoal.id)
    setDeleteGoal(null)
    toast('Objectif supprimé', 'info')
    load()
  }

  const cashflowData = cashflow.map(m => ({ month: m.month.slice(5), solde: m.running_balance, alert: m.alert }))

  const GoalFields = ({ form, setForm }: { form: typeof editForm; setForm: (f: typeof editForm) => void }) => (
    <>
      {([
        { label: 'Nom', key: 'name', type: 'text', placeholder: 'Vacances été' },
        { label: 'Montant cible (€)', key: 'target_amount', type: 'number', placeholder: '1500' },
        { label: 'Deadline', key: 'deadline', type: 'date', placeholder: '' },
        { label: 'Icône', key: 'icon', type: 'text', placeholder: '🎯' },
      ] as const).map(f => (
        <div key={f.key} className={styles.field}><label>{f.label}</label>
          <input type={f.type} className={styles.input} placeholder={f.placeholder}
            value={(form as any)[f.key]}
            onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
        </div>
      ))}
      <div className={styles.field}><label>Compte épargne lié (optionnel)</label>
        <select className={styles.input} value={form.savings_account} onChange={e => setForm({ ...form, savings_account: e.target.value })}>
          <option value="">— Aucun (saisie manuelle) —</option>
          {savingsAccounts.map(a => (
            <option key={a.id} value={a.id}>{a.icon} {a.name}</option>
          ))}
        </select>
        {form.savings_account && (
          <span className={styles.accountHint}>La progression sera calculée automatiquement depuis les transactions.</span>
        )}
      </div>
      {!form.savings_account && (
        <div className={styles.field}><label>Montant actuel (€)</label>
          <input type="number" className={styles.input} placeholder="0"
            value={form.current_amount}
            onChange={e => setForm({ ...form, current_amount: e.target.value })} />
        </div>
      )}
      <div className={styles.field}><label>Type</label>
        <select className={styles.input} value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
          <option value="savings">Épargne</option>
          <option value="expense">Dépense future</option>
        </select>
      </div>
      <div className={styles.field}><label>Couleur</label>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <input type="color" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })}
            style={{ width: 40, height: 32, border: 'none', background: 'none', cursor: 'pointer', padding: 0 }} />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{form.color}</span>
        </div>
      </div>
    </>
  )

  return (
    <div className={styles.page}>
      <ConfettiCelebration trigger={confetti} />
      <div className={styles.header}>
        <div className={styles.filters}>
          {HORIZONS.map(h => (
            <button key={h.key} className={`${styles.filter} ${horizon === h.key ? styles.active : ''}`}
              onClick={() => setHorizon(h.key)}>{h.label}</button>
          ))}
          <span className={styles.sep}>|</span>
          {TYPES.map(t => (
            <button key={t.key} className={`${styles.filter} ${type === t.key ? styles.active : ''}`}
              onClick={() => setType(t.key)}>{t.label}</button>
          ))}
        </div>
        <button className={styles.btnPrimary} onClick={() => setShowAdd(true)}>+ Objectif</button>
      </div>

      {/* Goal cards */}
      <div className={styles.grid}>
        <AnimatePresence>
          {goals.map(g => {
            const target = parseFloat(g.target_amount)
            const current = g.current_amount
            return (
              <motion.div key={g.id} className={styles.card} layout
                initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                style={{ '--gc': g.color, '--hc': HORIZON_COLORS[g.horizon] } as React.CSSProperties}
              >
                {/* Edit / delete buttons */}
                <div className={styles.cardActions}>
                  <button className={styles.cardActionBtn} onClick={() => openEdit(g)} title="Modifier">✎</button>
                  <button className={`${styles.cardActionBtn} ${styles.cardActionDel}`} onClick={() => setDeleteGoal(g)} title="Supprimer">✕</button>
                </div>

                <div className={styles.cardHeader}>
                  <span className={styles.cardIcon} style={{ background: `${g.color}22`, color: g.color }}>{g.icon}</span>
                  <div className={styles.cardMeta}>
                    <div className={styles.cardName}>{g.name}</div>
                    <div className={styles.cardBadges}>
                      <span className={styles.horizonBadge} style={{ background: `${HORIZON_COLORS[g.horizon]}22`, color: HORIZON_COLORS[g.horizon] }}>{g.horizon}</span>
                      <span className={styles.typeBadge}>{g.type === 'savings' ? '💰 Épargne' : '📅 Dépense'}</span>
                      {(() => { const s = goalStatus(g); return <span className={styles.statusBadge} style={{ background: s.bg, color: s.color }}>{s.label}</span> })()}
                    </div>
                  </div>
                </div>

                {/* Compte épargne lié */}
                {g.savings_account_detail && (
                  <div className={styles.linkedAccount} style={{ borderColor: `${g.savings_account_detail.color}44` }}>
                    <span>{g.savings_account_detail.icon}</span>
                    <span style={{ color: g.savings_account_detail.color }}>{g.savings_account_detail.name}</span>
                  </div>
                )}

                <div className={styles.cardProgress}>
                  <div className={styles.cardAmounts}>
                    <span style={{ color: g.color }}>{current.toFixed(0)} €</span>
                    <span className={styles.sep2}> / {target.toFixed(0)} €</span>
                  </div>
                  <ProgressBar value={g.progress} color={g.color} showLabel />
                </div>
                <div className={styles.cardFooter}>
                  <div className={styles.cardDeadline}>📅 {new Date(g.deadline).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                  <div className={styles.cardRequired}>{g.monthly_required.toFixed(0)} €/mois requis</div>
                </div>
                {g.progress < 100 && g.months_to_goal != null && (
                  <div className={styles.projection}>
                    {g.months_to_goal === 0
                      ? '✅ Objectif atteint'
                      : `📈 À ce rythme : atteint dans ${g.months_to_goal} mois`}
                  </div>
                )}
                {g.progress < 100 && (
                  <button className={styles.contributeBtn} onClick={() => setContribute(g)}>Verser</button>
                )}
                {g.progress >= 100 && <div className={styles.completed}>✅ Objectif atteint !</div>}
              </motion.div>
            )
          })}
        </AnimatePresence>
        {goals.length === 0 && <div className={styles.empty}>Aucun objectif pour ces filtres.</div>}
      </div>

      {/* Cash flow timeline */}
      {cashflow.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>📊 Cash Flow 24 mois</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={cashflowData} barSize={14}>
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} formatter={(v: number) => `${v.toFixed(0)} €`} />
              <Bar dataKey="solde" radius={[3,3,0,0]}>
                {cashflowData.map((e, i) => <Cell key={i} fill={e.alert ? 'var(--accent-red)' : 'var(--accent-blue)'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {cashflow.some(m => m.alert) && (
            <div className={styles.cashflowAlert}>⚠️ Solde projeté négatif détecté sur certains mois — vérifiez vos dépenses futures planifiées.</div>
          )}
        </section>
      )}

      {/* Contribute modal */}
      <Modal open={!!contribute} onClose={() => setContribute(null)} title={`Verser sur : ${contribute?.name}`}>
        <div className={styles.form}>
          {contribute?.savings_account_detail && (
            <div className={styles.contributeInfo}>
              <span>{contribute.savings_account_detail.icon}</span>
              <span>Crée une transaction épargne sur <strong style={{ color: contribute.savings_account_detail.color }}>{contribute.savings_account_detail.name}</strong></span>
            </div>
          )}
          <div className={styles.field}><label>Montant (€)</label>
            <input type="number" step="0.01" className={styles.input} value={amount} onChange={e => setAmount(e.target.value)} placeholder="100" autoFocus />
          </div>
          <button className={styles.btnPrimary} style={{ width: '100%' }} onClick={doContribute}>Confirmer le versement</button>
        </div>
      </Modal>

      {/* Add goal modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Nouvel objectif">
        <div className={styles.form}>
          <GoalFields form={newGoal as any} setForm={f => setNewGoal(f as any)} />
          <button className={styles.btnPrimary} style={{ width: '100%' }} onClick={doAdd}>Créer l'objectif</button>
        </div>
      </Modal>

      {/* Edit goal modal */}
      <Modal open={!!editGoal} onClose={() => setEditGoal(null)} title="Modifier l'objectif">
        <div className={styles.form}>
          <GoalFields form={editForm} setForm={setEditForm} />
          <button className={styles.btnPrimary} style={{ width: '100%' }} onClick={doEdit}>Sauvegarder</button>
        </div>
      </Modal>

      {/* Delete confirmation modal */}
      <Modal open={!!deleteGoal} onClose={() => setDeleteGoal(null)} title="Supprimer l'objectif">
        <div className={styles.form}>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Supprimer <strong style={{ color: 'var(--text)' }}>{deleteGoal?.icon} {deleteGoal?.name}</strong> ?
            Les transactions liées seront dissociées mais conservées.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button className={styles.btnSecondary} style={{ flex: 1 }} onClick={() => setDeleteGoal(null)}>Annuler</button>
            <button className={styles.btnDanger} style={{ flex: 1 }} onClick={doDelete}>Supprimer</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
