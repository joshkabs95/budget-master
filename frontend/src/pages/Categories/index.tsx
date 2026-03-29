import { useEffect, useState } from 'react'
import { categoriesAPI, categoryRulesAPI } from '../../services/api'
import type { Category } from '../../types'
import styles from './Categories.module.css'

interface CategoryRule {
  id: number
  keyword: string
  category: number
  category_name: string
  category_icon: string
  priority: number
}

const BUCKETS = [
  { key: 'needs',   label: 'Besoins',  color: '#60A5FA' },
  { key: 'wants',   label: 'Envies',   color: '#A78BFA' },
  { key: 'savings', label: 'Épargne',  color: '#34D399' },
] as const

const PRESET_COLORS = [
  '#60A5FA','#F87171','#34D399','#FBBF24','#A78BFA',
  '#F472B6','#FB923C','#E879F9','#38BDF8','#4ADE80',
  '#FCD34D','#818CF8','#2DD4BF','#94A3B8','#6b6b7e',
]

const EMPTY_FORM = { name: '', icon: '📦', color: '#60A5FA', type: 'expense' as 'expense'|'income', rule_bucket: 'wants' as Category['rule_bucket'], budget_limit: '' }

const BUCKET_OPTIONS = [
  { key: 'needs',   label: 'Besoins',  color: '#60A5FA' },
  { key: 'wants',   label: 'Envies',   color: '#A78BFA' },
  { key: 'savings', label: 'Épargne',  color: '#34D399' },
]

