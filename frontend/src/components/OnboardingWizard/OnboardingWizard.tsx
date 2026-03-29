import { useState } from 'react'
import { authAPI } from '../../services/api'
import styles from './OnboardingWizard.module.css'

interface Props {
  onDone: () => void
}

const STEPS = ['Bienvenue', 'Règle budgétaire', 'Première catégorie']

export default function OnboardingWizard({ onDone }: Props) {
  const [step, setStep] = useState(0)
  const [income, setIncome] = useState('')
  const [needs, setNeeds] = useState(50)
  const [wants, setWants] = useState(30)
  const [savings, setSavings] = useState(20)
  const [catName, setCatName] = useState('')
  const [saving, setSaving] = useState(false)

  const total = needs + wants + savings
  const totalOk = Math.abs(total - 100) <= 0.1

  function adjustSavings(n: number, w: number) {
    const s = Math.max(0, 100 - n - w)
    setNeeds(n); setWants(w); setSavings(s)
  }

  async function finish() {
    setSaving(true)
    try {
      await authAPI.completeOnboarding({
        monthly_income: parseFloat(income) || 0,
        needs_pct: needs,
        wants_pct: wants,
        savings_pct: savings,
        first_category: catName.trim(),
      })
      onDone()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.wizard}>
        {/* Progress */}
        <div className={styles.progress}>
          {STEPS.map((s, i) => (
            <div key={i} className={`${styles.step} ${i === step ? styles.stepActive : ''} ${i < step ? styles.stepDone : ''}`}>
              <div className={styles.stepDot}>{i < step ? '✓' : i + 1}</div>
              <span className={styles.stepLabel}>{s}</span>
            </div>
          ))}
        </div>

        {/* Step 0 — Bienvenue */}
        {step === 0 && (
          <div className={styles.body}>
            <div className={styles.emoji}>👋</div>
            <h2 className={styles.title}>Bienvenue sur Budget Master</h2>
            <p className={styles.hint}>Configurons votre espace en 2 minutes. Quel est votre revenu mensuel net ?</p>
            <div className={styles.field}>
              <label className={styles.label}>Revenu mensuel net (€)</label>
              <input
                className={styles.input}
                type="number"
                placeholder="ex: 2500"
                value={income}
                onChange={e => setIncome(e.target.value)}
                autoFocus
              />
            </div>
            <div className={styles.footer}>
              <button className={styles.btnSkip} onClick={() => setStep(1)}>Passer</button>
              <button className={styles.btnNext} onClick={() => setStep(1)}>Suivant →</button>
            </div>
          </div>
        )}

        {/* Step 1 — Règle 50/30/20 */}
        {step === 1 && (
          <div className={styles.body}>
            <div className={styles.emoji}>⚖️</div>
            <h2 className={styles.title}>Votre règle budgétaire</h2>
            <p className={styles.hint}>La règle 50/30/20 est un bon point de départ. Ajustez selon vos besoins.</p>

            {([
              { label: 'Besoins', color: '#60A5FA', val: needs, set: (v: number) => adjustSavings(v, wants) },
              { label: 'Envies',  color: '#A78BFA', val: wants, set: (v: number) => adjustSavings(needs, v) },
              { label: 'Épargne', color: '#34D399', val: savings, set: () => {} },
            ] as const).map(({ label, color, val, set }) => (
              <div key={label} className={styles.ruleRow}>
                <span className={styles.ruleLabel} style={{ color }}>{label}</span>
                <input
                  type="range" min={0} max={100} step={1}
                  value={val}
                  className={styles.slider}
                  style={{ accentColor: color }}
                  onChange={e => set(Number(e.target.value))}
                  disabled={label === 'Épargne'}
                />
                <span className={styles.rulePct} style={{ color }}>{val}%</span>
              </div>
            ))}

            <div className={styles.ruleBar}>
              <div style={{ width: `${needs}%`, background: '#60A5FA' }} />
              <div style={{ width: `${wants}%`, background: '#A78BFA' }} />
              <div style={{ width: `${savings}%`, background: '#34D399' }} />
            </div>
            <div className={styles.totalHint} style={{ color: totalOk ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              Total : {total}% {totalOk ? '✓' : '(doit faire 100%)'}
            </div>

            <div className={styles.footer}>
              <button className={styles.btnBack} onClick={() => setStep(0)}>← Retour</button>
              <button className={styles.btnNext} onClick={() => setStep(2)} disabled={!totalOk}>Suivant →</button>
            </div>
          </div>
        )}

        {/* Step 2 — Première catégorie */}
        {step === 2 && (
          <div className={styles.body}>
            <div className={styles.emoji}>🏷️</div>
            <h2 className={styles.title}>Votre première catégorie</h2>
            <p className={styles.hint}>Créez une catégorie pour classifier vos dépenses (ex: Alimentation, Loyer…)</p>
            <div className={styles.field}>
              <label className={styles.label}>Nom de la catégorie</label>
              <input
                className={styles.input}
                type="text"
                placeholder="ex: Alimentation"
                value={catName}
                onChange={e => setCatName(e.target.value)}
                autoFocus
              />
            </div>
            <div className={styles.footer}>
              <button className={styles.btnBack} onClick={() => setStep(1)}>← Retour</button>
              <button className={styles.btnNext} onClick={finish} disabled={saving}>
                {saving ? 'Enregistrement…' : "C'est parti ! 🚀"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
