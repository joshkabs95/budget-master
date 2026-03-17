import type { Transaction } from '../../types'
import styles from './TransactionRow.module.css'

interface Props {
  transaction: Transaction
  onDelete?: (id: number) => void
}

const TYPE_ICONS = { income: '↑', expense: '↓', saving: '🏦' }
const TYPE_COLORS = { income: 'var(--accent-green)', expense: 'var(--accent-red)', saving: 'var(--accent-blue)' }

export default function TransactionRow({ transaction: t, onDelete }: Props) {
  const sign = t.type === 'income' ? '+' : '-'
  const amount = parseFloat(t.amount)
  const formatted = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount)

  return (
    <div className={styles.row}>
      <div className={styles.icon} style={{ background: `${t.category_detail?.color ?? '#6b6b7e'}22`, color: t.category_detail?.color ?? '#6b6b7e' }}>
        {t.category_detail?.icon ?? (t.type === 'saving' ? '🏦' : '💳')}
      </div>
      <div className={styles.info}>
        <div className={styles.label}>{t.label}</div>
        <div className={styles.meta}>
          {t.category_detail?.name ?? (t.type === 'saving' ? 'Épargne' : 'Autre')} · {new Date(t.date).toLocaleDateString('fr-FR')}
        </div>
      </div>
      <div className={styles.amount} style={{ color: TYPE_COLORS[t.type] }}>
        {t.type === 'income' ? '+' : '-'}{formatted}
      </div>
      {onDelete && (
        <button className={styles.del} onClick={() => onDelete(t.id)}>✕</button>
      )}
    </div>
  )
}
