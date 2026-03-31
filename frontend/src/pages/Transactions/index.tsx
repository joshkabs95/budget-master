import { useEffect, useState, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { useForm } from 'react-hook-form'
import { transactionsAPI, categoriesAPI, savingsAPI, documentsAPI, accountsAPI } from '../../services/api'
import TransactionRow from '../../components/TransactionRow/TransactionRow'
import { SkeletonList } from '../../components/Skeleton/Skeleton'
import Modal from '../../components/Modal/Modal'
import { useToast } from '../../context/ToastContext'
import type { Transaction, Category, SavingsAccount, BankAccount, ParsedTransaction } from '../../types'
import styles from './Transactions.module.css'

function downloadCSV(month: string, filterCat: string, filterType: string, search?: string) {
  const params = new URLSearchParams()
  if (month) params.set('month', month)
  if (filterCat) params.set('category', filterCat)
  if (filterType) params.set('type', filterType)
  if (search) params.set('search', search)
  const token = localStorage.getItem('access_token')
  fetch(`/api/transactions/export/?${params}`, { headers: { Authorization: `Bearer ${token}` } })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `transactions_${month || 'all'}.csv`
      a.click()
      URL.revokeObjectURL(url)
    })
}

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

export default function Transactions() {
  const [txns, setTxns] = useState<Transaction[]>([])
  const [cats, setCats] = useState<Category[]>([])
  const [accounts, setAccounts] = useState<SavingsAccount[]>([])
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([])
  const [month, setMonth] = useState(currentMonth)
  const [monthReady, setMonthReady] = useState(false)
  const [filterCat, setFilterCat] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterBankAccount, setFilterBankAccount] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [isRecurring, setIsRecurring] = useState(false)
  const [parsed, setParsed] = useState<ParsedTransaction[]>([])
  const [xlsxExtras, setXlsxExtras] = useState<{ categories: any[]; goals: any[]; scores: Record<string, number> } | null>(null)
  const [docId, setDocId] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [importing, setImporting] = useState(false)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [catOverrides, setCatOverrides] = useState<Record<number, string>>({})
  const [typeOverrides, setTypeOverrides] = useState<Record<number, 'income' | 'expense'>>({})
  const [templateMonth, setTemplateMonth] = useState(currentMonth)
  const [templateLoading, setTemplateLoading] = useState(false)

  const [txnLoading, setTxnLoading] = useState(true)

  const [bulkSelected, setBulkSelected] = useState<Set<number>>(new Set())
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkCat, setBulkCat] = useState('')
  const [bulkLoading, setBulkLoading] = useState(false)

  const { toast } = useToast()
  const [editTxn, setEditTxn] = useState<Transaction | null>(null)
  const [editForm, setEditForm] = useState<Record<string, any>>({})
  const [editRecurring, setEditRecurring] = useState(false)
  const [editRecurrence, setEditRecurrence] = useState('monthly')

  const { register, handleSubmit, reset } = useForm()

  const load = useCallback(() => {
    if (!monthReady) return
    setTxnLoading(true)
    transactionsAPI.list({ month, category: filterCat || undefined, type: filterType || undefined, bank_account: filterBankAccount || undefined, search: search || undefined })
      .then(r => setTxns(r.data.results ?? r.data))
      .finally(() => setTxnLoading(false))
  }, [month, filterCat, filterType, filterBankAccount, search, monthReady])

  useEffect(() => { load() }, [load])

  function handleSearchChange(val: string) {
    setSearchInput(val)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setSearch(val.trim()), 300)
  }

  // Auto-detect most recent month that has transactions
  useEffect(() => {
    transactionsAPI.list({})
      .then(r => {
        const all: Transaction[] = r.data.results ?? r.data
        if (all.length > 0) {
          const d = new Date(all[0].date)
          const m = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
          setMonth(m)
        }
        setMonthReady(true)
      })
      .catch(() => setMonthReady(true))
  }, [])

  useEffect(() => {
    categoriesAPI.list().then(r => setCats(r.data.results ?? r.data))
    savingsAPI.accounts.list().then(r => setAccounts(r.data.results ?? r.data))
    accountsAPI.list().then(r => setBankAccounts(r.data.results ?? r.data))
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return
      if (e.key === 'n' || e.key === 'N') { e.preventDefault(); setShowAdd(true) }
      if (e.key === 'i' || e.key === 'I') { e.preventDefault(); setShowImport(true) }
      if (e.key === 'Escape') { setShowAdd(false); setShowImport(false); setEditTxn(null) }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  const onAdd = async (data: any) => {
    await transactionsAPI.create({
      ...data,
      amount: parseFloat(data.amount),
      is_recurring: isRecurring,
      recurrence: isRecurring ? data.recurrence : '',
    })
    reset()
    setIsRecurring(false)
    setShowAdd(false)
    load()
  }

  const onDelete = async (id: number) => {
    try {
      await transactionsAPI.delete(id)
      toast('Transaction supprimée', 'info')
      load()
    } catch {
      toast('Erreur lors de la suppression', 'error')
    }
  }

  const openEdit = (t: Transaction) => {
    setEditTxn(t)
    setEditRecurring(t.is_recurring)
    setEditRecurrence(t.recurrence || 'monthly')
    setEditForm({
      label: t.label,
      amount: parseFloat(t.amount).toString(),
      date: t.date,
      type: t.type,
      category: t.category?.toString() ?? '',
      savings_account: t.savings_account?.toString() ?? '',
      bank_account: t.bank_account?.toString() ?? '',
      notes: t.notes ?? '',
    })
  }

  const saveEdit = async () => {
    if (!editTxn) return
    await transactionsAPI.patch(editTxn.id, {
      label: editForm.label,
      amount: parseFloat(editForm.amount),
      date: editForm.date,
      type: editForm.type,
      category: editForm.category || null,
      savings_account: editForm.savings_account || null,
      bank_account: editForm.bank_account || null,
      notes: editForm.notes,
      is_recurring: editRecurring,
      recurrence: editRecurring ? editRecurrence : '',
    })
    setEditTxn(null)
    toast('Transaction modifiée')
    load()
  }

  function toggleBulkSelect(id: number) {
    setBulkSelected(prev => {
      const s = new Set(prev)
      s.has(id) ? s.delete(id) : s.add(id)
      return s
    })
  }

  async function bulkDelete() {
    if (!bulkSelected.size) return
    setBulkLoading(true)
    try {
      await Promise.all([...bulkSelected].map(id => transactionsAPI.delete(id)))
      toast(`${bulkSelected.size} transaction(s) supprimée(s)`, 'info')
      setBulkSelected(new Set())
      setBulkMode(false)
      load()
    } finally {
      setBulkLoading(false)
    }
  }

  async function bulkRecategorize() {
    if (!bulkSelected.size || !bulkCat) return
    setBulkLoading(true)
    try {
      await Promise.all([...bulkSelected].map(id => transactionsAPI.patch(id, { category: bulkCat })))
      toast(`${bulkSelected.size} transaction(s) recatégorisée(s)`)
      setBulkSelected(new Set())
      setBulkMode(false)
      setBulkCat('')
      load()
    } finally {
      setBulkLoading(false)
    }
  }

  const downloadTemplate = async () => {
    setTemplateLoading(true)
    try {
      const res = await documentsAPI.downloadTemplate(templateMonth)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `budget_master_seed_${templateMonth}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setTemplateLoading(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    onDrop: async (files) => {
      const file = files[0]
      if (!file) return
      setUploadError(null)
      setUploadLoading(true)
      try {
        const { data } = await documentsAPI.upload(file)
        const { data: preview } = await documentsAPI.preview(data.id)
        if (!preview.transactions?.length) {
          setUploadError('Aucune transaction détectée. Formats acceptés : relevé PDF BNP Paribas, Société Générale, Crédit Agricole, ou export CSV de votre banque (colonnes Date / Libellé / Montant).')
          return
        }
        setDocId(data.id)
        setParsed(preview.transactions)
        setCatOverrides({})
        setTypeOverrides({})
        if (preview.categories?.length || preview.goals?.length || Object.keys(preview.scores || {}).length) {
          setXlsxExtras({ categories: preview.categories || [], goals: preview.goals || [], scores: preview.scores || {} })
        } else {
          setXlsxExtras(null)
        }
        setSelected(new Set(preview.transactions
          .filter((t: ParsedTransaction) => !t.is_duplicate)
          .map((_: any, i: number) => i)))
      } catch (err: any) {
        const msg = err?.response?.data?.detail
          || err?.response?.data?.file?.[0]
          || 'Erreur lors de l\'import. Vérifiez le format du fichier.'
        setUploadError(msg)
      } finally {
        setUploadLoading(false)
      }
    },
  })

  const doImport = async () => {
    if (!docId) return
    setImporting(true)
    const toImport = parsed
      .filter((_, i) => selected.has(i))
      .map((t, i) => ({
        ...t,
        category: catOverrides[i] || t.suggested_category,
        type: typeOverrides[i] || t.type,
      }))
    await documentsAPI.import(docId, toImport)
    setShowImport(false)
    setParsed([])
    setDocId(null)
    load()
    setImporting(false)
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Transactions</h1>
        <div className={styles.actions}>
          <button className={styles.btnSecondary} onClick={() => downloadCSV(month, filterCat, filterType, search)}>📤 Exporter</button>
          <button className={styles.btnSecondary} onClick={() => setShowImport(true)}>📥 Importer</button>
          <button
            className={`${styles.btnSecondary} ${bulkMode ? styles.btnActive : ''}`}
            onClick={() => { setBulkMode(v => !v); setBulkSelected(new Set()) }}
          >{bulkMode ? '✕ Annuler' : '☑ Sélection'}</button>
          <button className={styles.btnPrimary} onClick={() => setShowAdd(true)}>+ Ajouter</button>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}>🔍</span>
          <input
            className={styles.searchInput}
            placeholder="Rechercher…"
            value={searchInput}
            onChange={e => handleSearchChange(e.target.value)}
          />
          {searchInput && (
            <button className={styles.searchClear} onClick={() => { setSearchInput(''); setSearch('') }}>✕</button>
          )}
        </div>
        <input type="month" value={month} onChange={e => setMonth(e.target.value)} className={styles.input} />
        <select value={filterType} onChange={e => setFilterType(e.target.value)} className={styles.input}>
          <option value="">Tous les types</option>
          <option value="income">Revenus</option>
          <option value="expense">Dépenses</option>
          <option value="saving">Épargne</option>
        </select>
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)} className={styles.input}>
          <option value="">Toutes catégories</option>
          {cats.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
        </select>
        {bankAccounts.length > 0 && (
          <select value={filterBankAccount} onChange={e => setFilterBankAccount(e.target.value)} className={styles.input}>
            <option value="">Tous les comptes</option>
            {bankAccounts.map(a => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
          </select>
        )}
      </div>

      {/* Bulk toolbar */}
      {bulkMode && (
        <div className={styles.bulkBar}>
          <span className={styles.bulkCount}>{bulkSelected.size} sélectionnée{bulkSelected.size > 1 ? 's' : ''}</span>
          <button className={styles.btnSecondary} style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
            onClick={() => setBulkSelected(new Set(txns.map(t => t.id)))}>Tout</button>
          <select className={styles.bulkCatSelect} value={bulkCat} onChange={e => setBulkCat(e.target.value)}>
            <option value="">Recatégoriser…</option>
            {cats.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
          </select>
          <button className={styles.btnPrimary} style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
            disabled={!bulkCat || !bulkSelected.size || bulkLoading}
            onClick={bulkRecategorize}>Appliquer</button>
          <button className={styles.btnDanger} style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
            disabled={!bulkSelected.size || bulkLoading}
            onClick={bulkDelete}>🗑 Supprimer</button>
        </div>
      )}

      {/* Totals bar */}
      {txns.length > 0 && (() => {
        const inc  = txns.filter(t => t.type === 'income').reduce((s, t) => s + Number(t.amount), 0)
        const exp  = txns.filter(t => t.type === 'expense').reduce((s, t) => s + Number(t.amount), 0)
        const sav  = txns.filter(t => t.type === 'saving').reduce((s, t) => s + Number(t.amount), 0)
        const bal  = inc - exp - sav
        const fmt  = (v: number) => v.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' €'
        return (
          <div className={styles.totalsBar}>
            {inc > 0 && <span className={styles.totIncome}>↑ {fmt(inc)}</span>}
            {exp > 0 && <span className={styles.totExpense}>↓ {fmt(exp)}</span>}
            {sav > 0 && <span className={styles.totSaving}>◎ {fmt(sav)}</span>}
            <span className={`${styles.totBalance} ${bal >= 0 ? styles.totPos : styles.totNeg}`}>= {bal >= 0 ? '+' : ''}{fmt(bal)}</span>
            <span className={styles.totCount}>{txns.length} opération{txns.length > 1 ? 's' : ''}</span>
          </div>
        )
      })()}

      {/* List */}
      <div className={styles.list}>
        {txnLoading
          ? <SkeletonList count={6} />
          : txns.length > 0
            ? txns.map(t => (
                <TransactionRow
                  key={t.id}
                  transaction={t}
                  onDelete={onDelete}
                  onEdit={openEdit}
                  bulkMode={bulkMode}
                  bulkChecked={bulkSelected.has(t.id)}
                  onBulkToggle={() => toggleBulkSelect(t.id)}
                />
              ))
            : <div className={styles.empty}>Aucune transaction pour ce filtre.</div>
        }
      </div>

      {/* Add modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Nouvelle transaction">
        <form onSubmit={handleSubmit(onAdd)} className={styles.form}>
          <div className={styles.field}><label>Type</label>
            <select {...register('type')} className={styles.input}>
              <option value="expense">Dépense</option>
              <option value="income">Revenu</option>
              <option value="saving">Épargne</option>
            </select>
          </div>
          <div className={styles.field}><label>Libellé</label>
            <input {...register('label')} className={styles.input} required />
          </div>
          <div className={styles.field}><label>Montant (€)</label>
            <input type="number" step="0.01" {...register('amount')} className={styles.input} required />
          </div>
          <div className={styles.field}><label>Date</label>
            <input type="date" defaultValue={today.toISOString().slice(0, 10)} {...register('date')} className={styles.input} required />
          </div>
          <div className={styles.field}><label>Catégorie</label>
            <select {...register('category')} className={styles.input}>
              <option value="">— Aucune —</option>
              {cats.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
            </select>
          </div>
          {bankAccounts.length > 0 && (
            <div className={styles.field}><label>Compte bancaire</label>
              <select {...register('bank_account')} className={styles.input}>
                <option value="">— Aucun —</option>
                {bankAccounts.map(a => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
              </select>
            </div>
          )}
          <div className={styles.field}><label>Compte épargne (si saving)</label>
            <select {...register('savings_account')} className={styles.input}>
              <option value="">— Aucun —</option>
              {accounts.map(a => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
            </select>
          </div>
          <div className={styles.field}>
            <label>
              <input type="checkbox" checked={isRecurring} onChange={e => setIsRecurring(e.target.checked)} style={{ marginRight: '0.5rem' }} />
              Transaction récurrente
            </label>
          </div>
          {isRecurring && (
            <div className={styles.field}><label>Fréquence</label>
              <select {...register('recurrence')} className={styles.input}>
                <option value="monthly">Mensuelle</option>
                <option value="weekly">Hebdomadaire</option>
                <option value="yearly">Annuelle</option>
              </select>
            </div>
          )}
          <div className={styles.field}><label>Notes (optionnel)</label>
            <textarea {...register('notes')} className={styles.input} rows={2} placeholder="Remarques, contexte..." style={{ resize: 'vertical' }} />
          </div>
          <button type="submit" className={styles.btnPrimary} style={{ width: '100%', marginTop: '0.5rem' }}>Ajouter</button>
        </form>
      </Modal>

      {/* Edit modal — full */}
      <Modal open={!!editTxn} onClose={() => setEditTxn(null)} title="Modifier la transaction">
        {editTxn && (
          <div className={styles.form}>
            <div className={styles.field}><label>Libellé</label>
              <input className={styles.input} value={editForm.label ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, label: e.target.value }))} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className={styles.field}><label>Montant (€)</label>
                <input type="number" step="0.01" className={styles.input} value={editForm.amount ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, amount: e.target.value }))} />
              </div>
              <div className={styles.field}><label>Date</label>
                <input type="date" className={styles.input} value={editForm.date ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, date: e.target.value }))} />
              </div>
            </div>
            <div className={styles.field}><label>Type</label>
              <select className={styles.input} value={editForm.type ?? 'expense'} onChange={e => setEditForm((f: any) => ({ ...f, type: e.target.value }))}>
                <option value="expense">Dépense</option>
                <option value="income">Revenu</option>
                <option value="saving">Épargne</option>
              </select>
            </div>
            <div className={styles.field}><label>Catégorie</label>
              <select className={styles.input} value={editForm.category ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, category: e.target.value }))}>
                <option value="">— Aucune —</option>
                {cats.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
              </select>
            </div>
            {bankAccounts.length > 0 && (
              <div className={styles.field}><label>Compte bancaire</label>
                <select className={styles.input} value={editForm.bank_account ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, bank_account: e.target.value }))}>
                  <option value="">— Aucun —</option>
                  {bankAccounts.map(a => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
                </select>
              </div>
            )}
            {editForm.type === 'saving' && (
              <div className={styles.field}><label>Compte épargne</label>
                <select className={styles.input} value={editForm.savings_account ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, savings_account: e.target.value }))}>
                  <option value="">— Aucun —</option>
                  {accounts.map(a => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
                </select>
              </div>
            )}
            <div className={styles.field}><label>Notes</label>
              <textarea className={styles.input} rows={2} style={{ resize: 'vertical' }} value={editForm.notes ?? ''} onChange={e => setEditForm((f: any) => ({ ...f, notes: e.target.value }))} />
            </div>
            <div className={styles.field}>
              <label>
                <input type="checkbox" checked={editRecurring} onChange={e => setEditRecurring(e.target.checked)} style={{ marginRight: '0.5rem' }} />
                Transaction récurrente
              </label>
            </div>
            {editRecurring && (
              <div className={styles.field}><label>Fréquence</label>
                <select value={editRecurrence} onChange={e => setEditRecurrence(e.target.value)} className={styles.input}>
                  <option value="monthly">Mensuelle</option>
                  <option value="weekly">Hebdomadaire</option>
                  <option value="yearly">Annuelle</option>
                </select>
              </div>
            )}
            <button className={styles.btnPrimary} onClick={saveEdit} style={{ width: '100%', marginTop: '0.5rem' }}>Sauvegarder</button>
          </div>
        )}
      </Modal>

      {/* Import modal */}
      <Modal open={showImport} onClose={() => { setShowImport(false); setParsed([]); setDocId(null); setUploadError(null); setUploadLoading(false); setCatOverrides({}); setTypeOverrides({}); setXlsxExtras(null) }} title="Importer un relevé" width={720}>
        {parsed.length === 0 ? (
          <div>
            <div {...getRootProps()} className={`${styles.dropzone} ${isDragActive ? styles.dragActive : ''} ${uploadLoading ? styles.dropzoneLoading : ''}`}>
              <input {...getInputProps()} />
              {uploadLoading
                ? <><span className={styles.dropIcon}>⏳</span><p>Analyse en cours…</p></>
                : <><span className={styles.dropIcon}>📂</span><p>Glissez votre relevé PDF ou CSV ici</p><p className={styles.dropHint}>ou cliquez pour choisir un fichier</p><p className={styles.dropHint} style={{marginTop:'0.25rem',opacity:0.5,fontSize:'0.75rem'}}>Compatibles : BNP · SG · Crédit Agricole · LCL · Boursorama · CSV bancaire</p></>
              }
            </div>
            <div className={styles.templateBox}>
              <div className={styles.templateInfo}>
                <span className={styles.templateIcon}>📥</span>
                <div>
                  <div className={styles.templateTitle}>Modèle Excel à remplir</div>
                  <div className={styles.templateDesc}>Téléchargez, remplissez et réimportez</div>
                </div>
              </div>
              <div className={styles.templateActions}>
                <input
                  type="month"
                  value={templateMonth}
                  onChange={e => setTemplateMonth(e.target.value)}
                  className={styles.templateMonthPicker}
                />
                <button
                  className={styles.btnSecondary}
                  onClick={downloadTemplate}
                  disabled={templateLoading}
                >
                  {templateLoading ? '...' : '⬇ .xlsx'}
                </button>
              </div>
            </div>
            {uploadError && (
              <div style={{ marginTop: '0.75rem', padding: '0.625rem 0.875rem', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '8px', color: '#f87171', fontSize: '0.82rem' }}>
                ⚠️ {uploadError}
              </div>
            )}
          </div>
        ) : (
          <div>
            <div className={styles.importHeader}>
              <span>{parsed.length} transactions détectées · {parsed.filter(t => t.is_duplicate).length} doublons</span>
              <button className={styles.btnSecondary} onClick={() => setSelected(new Set(parsed.filter(t => !t.is_duplicate).map((_, i) => i)))}>Tout sélectionner</button>
            </div>
            {xlsxExtras && (
              <div className={styles.xlsxBanner}>
                🟣 {xlsxExtras.categories.length} catégorie(s)
                {xlsxExtras.goals.length > 0 && ` · 🎯 ${xlsxExtras.goals.length} objectif(s)`}
                {Object.keys(xlsxExtras.scores).length > 0 && ` · ⭐ ${Object.keys(xlsxExtras.scores).length} score(s) wants`}
                {' '}— seront créés automatiquement à l'import
              </div>
            )}
            <div className={styles.importList}>
              {parsed.map((t, i) => (
                <div key={i} className={`${styles.importRow} ${t.is_duplicate ? styles.duplicate : ''}`}>
                  <input type="checkbox" checked={selected.has(i)} disabled={t.is_duplicate}
                    onChange={e => {
                      const s = new Set(selected)
                      e.target.checked ? s.add(i) : s.delete(i)
                      setSelected(s)
                    }} />
                  <span className={styles.importDate}>{t.date}</span>
                  <span className={styles.importLabel}>{t.label}</span>
                  <span className={`${styles.importAmt} ${(typeOverrides[i] || t.type) === 'income' ? styles.amtIncome : styles.amtExpense}`}>
                    {(typeOverrides[i] || t.type) === 'income' ? '+' : '-'}{t.amount.toFixed(2)} €
                  </span>
                  {!t.is_duplicate ? (
                    <>
                      <button
                        className={`${styles.typeToggle} ${(typeOverrides[i] || t.type) === 'income' ? styles.typeIncome : styles.typeExpense}`}
                        onClick={() => setTypeOverrides(prev => ({ ...prev, [i]: (prev[i] || t.type) === 'income' ? 'expense' : 'income' }))}
                        title="Basculer revenu/dépense"
                      >{(typeOverrides[i] || t.type) === 'income' ? '↑' : '↓'}</button>
                      <select
                        className={styles.importCatSelect}
                        value={catOverrides[i] || t.suggested_category}
                        onChange={e => setCatOverrides(prev => ({ ...prev, [i]: e.target.value }))}
                        onClick={e => e.stopPropagation()}
                      >
                        <option value={t.suggested_category}>{t.suggested_category}</option>
                        <option disabled>──────────</option>
                        {cats.map(c => <option key={c.id} value={c.name}>{c.icon} {c.name}</option>)}
                      </select>
                    </>
                  ) : (
                    <span className={styles.dupBadge}>doublon</span>
                  )}
                </div>
              ))}
            </div>
            <button className={styles.btnPrimary} style={{ width: '100%', marginTop: '1rem' }}
              onClick={doImport} disabled={importing || selected.size === 0}>
              {importing ? 'Import...' : `Importer ${selected.size} transaction(s)`}
            </button>
          </div>
        )}
      </Modal>
    </div>
  )
}
