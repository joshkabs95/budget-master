import { useEffect, useState } from 'react'
import { authAPI, savingsAPI } from '../../services/api'
import styles from './Profile.module.css'

interface Rule {
  id?: number
  needs_target: number
  wants_target: number
  savings_target: number
  needs_tolerance: number
  wants_tolerance: number
  savings_tolerance: number
  mode: 'strict' | 'adaptive'
  window_months: number
  catchup_max_months: number
}

const DEFAULT_RULE: Rule = {
  needs_target: 50, wants_target: 30, savings_target: 20,
  needs_tolerance: 5, wants_tolerance: 5, savings_tolerance: 5,
  mode: 'adaptive', window_months: 3, catchup_max_months: 3,
}

function sum3(a: number, b: number, c: number) { return a + b + c }

export default function Profile() {
  const [profile, setProfile] = useState({ username: '', email: '', first_name: '', last_name: '' })
  const [profileSaved, setProfileSaved] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)

  const [rule, setRule] = useState<Rule>(DEFAULT_RULE)
  const [ruleSaved, setRuleSaved] = useState(false)
  const [ruleSaving, setRuleSaving] = useState(false)
  const [ruleError, setRuleError] = useState('')

  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' })
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState<{ text: string; ok: boolean } | null>(null)

  useEffect(() => {
    authAPI.profile().then((r: any) => setProfile(r.data)).catch(() => {})
    savingsAPI.rule.get().then((r: any) => {
      const d = r.data
      setRule({
        ...d,
        needs_target:      Number(d.needs_target),
        wants_target:      Number(d.wants_target),
        savings_target:    Number(d.savings_target),
        needs_tolerance:   Number(d.needs_tolerance),
        wants_tolerance:   Number(d.wants_tolerance),
        savings_tolerance: Number(d.savings_tolerance),
      })
    }).catch(() => {})
  }, [])

  async function saveProfile() {
    setProfileSaving(true)
    try {
      await authAPI.profile_update({ username: profile.username, email: profile.email })
      setProfileSaved(true)
      setTimeout(() => setProfileSaved(false), 2500)
    } finally {
      setProfileSaving(false)
    }
  }

  async function saveRule() {
    const total = sum3(rule.needs_target, rule.wants_target, rule.savings_target)
    if (Math.abs(total - 100) > 0.1) {
      setRuleError(`Les cibles doivent totaliser 100% (actuellement ${total}%)`)
      return
    }
    setRuleError('')
    setRuleSaving(true)
    try {
      await savingsAPI.rule.save(rule)
      setRuleSaved(true)
      setTimeout(() => setRuleSaved(false), 2500)
    } finally {
      setRuleSaving(false)
    }
  }

  function setTarget(key: 'needs_target' | 'wants_target' | 'savings_target', val: number) {
    setRule(r => {
      const updated = { ...r, [key]: val }
      const total = sum3(updated.needs_target, updated.wants_target, updated.savings_target)
      return { ...updated, _total: total } as any
    })
    setRuleError('')
  }

  const total = sum3(rule.needs_target, rule.wants_target, rule.savings_target)
  const totalOk = Math.abs(total - 100) <= 0.1

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Profil & Paramètres</h1>
      </div>

      {/* Profil utilisateur */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Compte</h2>
        <div className={styles.fields}>
          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Nom d'utilisateur</label>
              <input className={styles.input} value={profile.username}
                onChange={e => setProfile(p => ({ ...p, username: e.target.value }))} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Email</label>
              <input className={styles.input} type="email" value={profile.email}
                onChange={e => setProfile(p => ({ ...p, email: e.target.value }))} />
            </div>
          </div>
          <div className={styles.fieldActions}>
            <button className={styles.btnSave} onClick={saveProfile} disabled={profileSaving}>
              {profileSaved ? '✓ Sauvegardé' : profileSaving ? 'Sauvegarde…' : 'Enregistrer'}
            </button>
          </div>
        </div>
      </section>

      {/* Règle 50/30/20 */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Règle personnalisée</h2>
        <p className={styles.hint}>Ajuste les cibles selon ta situation. La somme des 3 cibles doit faire 100%.</p>

        <div className={styles.ruleGrid}>
          {([
            { key: 'needs_target',   label: 'Besoins',  color: '#60A5FA', tolKey: 'needs_tolerance'   },
            { key: 'wants_target',   label: 'Envies',   color: '#A78BFA', tolKey: 'wants_tolerance'   },
            { key: 'savings_target', label: 'Épargne',  color: '#34D399', tolKey: 'savings_tolerance' },
          ] as const).map(({ key, label, color, tolKey }) => (
            <div key={key} className={styles.ruleCard} style={{ '--rc': color } as any}>
              <div className={styles.ruleCardHeader}>
                <span className={styles.ruleCardLabel} style={{ color }}>{label}</span>
                <span className={styles.ruleCardPct} style={{ color }}>{Number(rule[key]).toFixed(0)}%</span>
              </div>
              <input
                type="range" min={0} max={100} step={1}
                value={rule[key]}
                className={styles.slider}
                style={{ accentColor: color }}
                onChange={e => setTarget(key, Number(e.target.value))}
              />
              <div className={styles.tolRow}>
                <span className={styles.tolLabel}>Tolérance</span>
                <div className={styles.tolInputWrap}>
                  <input
                    type="number" min={0} max={20} step={0.5}
                    className={styles.tolInput}
                    value={rule[tolKey]}
                    onChange={e => setRule(r => ({ ...r, [tolKey]: Number(e.target.value) }))}
                  />
                  <span className={styles.tolUnit}>%</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Total indicator */}
        <div className={styles.totalRow}>
          <span className={styles.totalLabel}>Total</span>
          <span className={styles.totalVal} style={{ color: totalOk ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {total}% {totalOk ? '✓' : `— il manque ${(100 - total).toFixed(0)}%`}
          </span>
        </div>

        {/* Visual bar */}
        <div className={styles.ruleBar}>
          <div style={{ width: `${rule.needs_target}%`, background: '#60A5FA' }} />
          <div style={{ width: `${rule.wants_target}%`, background: '#A78BFA' }} />
          <div style={{ width: `${rule.savings_target}%`, background: '#34D399' }} />
        </div>

        {/* Mode */}
        <div className={styles.modeRow}>
          <span className={styles.label}>Mode</span>
          <div className={styles.toggle}>
            {(['strict', 'adaptive'] as const).map(m => (
              <button key={m}
                className={`${styles.toggleBtn} ${rule.mode === m ? styles.toggleActive : ''}`}
                onClick={() => setRule(r => ({ ...r, mode: m }))}>
                {m === 'strict' ? 'Fixe' : 'Adaptatif'}
              </button>
            ))}
          </div>
          {rule.mode === 'adaptive' && (
            <span className={styles.modeHint}>Lissage sur
              <input type="number" min={1} max={12} className={styles.inlineNum}
                value={rule.window_months}
                onChange={e => setRule(r => ({ ...r, window_months: Number(e.target.value) }))} />
              mois
            </span>
          )}
        </div>

        {ruleError && <div className={styles.error}>{ruleError}</div>}

        <div className={styles.fieldActions}>
          <button className={styles.btnSave} onClick={saveRule} disabled={ruleSaving || !totalOk}>
            {ruleSaved ? '✓ Sauvegardé' : ruleSaving ? 'Sauvegarde…' : 'Enregistrer la règle'}
          </button>
        </div>
      </section>

      {/* Export backup */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Sauvegarde des données</h2>
        <p className={styles.hint}>Télécharge une copie de toutes tes données (transactions, catégories, objectifs) au format JSON.</p>
        <div className={styles.fieldActions}>
          <a
            href="/api/users/export-backup/"
            download
            className={styles.btnSave}
            style={{ display: 'inline-block', textDecoration: 'none', textAlign: 'center' }}
          >
            ⬇ Exporter les données (JSON)
          </a>
        </div>
      </section>

      {/* Password change */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Changer le mot de passe</h2>
        <div className={styles.fields}>
          <div className={styles.field}>
            <label className={styles.label}>Mot de passe actuel</label>
            <input className={styles.input} type="password" value={pwForm.current}
              onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))} autoComplete="current-password" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Nouveau mot de passe</label>
            <input className={styles.input} type="password" value={pwForm.next}
              onChange={e => setPwForm(f => ({ ...f, next: e.target.value }))} autoComplete="new-password" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Confirmer</label>
            <input className={styles.input} type="password" value={pwForm.confirm}
              onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))} autoComplete="new-password" />
          </div>
          {pwMsg && (
            <div style={{ fontSize: '0.82rem', color: pwMsg.ok ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {pwMsg.ok ? '✓ ' : '⚠ '}{pwMsg.text}
            </div>
          )}
        </div>
        <div className={styles.fieldActions}>
          <button
            className={styles.btnSave}
            disabled={pwSaving || !pwForm.current || !pwForm.next || !pwForm.confirm}
            onClick={async () => {
              if (pwForm.next !== pwForm.confirm) { setPwMsg({ text: 'Les mots de passe ne correspondent pas.', ok: false }); return }
              setPwSaving(true); setPwMsg(null)
              try {
                await authAPI.changePassword(pwForm.current, pwForm.next)
                setPwMsg({ text: 'Mot de passe modifié avec succès.', ok: true })
                setPwForm({ current: '', next: '', confirm: '' })
              } catch (e: any) {
                setPwMsg({ text: e.response?.data?.error || 'Erreur.', ok: false })
              } finally { setPwSaving(false) }
            }}
          >{pwSaving ? 'Sauvegarde…' : 'Changer le mot de passe'}</button>
        </div>
      </section>
    </div>
  )
}
