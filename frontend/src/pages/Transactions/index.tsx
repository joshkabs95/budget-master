import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { useForm } from 'react-hook-form'
import { transactionsAPI, categoriesAPI, savingsAPI, documentsAPI } from '../../services/api'
import TransactionRow from '../../components/TransactionRow/TransactionRow'
import Modal from '../../components/Modal/Modal'
import type { Transaction, Category, SavingsAccount, ParsedTransaction } from '../../types'
import styles from './Transactions.module.css'

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

export default function Transactions() {
  const [txns, setTxns] = useState<Transaction[]>([])
  const [cats, setCats] = useState<Category[]>([])
  const [accounts, setAccounts] = useState<SavingsAccount[]>([])
  const [month, setMonth] = useState(currentMonth)
  const [monthReady, setMonthReady] = useState(false)
  const [filterCat, setFilterCat] = useState('')
  const [filterType, setFilterType] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [parsed, setParsed] = useState<ParsedTransaction[]>([])
  const [docId, setDocId] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [importing, setImporting] = useState(false)

  const { register, handleSubmit, reset } = useForm()

  const load = useCallback(() => {
    if (!monthReady) return
    transactionsAPI.list({ month, category: filterCat || undefined, type: filterType || undefined })
      .then(r => setTxns(r.data.results ?? r.data))
  }, [month, filterCat, filterType, monthReady])

  useEffect(() => { load() }, [load])
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
  }, [])

  const onAdd = async (data: any) => {
    await transactionsAPI.create({ ...data, amount: parseFloat(data.amount) })
    reset()
    setShowAdd(false)
    load()
  }

  const onDelete = async (id: number) => {
    await transactionsAPI.delete(id)
    load()
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'], 'text/csv': ['.csv'] },
    onDrop: async (files) => {
      const file = files[0]
      if (!file) return
      const { data } = await documentsAPI.upload(file)
      const { data: preview } = await documentsAPI.preview(data.id)
      setDocId(data.id)
      setParsed(preview.transactions)
      setSelected(new Set(preview.transactions.filter((t: ParsedTransaction) => !t.is_duplicate).map((_: any, i: number) => i)))
    },
  })

  const doImport = async () => {
    if (!docId) return
    setImporting(true)
    const toImport = parsed.filter((_, i) => selected.has(i))
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
          <button className={styles.btnSecondary} onClick={() => setShowImport(true)}>📥 Importer</button>
          <button className={styles.btnPrimary} onClick={() => setShowAdd(true)}>+ Ajouter</button>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
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
      </div>

      {/* List */}
      <div className={styles.list}>
        {txns.length > 0
          ? txns.map(t => <TransactionRow key={t.id} transaction={t} onDelete={onDelete} />)
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
          <div className={styles.field}><label>Compte épargne (si saving)</label>
            <select {...register('savings_account')} className={styles.input}>
              <option value="">— Aucun —</option>
              {accounts.map(a => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
            </select>
          </div>
          <button type="submit" className={styles.btnPrimary} style={{ width: '100%', marginTop: '0.5rem' }}>Ajouter</button>
        </form>
      </Modal>

      {/* Import modal */}
      <Modal open={showImport} onClose={() => setShowImport(false)} title="Importer un relevé" width={680}>
        {parsed.length === 0 ? (
          <div {...getRootProps()} className={`${styles.dropzone} ${isDragActive ? styles.dragActive : ''}`}>
            <input {...getInputProps()} />
            <span className={styles.dropIcon}>📂</span>
            <p>Glissez votre relevé PDF ou CSV ici</p>
            <p className={styles.dropHint}>ou cliquez pour choisir un fichier</p>
          </div>
        ) : (
          <div>
            <div className={styles.importHeader}>
              <span>{parsed.length} transactions détectées · {parsed.filter(t => t.is_duplicate).length} doublons</span>
              <button className={styles.btnSecondary} onClick={() => setSelected(new Set(parsed.filter(t => !t.is_duplicate).map((_, i) => i)))}>Tout sélectionner</button>
            </div>
            <div className={styles.importList}>
              {parsed.map((t, i) => (
                <label key={i} className={`${styles.importRow} ${t.is_duplicate ? styles.duplicate : ''}`}>
                  <input type="checkbox" checked={selected.has(i)} disabled={t.is_duplicate}
                    onChange={e => {
                      const s = new Set(selected)
                      e.target.checked ? s.add(i) : s.delete(i)
                      setSelected(s)
                    }} />
                  <span className={styles.importDate}>{t.date}</span>
                  <span className={styles.importLabel}>{t.label}</span>
                  <span className={styles.importAmt}>{t.amount.toFixed(2)} €</span>
                  <span className={styles.importCat}>{t.suggested_category}</span>
                  {t.is_duplicate && <span className={styles.dupBadge}>doublon</span>}
                </label>
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
