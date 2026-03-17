import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../../context/AuthContext'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import styles from './Auth.module.css'

const schema = z.object({
  username: z.string().min(3, 'Min 3 caractères'),
  email: z.string().email('Email invalide'),
  password: z.string().min(6, 'Min 6 caractères'),
})
type Form = z.infer<typeof schema>

export default function Register() {
  const { register: regFn } = useAuth()
  const nav = useNavigate()
  const [err, setErr] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: Form) => {
    try {
      setErr('')
      await regFn(data.username, data.email, data.password)
      nav('/')
    } catch (e: any) {
      setErr(e?.response?.data?.username?.[0] ?? "Erreur lors de l'inscription.")
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logo}>
          <div className={styles.logoMark}>B</div>
          <span className={styles.logoText}>Budget<strong>Master</strong></span>
        </div>
        <h1 className={styles.title}>Créer un compte</h1>
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <div className={styles.field}>
            <label>Nom d'utilisateur</label>
            <input {...register('username')} placeholder="jdupont" />
            {errors.username && <span className={styles.error}>{errors.username.message}</span>}
          </div>
          <div className={styles.field}>
            <label>Email</label>
            <input type="email" {...register('email')} placeholder="jean@example.fr" />
            {errors.email && <span className={styles.error}>{errors.email.message}</span>}
          </div>
          <div className={styles.field}>
            <label>Mot de passe</label>
            <input type="password" {...register('password')} placeholder="••••••" />
            {errors.password && <span className={styles.error}>{errors.password.message}</span>}
          </div>
          {err && <div className={styles.serverError}>{err}</div>}
          <button type="submit" className={styles.btn} disabled={isSubmitting}>
            {isSubmitting ? 'Inscription...' : "S'inscrire"}
          </button>
        </form>
        <p className={styles.link}>Déjà un compte ? <Link to="/login">Se connecter</Link></p>
      </div>
    </div>
  )
}
