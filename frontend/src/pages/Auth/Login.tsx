import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../../context/AuthContext'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import styles from './Auth.module.css'

const schema = z.object({
  username: z.string().min(1, 'Requis'),
  password: z.string().min(1, 'Requis'),
})
type Form = z.infer<typeof schema>

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [err, setErr] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: Form) => {
    try {
      setErr('')
      await login(data.username, data.password)
      nav('/')
    } catch {
      setErr('Identifiants incorrects.')
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logo}>💰 Budget Master</div>
        <h1 className={styles.title}>Connexion</h1>
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <div className={styles.field}>
            <label>Nom d'utilisateur</label>
            <input {...register('username')} placeholder="demo" />
            {errors.username && <span className={styles.error}>{errors.username.message}</span>}
          </div>
          <div className={styles.field}>
            <label>Mot de passe</label>
            <input type="password" {...register('password')} placeholder="••••••" />
            {errors.password && <span className={styles.error}>{errors.password.message}</span>}
          </div>
          {err && <div className={styles.serverError}>{err}</div>}
          <button type="submit" className={styles.btn} disabled={isSubmitting}>
            {isSubmitting ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>
        <p className={styles.link}>Pas de compte ? <Link to="/register">S'inscrire</Link></p>
        <p className={styles.hint}>Démo : demo / demo1234</p>
      </div>
    </div>
  )
}
