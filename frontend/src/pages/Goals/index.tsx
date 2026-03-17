import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { goalsAPI } from '../../services/api'
import Modal from '../../components/Modal/Modal'
import ProgressBar from '../../components/ProgressBar/ProgressBar'
import ConfettiCelebration from '../../components/ConfettiCelebration/ConfettiCelebration'
import type { Goal, CashFlowMonth } from '../../types'
import styles from './Goals.module.css'

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

export default function Goals() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [cashflow, setCashflow] = useState<CashFlowMonth[]>([])
  const [horizon, setHorizon] = useState('')
  const [type, setType] = useState('')
  const [contribute, setContribute] = useState<Goal | null>(null)
  const [amount, setAmount] = useState('')
  const [confetti, setConfetti] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newGoal, setNewGoal] = useState({ name: '', type: 'savings', target_amount: '', current_amount: '0', deadline: '', icon: '🎯', color: '#a855f7' })

  const load = () => {
    goalsAPI.list({ horizon: horizon || undefined, type: type || undefined }).then(r => setGoals(r.data.results ?? r.data))
  }

  useEffect(() => { load() }, [horizon, type])
  useEffect(() => { goalsAPI.cashflow(24).then(r => setCashflow(r.data)).catch(() => {}) }, [])

  const doContribute = async () => {
    if (!contribute) return
    const a = parseFloat(amount)
    if (!a) return
    const { data } = await goalsAPI.contribute(contribute.id, a)
    if (data.progress >= 100) setConfetti(true)
    setContribute(null)
    setAmount('')
    load()
  }

  const doAdd = async () => {
    await goalsAPI.create({ ...newGoal, target_amount: parseFloat(newGoal.target_amount), current_amount: parseFloat(newGoal.current_amount) })
    setShowAdd(false)
    load()
  }

  const cashflowData = cashflow.map(m => ({ month: m.month.slice(5), solde: m.running_balance, alert: m.alert }))

  return (
    <div className={styles.page}>
      <ConfettiCelebration trigger={confetti} />
      <div className={styles.header}>
        <h1 className={styles.title}>Objectifs</h1>
        <button className={styles.btnPrimary} onClick={() => setShowAdd(true)}>+ Objectif</button>
      </div>

      {/* Filters */}
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

      {/* Goal cards */}
      <div className={styles.grid}>
        <AnimatePresence>
          {goals.map(g => {
            const target = parseFloat(g.target_amount)
            const current = parseFloat(g.current_amount)
            return (
              <motion.div key={g.id} className={styles.card} layout
                initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                style={{ '--gc': g.color, '--hc': HORIZON_COLORS[g.horizon] } as React.CSSProperties}
              >
                <div className={styles.cardHeader}>
                  <span className={styles.cardIcon} style={{ background: `${g.color}22`, color: g.color }}>{g.icon}</span>
                  <div className={styles.cardMeta}>
                    <div className={styles.cardName}>{g.name}</div>
                    <div className={styles.cardBadges}>
                      <span className={styles.horizonBadge} style={{ background: `${HORIZON_COLORS[g.horizon]}22`, color: HORIZON_COLORS[g.horizon] }}>{g.horizon}</span>
                      <span className={styles.typeBadge}>{g.type === 'savings' ? '💰 Épargne' : '📅 Dépense'}</span>
                    </div>
                  </div>
                </div>
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
          <div className={styles.field}><label>Montant (€)</label>
            <input type="number" step="0.01" className={styles.input} value={amount} onChange={e => setAmount(e.target.value)} placeholder="100" />
          </div>
          <button className={styles.btnPrimary} style={{ width: '100%' }} onClick={doContribute}>Confirmer le versement</button>
        </div>
      </Modal>

      {/* Add goal modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Nouvel objectif">
        <div className={styles.form}>
          {[
            { label: 'Nom', key: 'name', type: 'text', placeholder: 'Vacances été' },
            { label: 'Montant cible (€)', key: 'target_amount', type: 'number', placeholder: '1500' },
            { label: 'Montant actuel (€)', key: 'current_amount', type: 'number', placeholder: '0' },
            { label: 'Deadline', key: 'deadline', type: 'date', placeholder: '' },
            { label: 'Icône', key: 'icon', type: 'text', placeholder: '🎯' },
          ].map(f => (
            <div key={f.key} className={styles.field}><label>{f.label}</label>
              <input type={f.type} className={styles.input} placeholder={f.placeholder}
                value={(newGoal as any)[f.key]}
                onChange={e => setNewGoal(prev => ({ ...prev, [f.key]: e.target.value }))} />
            </div>
          ))}
          <div className={styles.field}><label>Type</label>
            <select className={styles.input} value={newGoal.type} onChange={e => setNewGoal(p => ({ ...p, type: e.target.value }))}>
              <option value="savings">Épargne</option>
              <option value="expense">Dépense future</option>
            </select>
          </div>
          <button className={styles.btnPrimary} style={{ width: '100%' }} onClick={doAdd}>Créer l'objectif</button>
        </div>
      </Modal>
    </div>
  )
}
