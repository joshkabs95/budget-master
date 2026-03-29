import { useEffect, useState } from 'react'
import { accountsAPI } from '../../services/api'
import type { BankAccount } from '../../types'
import Modal from '../../components/Modal/Modal'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import styles from './Accounts.module.css'

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  checking: 'Compte courant',
  joint: 'Compte joint',
  pro: 'Compte professionnel',
  other: 'Autre',
}

const COLORS = ['#00D4AA', '#60A5FA', '#A78BFA', '#F59E0B', '#F87171', '#34D399']
const ICONS = ['🏦', '💳', '🏧', '💰', '🏠', '💼', '🌍']

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#1e2235', border: '1px solid #3a3f5c', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: '#f1f5f9', fontWeight: 600, marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: '#cbd5e1' }}>
          <span style={{ color: p.color }}>■</span> {p.name} : {Number(p.value).toFixed(0)} €
        </div>
      ))}
    </div>
  )
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<BankAccount[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<BankAccount | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [form, setForm] = useState({
    name: '', bank_name: '', account_type: 'checking',
    initial_balance: 0, color: COLORS[0], icon: '🏦', is_default: false,
  })
  const [saving, setSaving] = useState(false)
  const [totalBalance, setTotalBalance] = useState(0)

  const load = () => {
    accountsAPI.list().then(r => {
      const data: BankAccount[] = r.data.results ?? r.data
      setAccounts(data)
    })
    accountsAPI.summary().then(r => setTotalBalance(r.data.total_balance))
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!selectedId) return
    accountsAPI.history(selectedId).then(r => setHistory(r.data))
  }, [selectedId])

  const openCreate = () => {
    setEditing(null)
    setForm({ name: '', bank_name: '', account_type: 'checking', initial_balance: 0, color: COLORS[0], icon: '🏦', is_default: false })
    setShowModal(true)
  }

  const openEdit = (acc: BankAccount) => {
    setEditing(acc)
    setForm({
      name: acc.name, bank_name: acc.bank_name, account_type: acc.account_type,
      initial_balance: acc.initial_balance, color: acc.color, icon: acc.icon, is_default: acc.is_default,
    })
    setShowModal(true)
  }

  const submit = async () => {
    setSaving(true)
    try {
      if (editing) {
        await accountsAPI.update(editing.id, form)
      } else {
        await accountsAPI.create(form)
      }
      setShowModal(false)
      load()
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: number) => {
    if (!confirm('Supprimer ce compte ? Les transactions associées seront conservées.')) return
    await accountsAPI.delete(id)
    if (selectedId === id) setSelectedId(null)
    load()
  }

  const selectedAcc = accounts.find(a => a.id === selectedId)

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Comptes bancaires</h1>
          <div className={styles.totalBalance}>
            Solde total : <span style={{ color: totalBalance >= 0 ? '#34d399' : '#f87171' }}>
              {totalBalance.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
            </span>
          </div>
        </div>
        <button className={styles.btnPrimary} onClick={openCreate}>+ Ajouter un compte</button>
      </div>

      {/* Account cards */}
      {accounts.length === 0 ? (
        <div className={styles.empty}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🏦</div>
          <div>Aucun compte bancaire. Ajoutez votre premier compte pour commencer.</div>
        </div>
      ) : (
        <div className={styles.grid}>
          {accounts.map(acc => (
            <div
              key={acc.id}
              className={`${styles.card} ${selectedId === acc.id ? styles.cardActive : ''}`}
              style={{ '--acc-color': acc.color } as any}
              onClick={() => setSelectedId(selectedId === acc.id ? null : acc.id)}
            >
              <div className={styles.cardTop}>
                <div className={styles.cardIcon} style={{ background: `${acc.color}22`, color: acc.color }}>
                  {acc.icon}
                </div>
                <div className={styles.cardActions}>
                  {acc.is_default && <span className={styles.defaultBadge}>défaut</span>}
                  <button className={styles.iconBtn} onClick={e => { e.stopPropagation(); openEdit(acc) }}>✎</button>
                  <button className={styles.iconBtn} onClick={e => { e.stopPropagation(); remove(acc.id) }} style={{ color: '#f87171' }}>✕</button>
                </div>
              </div>
              <div className={styles.cardName}>{acc.name}</div>
              {acc.bank_name && <div className={styles.cardBank}>{acc.bank_name}</div>}
              <div className={styles.cardType}>{ACCOUNT_TYPE_LABELS[acc.account_type]}</div>
              <div className={styles.cardBalance} style={{ color: acc.balance >= 0 ? '#34d399' : '#f87171' }}>
                {acc.balance.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </div>
              <div className={styles.cardTxnCount}>{acc.transaction_count} transaction{acc.transaction_count !== 1 ? 's' : ''}</div>
              <div className={styles.cardAccent} style={{ background: acc.color }} />
            </div>
          ))}
        </div>
      )}

      {/* History chart for selected account */}
      {selectedAcc && history.length > 0 && (
        <div className={styles.chartSection}>
          <div className={styles.chartTitle}>
            {selectedAcc.icon} {selectedAcc.name} — évolution du solde
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={history} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={selectedAcc.color} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={selectedAcc.color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `${v.toFixed(0)} €`} />
              <Tooltip content={ChartTooltip} />
              <Area type="monotone" dataKey="balance" name="Solde" stroke={selectedAcc.color} fill="url(#balGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Create / Edit modal */}
      <Modal open={showModal} onClose={() => setShowModal(false)} title={editing ? 'Modifier le compte' : 'Nouveau compte bancaire'} width={480}>
        <div className={styles.form}>
          <div className={styles.field}>
            <label>Nom du compte *</label>
            <input className={styles.input} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="ex: Compte BNP principal" />
          </div>
          <div className={styles.field}>
            <label>Banque</label>
            <input className={styles.input} value={form.bank_name} onChange={e => setForm(f => ({ ...f, bank_name: e.target.value }))} placeholder="ex: BNP Paribas, Société Générale…" />
          </div>
          <div className={styles.row2}>
            <div className={styles.field}>
              <label>Type</label>
              <select className={styles.input} value={form.account_type} onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))}>
                <option value="checking">Compte courant</option>
                <option value="joint">Compte joint</option>
                <option value="pro">Compte professionnel</option>
                <option value="other">Autre</option>
              </select>
            </div>
            <div className={styles.field}>
              <label>Solde initial (€)</label>
              <input type="number" step="0.01" className={styles.input} value={form.initial_balance}
                onChange={e => setForm(f => ({ ...f, initial_balance: parseFloat(e.target.value) || 0 }))} />
            </div>
          </div>

          <div className={styles.field}>
            <label>Icône</label>
            <div className={styles.iconPicker}>
              {ICONS.map(ic => (
                <button key={ic} className={`${styles.iconOption} ${form.icon === ic ? styles.iconSelected : ''}`}
                  onClick={() => setForm(f => ({ ...f, icon: ic }))}>{ic}</button>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <label>Couleur</label>
            <div className={styles.colorPicker}>
              {COLORS.map(c => (
                <button key={c} className={`${styles.colorDot} ${form.color === c ? styles.colorSelected : ''}`}
                  style={{ background: c }} onClick={() => setForm(f => ({ ...f, color: c }))} />
              ))}
            </div>
          </div>

          <label className={styles.checkRow}>
            <input type="checkbox" checked={form.is_default} onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))} />
            Compte par défaut
          </label>

          <button className={styles.btnPrimary} style={{ width: '100%', marginTop: '0.5rem' }}
            onClick={submit} disabled={saving || !form.name}>
            {saving ? 'Enregistrement…' : (editing ? 'Modifier' : 'Créer le compte')}
          </button>
        </div>
      </Modal>
    </div>
  )
}
