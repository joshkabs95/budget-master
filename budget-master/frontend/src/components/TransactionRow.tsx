import React from 'react';
import { Transaction } from '../types';

interface Props {
  transaction: Transaction;
  onDelete?: (id: number) => void;
}

const fmt = (amount: number) =>
  amount.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

const TransactionRow: React.FC<Props> = ({ transaction: t, onDelete }) => {
  const isIncome = t.type === 'income';
  const isSaving = t.type === 'saving';
  const color = isIncome ? 'var(--accent-green)' : isSaving ? 'var(--accent-blue)' : 'var(--accent-red)';

  return (
    <tr>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: `${color}22`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '16px',
          }}>
            {t.category?.icon || (isIncome ? '💰' : isSaving ? '🏦' : '💸')}
          </span>
          <div>
            <div style={{ fontWeight: 500 }}>{t.label}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {t.category?.name || 'Sans catégorie'}
            </div>
          </div>
        </div>
      </td>
      <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
        {new Date(t.date).toLocaleDateString('fr-FR')}
      </td>
      <td>
        <span style={{
          padding: '3px 10px',
          borderRadius: '20px',
          fontSize: '12px',
          background: isIncome ? 'rgba(34,197,94,0.1)' : isSaving ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)',
          color,
        }}>
          {isIncome ? 'Revenu' : isSaving ? 'Épargne' : 'Dépense'}
        </span>
      </td>
      <td style={{ fontWeight: 600, color, textAlign: 'right' }}>
        {isIncome ? '+' : '-'}{fmt(Number(t.amount))}
      </td>
      {onDelete && (
        <td style={{ textAlign: 'right' }}>
          <button
            className="btn-ghost"
            style={{ padding: '4px 8px', fontSize: '16px' }}
            onClick={() => onDelete(t.id)}
          >
            🗑️
          </button>
        </td>
      )}
    </tr>
  );
};

export default TransactionRow;
