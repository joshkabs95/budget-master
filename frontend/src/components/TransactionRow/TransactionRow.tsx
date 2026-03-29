import type { Transaction } from '../../types'
import styles from './TransactionRow.module.css'

interface Props {
  transaction: Transaction
  onDelete?: (id: number) => void
  onEdit?: (t: Transaction) => void
  bulkMode?: boolean
  bulkChecked?: boolean
  onBulkToggle?: () => void
}

const TYPE_COLORS = { income: 'var(--accent-green)', expense: 'var(--accent-red)', saving: 'var(--accent-blue)' }
const RECURRENCE_LABEL = { monthly: 'mensuel', weekly: 'hebdo', yearly: 'annuel' }

export default function TransactionRow({ transaction: t, onDelete, onEdit, bulkMode, bulkChecked, onBulkToggle }: Props) {
  const amount = parseFloat(t.amount)
  const formatted = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount)

  return (
    <div className={`${styles.row} ${bulkMode && bulkChecked ? styles.rowSelected : ''}`} onClick={bulkMode ? onBulkToggle : undefined} style={bulkMode ? { cursor: 'pointer' } : undefined}>
      {bulkMode && (
        <input type="checkbox" checked={!!bulkChecked} onChange={() => {}} className={styles.bulkCheck} onClick={e => e.stopPropagation()} />
      )}
      <div className={styles.icon} style={{ background: `${t.category_detail?.color ?? '#6b6b7e'}22`, color: t.category_detail?.color ?? '#6b6b7e' }}>
        {t.category_detail?.icon ?? (t.type === 'saving' ? '🏦' : '💳')}
      </div>
      <div className={styles.info}>
        <div className={styles.labelRow}>
          <span className={styles.label}>{t.label}</span>
          {t.is_recurring && (
            <span className={styles.recurBadge}>
              ↻ {t.recurrence ? RECURRENCE_LABEL[t.recurrence] : 'récurrent'}
            </span>
          )}
          {t.notes && <span className={styles.noteIcon} title={t.notes}>📝</span>}
        </div>
        <div className={styles.meta}>
          {t.category_detail?.name ?? (t.type === 'saving' ? 'Épargne' : 'Autre')} · {new Date(t.date).toLocaleDateString('fr-FR')}
        </div>
      </div>
      <div className={styles.amount} style={{ color: TYPE_COLORS[t.type] }}>
        {t.type === 'income' ? '+' : '-'}{formatted}
      </div>
      {!bulkMode && onEdit && (
        <button className={styles.edit} onClick={() => onEdit(t)}>✎</button>
      )}
      {!bulkMode && onDelete && (
        <button className={styles.del} onClick={() => onDelete(t.id)}>✕</button>
      )}
    </div>
  )
}