export default function Categories() {
  const [categories, setCategories] = useState<Category[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Category | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [dropdownOpen, setDropdownOpen] = useState<number | null>(null)
  const [rules, setRules] = useState<CategoryRule[]>([])
  const [newRuleKeyword, setNewRuleKeyword] = useState('')
  const [newRuleCat, setNewRuleCat] = useState('')
  const [ruleAdding, setRuleAdding] = useState(false)
  const [mergeSource, setMergeSource] = useState<Category | null>(null)
  const [mergeTarget, setMergeTarget] = useState('')
  const [merging, setMerging] = useState(false)

  useEffect(() => { load(); loadRules() }, [])

  useEffect(() => {
    if (dropdownOpen === null) return
    const handler = () => setDropdownOpen(null)
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [dropdownOpen])

  async function changeBucket(cat: Category, bucket: Category['rule_bucket']) {
    setDropdownOpen(null)
    await categoriesAPI.update(cat.id, { ...cat, rule_bucket: bucket })
    setCategories(prev => prev.map(c => c.id === cat.id ? { ...c, rule_bucket: bucket } : c))
  }

  function load() {
    categoriesAPI.list().then(r => setCategories(r.data.results ?? r.data))
  }

  function loadRules() {
    categoryRulesAPI.list().then(r => setRules(r.data.results ?? r.data)).catch(() => {})
  }

  async function addRule() {
    if (!newRuleKeyword.trim() || !newRuleCat) return
    setRuleAdding(true)
    try {
      await categoryRulesAPI.create({ keyword: newRuleKeyword.trim(), category: newRuleCat, priority: 0 })
      setNewRuleKeyword(''); setNewRuleCat('')
      loadRules()
    } finally { setRuleAdding(false) }
  }

  async function deleteRule(id: number) {
    await categoryRulesAPI.delete(id)
    setRules(prev => prev.filter(r => r.id !== id))
  }

  async function doMerge() {
    if (!mergeSource || !mergeTarget) return
    setMerging(true)
    try {
      await categoriesAPI.mergeInto(mergeSource.id, parseInt(mergeTarget))
      setMergeSource(null)
      setMergeTarget('')
      load()
    } finally {
      setMerging(false)
    }
  }

  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setError('')
    setShowModal(true)
  }

  function openEdit(cat: Category) {
    setEditing(cat)
    setForm({
      name: cat.name,
      icon: cat.icon,
      color: cat.color,
      type: cat.type,
      rule_bucket: cat.rule_bucket,
      budget_limit: cat.budget_limit != null ? String(cat.budget_limit) : '',
    })
    setError('')
    setShowModal(true)
  }

  async function handleSave() {
    if (!form.name.trim()) { setError('Le nom est requis.'); return }
    setSaving(true)
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        icon: form.icon,
        color: form.color,
        type: form.type,
        rule_bucket: form.rule_bucket,
        budget_limit: form.budget_limit ? parseFloat(form.budget_limit) : null,
      }
      if (editing) {
        await categoriesAPI.update(editing.id, payload)
      } else {
        await categoriesAPI.create(payload)
      }
      load()
      setShowModal(false)
    } catch (e: any) {
      setError(e.response?.data?.name?.[0] || 'Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    setDeleting(id)
    try {
      await categoriesAPI.delete(id)
      setCategories(prev => prev.filter(c => c.id !== id))
    } catch {
      alert('Impossible de supprimer : des transactions utilisent cette catégorie.')
    } finally {
      setDeleting(null)
    }
  }

  const byBucket = (bucket: string) => categories.filter(c => c.rule_bucket === bucket)
  const incomeCategories = categories.filter(c => c.type === 'income')

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Catégories</h1>
        <button className={styles.btnAdd} onClick={openCreate}>+ Nouvelle catégorie</button>
      </div>

      {(['needs', 'wants', 'savings'] as const).map(bucket => {
        const cats = byBucket(bucket)
        const b = BUCKETS.find(b => b.key === bucket)!
        return (
          <section key={bucket} className={styles.section}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionDot} style={{ background: b.color }} />
              <span className={styles.sectionTitle}>{b.label}</span>
              <span className={styles.sectionCount}>{cats.length}</span>
            </div>
            {cats.length === 0
              ? <div className={styles.empty}>Aucune catégorie</div>
              : <div className={styles.grid}>
                  {cats.map(cat => {
                    const currentBucket = BUCKET_OPTIONS.find(b => b.key === cat.rule_bucket)
                    return (
                      <div key={cat.id} className={styles.card}>
                        <div className={styles.cardIcon} style={{ background: `${cat.color}22`, color: cat.color }}>
                          {cat.icon}
                        </div>
                        <div className={styles.cardInfo}>
                          <div className={styles.cardName}>{cat.name}</div>
                          {cat.budget_limit ? (() => {
                            const spent = (cat as any).month_spending ?? 0
                            const pct = Math.min(100, (spent / cat.budget_limit) * 100)
                            const over = spent > cat.budget_limit
                            return (
                              <div className={styles.budgetProgress}>
                                <div className={styles.budgetBar}>
                                  <div className={styles.budgetFill} style={{ width: `${pct}%`, background: over ? 'var(--accent-red)' : pct > 80 ? 'var(--accent-orange)' : 'var(--accent-green)' }} />
                                </div>
                                <div className={styles.budgetLabel} style={{ color: over ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                                  {spent.toFixed(0)} / {cat.budget_limit} €{over ? ' ⚠' : ''}
                                </div>
                              </div>
                            )
                          })() : null}
                        </div>
                        <div className={styles.cardRight}>
                          <div className={styles.bucketDropWrapper} onClick={e => { e.stopPropagation(); setDropdownOpen(dropdownOpen === cat.id ? null : cat.id) }}>
                            <span className={styles.bucketBadge} style={{ color: currentBucket?.color, borderColor: `${currentBucket?.color}44`, background: `${currentBucket?.color}18` }}>
                              {currentBucket?.label} ▾
                            </span>
                            {dropdownOpen === cat.id && (
                              <div className={styles.bucketMenu} onClick={e => e.stopPropagation()}>
                                {BUCKET_OPTIONS.map(b => (
                                  <div
                                    key={b.key}
                                    className={`${styles.bucketOption} ${cat.rule_bucket === b.key ? styles.bucketOptionActive : ''}`}
                                    style={cat.rule_bucket === b.key ? { color: b.color } : {}}
                                    onClick={() => changeBucket(cat, b.key as Category['rule_bucket'])}
                                  >
                                    <span className={styles.bucketOptionDot} style={{ background: b.color }} />
                                    {b.label}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className={styles.cardActions}>
                            <button className={styles.btnEdit} onClick={() => openEdit(cat)} title="Modifier">✎</button>
                            <button className={styles.btnMerge} onClick={() => { setMergeSource(cat); setMergeTarget('') }} title="Fusionner">⇄</button>
                            <button className={styles.btnDelete} onClick={() => handleDelete(cat.id)} disabled={deleting === cat.id} title="Supprimer">✕</button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
            }
          </section>
        )
      })}

      {incomeCategories.length > 0 && (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionDot} style={{ background: '#34D399' }} />
            <span className={styles.sectionTitle}>Revenus</span>
            <span className={styles.sectionCount}>{incomeCategories.length}</span>
          </div>
          <div className={styles.grid}>
            {incomeCategories.map(cat => (
              <div key={cat.id} className={styles.card}>
                <div className={styles.cardIcon} style={{ background: `${cat.color}22`, color: cat.color }}>
                  {cat.icon}
                </div>
                <div className={styles.cardInfo}>
                  <div className={styles.cardName}>{cat.name}</div>
                </div>
                <div className={styles.cardRight}>
                  <div className={styles.cardActions}>
                    <button className={styles.btnEdit} onClick={() => openEdit(cat)} title="Modifier">✎</button>
                    <button className={styles.btnMerge} onClick={() => { setMergeSource(cat); setMergeTarget('') }} title="Fusionner">⇄</button>
                    <button className={styles.btnDelete} onClick={() => handleDelete(cat.id)} disabled={deleting === cat.id} title="Supprimer">✕</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Auto-catégorisation rules */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionDot} style={{ background: '#f59e0b' }} />
          <span className={styles.sectionTitle}>Règles d'auto-catégorisation</span>
          <span className={styles.sectionCount}>{rules.length}</span>
        </div>
        <div className={styles.rulesInfo}>
          Si un libellé contient le mot-clé, la catégorie est assignée automatiquement à l'import.
        </div>
        <div className={styles.ruleAddRow}>
          <input
            className={styles.ruleInput}
            placeholder='Mot-clé (ex: "carrefour")'
            value={newRuleKeyword}
            onChange={e => setNewRuleKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addRule()}
          />
          <select className={styles.ruleSelect} value={newRuleCat} onChange={e => setNewRuleCat(e.target.value)}>
            <option value="">Choisir une catégorie…</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
          </select>
          <button className={styles.btnAdd} onClick={addRule} disabled={ruleAdding || !newRuleKeyword.trim() || !newRuleCat}>
            + Ajouter
          </button>
        </div>
        {rules.length > 0 && (
          <div className={styles.ruleList}>
            {rules.map(r => (
              <div key={r.id} className={styles.ruleRow}>
                <span className={styles.ruleKeyword}>"{r.keyword}"</span>
                <span className={styles.ruleArrow}>→</span>
                <span className={styles.ruleCat}>{r.category_icon} {r.category_name}</span>
                <button className={styles.ruleDelete} onClick={() => deleteRule(r.id)}>✕</button>
              </div>
            ))}
          </div>
        )}
        {rules.length === 0 && <div className={styles.empty}>Aucune règle — les règles génériques s'appliquent</div>}
      </section>

      {/* Modal */}
      {showModal && (
        <div className={styles.overlay} onClick={() => setShowModal(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <span className={styles.modalTitle}>{editing ? 'Modifier la catégorie' : 'Nouvelle catégorie'}</span>
              <button className={styles.modalClose} onClick={() => setShowModal(false)}>✕</button>
            </div>

            <div className={styles.fields}>
              {/* Icon + Name row */}
              <div className={styles.row}>
                <div className={styles.field} style={{ width: 72 }}>
                  <label className={styles.label}>Icône</label>
                  <input
                    className={styles.inputIcon}
                    value={form.icon}
                    onChange={e => setForm(f => ({ ...f, icon: e.target.value }))}
                    maxLength={4}
                  />
                </div>
                <div className={styles.field} style={{ flex: 1 }}>
                  <label className={styles.label}>Nom</label>
                  <input
                    className={styles.input}
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Ex: Alimentation"
                    autoFocus
                  />
                </div>
              </div>

              {/* Color */}
              <div className={styles.field}>
                <label className={styles.label}>Couleur</label>
                <div className={styles.colorGrid}>
                  {PRESET_COLORS.map(c => (
                    <button
                      key={c}
                      className={`${styles.colorDot} ${form.color === c ? styles.colorDotActive : ''}`}
                      style={{ background: c }}
                      onClick={() => setForm(f => ({ ...f, color: c }))}
                    />
                  ))}
                </div>
              </div>

              {/* Type */}
              <div className={styles.field}>
                <label className={styles.label}>Type</label>
                <div className={styles.toggle}>
                  {(['expense', 'income'] as const).map(t => (
                    <button
                      key={t}
                      className={`${styles.toggleBtn} ${form.type === t ? styles.toggleActive : ''}`}
                      onClick={() => setForm(f => ({ ...f, type: t }))}
                    >
                      {t === 'expense' ? 'Dépense' : 'Revenu'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Bucket (only for expenses) */}
              {form.type === 'expense' && (
                <div className={styles.field}>
                  <label className={styles.label}>Bucket 50/30/20</label>
                  <div className={styles.toggle}>
                    {BUCKETS.map(b => (
                      <button
                        key={b.key}
                        className={`${styles.toggleBtn} ${form.rule_bucket === b.key ? styles.toggleActive : ''}`}
                        style={form.rule_bucket === b.key ? { borderColor: b.color, color: b.color } : {}}
                        onClick={() => setForm(f => ({ ...f, rule_bucket: b.key }))}
                      >
                        {b.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Budget limit */}
              <div className={styles.field}>
                <label className={styles.label}>Limite mensuelle (optionnel)</label>
                <input
                  className={styles.input}
                  type="number"
                  value={form.budget_limit}
                  onChange={e => setForm(f => ({ ...f, budget_limit: e.target.value }))}
                  placeholder="Ex: 300"
                />
              </div>

              {error && <div className={styles.error}>{error}</div>}
            </div>

            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setShowModal(false)}>Annuler</button>
              <button className={styles.btnSave} onClick={handleSave} disabled={saving}>
                {saving ? 'Sauvegarde…' : editing ? 'Enregistrer' : 'Créer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge modal */}
      {mergeSource && (
        <div className={styles.overlay} onClick={() => setMergeSource(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <span className={styles.modalTitle}>Fusionner « {mergeSource.icon} {mergeSource.name} »</span>
              <button className={styles.modalClose} onClick={() => setMergeSource(null)}>✕</button>
            </div>
            <div className={styles.fields}>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', lineHeight: 1.5 }}>
                Toutes les transactions de <strong style={{ color: 'var(--text-primary)' }}>{mergeSource.name}</strong> seront
                réassignées vers la catégorie cible, puis <strong style={{ color: 'var(--accent-red)' }}>{mergeSource.name}</strong> sera supprimée.
              </p>
              <div className={styles.field}>
                <label className={styles.label}>Fusionner dans…</label>
                <select className={styles.input} value={mergeTarget} onChange={e => setMergeTarget(e.target.value)}>
                  <option value="">Choisir une catégorie…</option>
                  {categories.filter(c => c.id !== mergeSource.id).map(c => (
                    <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className={styles.modalFooter}>
              <button className={styles.btnGhost} onClick={() => setMergeSource(null)}>Annuler</button>
              <button
                className={styles.btnSave}
                style={{ background: 'var(--accent-red)', borderColor: 'var(--accent-red)' }}
                onClick={doMerge}
                disabled={!mergeTarget || merging}
              >
                {merging ? 'Fusion…' : 'Fusionner et supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
