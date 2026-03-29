import { useState, useEffect, useRef, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { reconciliationAPI, transactionsAPI } from '../../services/api'
import type { ReconciliationSession, ReconciliationEntry, Transaction } from '../../types'
import styles from './Reconciliation.module.css'

const STATUS_LABELS: Record<string, string> = {
  auto: 'Auto',
  manual: 'Manuel',
  unmatched_app: 'Manquant banque',
  unmatched_bank: 'Manquant app',
}

const STATUS_CLASS: Record<string, string> = {
  auto: styles.statusAuto,
  manual: styles.statusManual,
  unmatched_app: styles.statusUnmatchedApp,
  unmatched_bank: styles.statusUnmatchedBank,
}

function fmt(amount: string | null) {
  if (!amount) return '—'
  return `${parseFloat(amount).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`
}

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

interface ManualMatchState {
  sessionId: number
  entryId: number
  bankLabel: string
  bankAmount: string | null
}

export default function Reconciliation() {
  const [month, setMonth] = useState(currentMonth())
  const [csvContent, setCsvContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessions, setSessions] = useState<ReconciliationSession[]>([])
  const [activeSession, setActiveSession] = useState<ReconciliationSession | null>(null)
  const [manualMatch, setManualMatch] = useState<ManualMatchState | null>(null)
  const [allTxns, setAllTxns] = useState<Transaction[]>([])
  const [txnSearch, setTxnSearch] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [droppedFile, setDroppedFile] = useState<string | null>(null)
  const [showPaste, setShowPaste] = useState(false)

  const onDrop = useCallback((files: File[]) => {
    const file = files[0]
    if (!file) return
    setDroppedFile(file.name)
    const reader = new FileReader()
    reader.onload = ev => setCsvContent(ev.target?.result as string || '')
    reader.readAsText(file, 'utf-8')
  }, [])

  useEffect(() => {
    reconciliationAPI.list().then(r => {
      setSessions(r.data.results ?? r.data)
    }).catch(() => {})
  }, [])

  async function handleStart() {
    if (!csvContent.trim()) { setError('Collez le CSV bancaire ci-dessous.'); return }
    setError('')
    setLoading(true)
    try {
      const { data } = await reconciliationAPI.start(month, csvContent)
      setActiveSession(data)
      setSessions(prev => {
        const without = prev.filter(s => s.id !== data.id)
        return [data, ...without]
      })
    } catch (e: any) {
      setError(e.response?.data?.error || 'Erreur lors du démarrage.')
    } finally {
      setLoading(false)
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => setCsvContent(ev.target?.result as string || '')
    reader.readAsText(file, 'utf-8')
  }

  async function handleIgnore(entry: ReconciliationEntry) {
    if (!activeSession) return
    try {
      const { data } = await reconciliationAPI.ignoreEntry(activeSession.id, entry.id)
      setActiveSession(data)
    } catch {}
  }

  async function handleClose() {
    if (!activeSession) return
    try {
      const { data } = await reconciliationAPI.close(activeSession.id)
      setActiveSession(data)
      setSessions(prev => prev.map(s => s.id === data.id ? data : s))
    } catch (e: any) {
      setError(e.response?.data?.error || 'Clôture impossible.')
    }
  }

  async function openManualMatch(entry: ReconciliationEntry) {
    if (!activeSession) return
    setTxnSearch('')
    setManualMatch({ sessionId: activeSession.id, entryId: entry.id, bankLabel: entry.bank_label, bankAmount: entry.bank_amount })
    if (allTxns.length === 0) {
      const { data } = await transactionsAPI.list({ month, type: 'expense,saving', page_size: 200 })
      setAllTxns(data.results ?? data)
    }
  }

  async function doManualMatch(txn: Transaction) {
    if (!manualMatch) return
    try {
      const { data } = await reconciliationAPI.matchManual(manualMatch.sessionId, manualMatch.entryId, txn.id)
      setActiveSession(data)
      setManualMatch(null)
    } catch (e: any) {
      setError(e.response?.data?.error || 'Erreur matching manuel.')
    }
  }

  const filteredTxns = allTxns.filter(t =>
    t.label.toLowerCase().includes(txnSearch.toLowerCase()) ||
    t.amount.includes(txnSearch)
  )

  const unmatched = activeSession?.entries.filter(e => e.status === 'unmatched_app' || e.status === 'unmatched_bank') ?? []

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'text/csv': ['.csv'], 'text/plain': ['.txt'] },
    maxFiles: 1,
    onDrop,
  })

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Réconciliation bancaire</h1>
      </div>

      {/* Setup */}
      <div className={styles.setupCard}>
        <div className={styles.setupRow}>
          <div className={styles.field}>
            <span className={styles.label}>Mois</span>
            <input
              type="month"
              className={styles.input}
              value={month}
              onChange={e => setMonth(e.target.value)}
            />
          </div>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`${styles.dropzone} ${isDragActive ? styles.dragActive : ''} ${droppedFile ? styles.dropzoneReady : ''}`}
        >
          <input {...getInputProps()} />
          {droppedFile ? (
            <div className={styles.dropReady}>
              <span className={styles.dropIcon}>✅</span>
              <div>
                <div className={styles.dropFileName}>{droppedFile}</div>
                <div className={styles.dropHint}>{csvContent.split('\n').filter(Boolean).length} lignes chargées · Glissez un autre fichier pour remplacer</div>
              </div>
              <button className={styles.btnGhost} onClick={e => { e.stopPropagation(); setDroppedFile(null); setCsvContent('') }}>✕</button>
            </div>
          ) : (
            <>
              <span className={styles.dropIcon}>📄</span>
              <div>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>Glissez votre relevé CSV ici</div>
                <div className={styles.dropHint}>ou cliquez pour choisir — Format : Date ; Libellé ; Montant</div>
              </div>
            </>
          )}
        </div>

        {/* Paste fallback */}
        <button className={styles.pasteToggle} onClick={() => setShowPaste(p => !p)}>
          {showPaste ? '▲ Masquer' : '▼ Coller le CSV manuellement'}
        </button>
        {showPaste && (
          <div className={styles.field} style={{ marginBottom: '0.5rem' }}>
            <textarea
              className={styles.textarea}
              placeholder={`Date;Libellé;Montant\n01/03/2025;AMAZON PRIME;-8.99\n03/03/2025;CARREFOUR;-42.30`}
              value={csvContent}
              onChange={e => { setCsvContent(e.target.value); setDroppedFile(null) }}
            />
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button className={styles.btnPrimary} onClick={handleStart} disabled={loading}>
            {loading ? 'Analyse en cours…' : 'Démarrer la réconciliation'}
          </button>
          {error && <span className={styles.error}>{error}</span>}
        </div>
      </div>

      {/* Previous sessions */}
      {sessions.length > 0 && !activeSession && (
        <div>
          <div className={styles.label} style={{ marginBottom: '0.5rem' }}>Sessions précédentes</div>
          <div className={styles.sessionsList}>
            {sessions.map(s => (
              <div
                key={s.id}
                className={`${styles.sessionItem} ${activeSession && (activeSession as ReconciliationSession).id === s.id ? styles.sessionItemActive : ''}`}
                onClick={() => { setActiveSession(s); setMonth(s.month) }}
              >
                <div>
                  <span style={{ fontWeight: 600, marginRight: '0.75rem' }}>{s.month}</span>
                  <span className={`${styles.badge} ${s.status === 'open' ? styles.badgeOpen : styles.badgeClosed}`}>
                    {s.status === 'open' ? 'Ouverte' : 'Clôturée'}
                  </span>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {s.stats.matched_pct}% réconcilié · {s.stats.total} entrées
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active session results */}
      {activeSession && (
        <>
          <div className={styles.sessionHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontWeight: 700, fontSize: '1rem' }}>{activeSession.month}</span>
              <span className={`${styles.badge} ${activeSession.status === 'open' ? styles.badgeOpen : styles.badgeClosed}`}>
                {activeSession.status === 'open' ? 'Ouverte' : 'Clôturée'}
              </span>
              <button className={styles.btnGhost} onClick={() => setActiveSession(null)}>← Retour</button>
            </div>
            {activeSession.status === 'open' && (
              <button
                className={styles.btnDanger}
                onClick={handleClose}
                disabled={unmatched.length > 0}
                title={unmatched.length > 0 ? `${unmatched.length} entrée(s) non réconciliée(s)` : ''}
              >
                Clôturer le mois
              </button>
            )}
          </div>

          {/* Stats */}
          <div className={styles.statsBar}>
            <div className={styles.stat}>
              <div className={styles.statValue}>{activeSession.stats.total}</div>
              <div className={styles.statLabel}>Total</div>
            </div>
            <div className={`${styles.stat} ${styles.statGreen}`}>
              <div className={styles.statValue}>{activeSession.stats.matched_pct}%</div>
              <div className={styles.statLabel}>Réconcilié</div>
            </div>
            <div className={`${styles.stat} ${styles.statGreen}`}>
              <div className={styles.statValue}>{activeSession.stats.auto}</div>
              <div className={styles.statLabel}>Auto</div>
            </div>
            <div className={styles.stat}>
              <div className={styles.statValue}>{activeSession.stats.manual}</div>
              <div className={styles.statLabel}>Manuel</div>
            </div>
            <div className={`${styles.stat} ${unmatched.length > 0 ? styles.statRed : ''}`}>
              <div className={styles.statValue}>{unmatched.length}</div>
              <div className={styles.statLabel}>Non réconcilié</div>
            </div>
          </div>

          {/* Entries table */}
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Statut</th>
                  <th>Date banque</th>
                  <th>Libellé banque</th>
                  <th>Montant banque</th>
                  <th>Transaction app</th>
                  <th>Score</th>
                  {activeSession.status === 'open' && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {activeSession.entries.map(entry => (
                  <tr key={entry.id}>
                    <td>
                      <span className={`${styles.statusBadge} ${STATUS_CLASS[entry.status]}`}>
                        {STATUS_LABELS[entry.status]}
                      </span>
                    </td>
                    <td>{entry.bank_date ?? '—'}</td>
                    <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {entry.bank_label || '—'}
                    </td>
                    <td style={{ fontWeight: 600, color: entry.bank_amount && parseFloat(entry.bank_amount) < 0 ? '#ef4444' : '#22c55e' }}>
                      {fmt(entry.bank_amount)}
                    </td>
                    <td>
                      {entry.transaction_detail ? (
                        <div className={styles.appTxn}>
                          <span className={styles.appLabel}>{entry.transaction_detail.label}</span>
                          <span className={styles.appMeta}>
                            {entry.transaction_detail.date} · {fmt(entry.transaction_detail.amount)}
                          </span>
                        </div>
                      ) : '—'}
                    </td>
                    <td className={styles.score}>
                      {entry.match_score > 0 ? `${(entry.match_score * 100).toFixed(0)}%` : '—'}
                    </td>
                    {activeSession.status === 'open' && (
                      <td>
                        {(entry.status === 'unmatched_bank' || entry.status === 'unmatched_app') && (
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            {entry.status === 'unmatched_bank' && (
                              <button className={styles.btnGhost} onClick={() => openManualMatch(entry)}>
                                Lier
                              </button>
                            )}
                            <button className={styles.btnGhost} onClick={() => handleIgnore(entry)}>
                              Ignorer
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Manual match modal */}
      {manualMatch && (
        <div className={styles.modalOverlay} onClick={() => setManualMatch(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalTitle}>
              Lier manuellement — {manualMatch.bankLabel} ({fmt(manualMatch.bankAmount)})
            </div>
            <input
              type="text"
              className={styles.modalSearch}
              placeholder="Rechercher une transaction…"
              value={txnSearch}
              onChange={e => setTxnSearch(e.target.value)}
              autoFocus
            />
            <div className={styles.txnList}>
              {filteredTxns.map(t => (
                <div key={t.id} className={styles.txnOption} onClick={() => doManualMatch(t)}>
                  <div className={styles.txnOptionInfo}>
                    <span className={styles.txnOptionLabel}>{t.label}</span>
                    <span className={styles.txnOptionDate}>{t.date} · {t.category_detail?.name ?? 'Sans catégorie'}</span>
                  </div>
                  <span className={styles.txnOptionAmount}>{fmt(t.amount)}</span>
                </div>
              ))}
              {filteredTxns.length === 0 && (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1.5rem' }}>
                  Aucune transaction trouvée
                </div>
              )}
            </div>
            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setManualMatch(null)}>Annuler</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
