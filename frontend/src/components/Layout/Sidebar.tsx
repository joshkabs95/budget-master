import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import styles from './Sidebar.module.css'

const NAV = [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/transactions', icon: '💳', label: 'Transactions' },
  { to: '/budget', icon: '⚖️', label: 'Budget' },
  { to: '/savings', icon: '🏦', label: 'Épargne' },
  { to: '/analytics', icon: '📈', label: 'Analytics' },
  { to: '/goals', icon: '🎯', label: 'Objectifs' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <span className={styles.brandIcon}>💰</span>
        <span className={styles.brandName}>Budget Master</span>
      </div>
      <nav className={styles.nav}>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            <span className={styles.navIcon}>{item.icon}</span>
            <span className={styles.navLabel}>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className={styles.footer}>
        <div className={styles.user}>
          <div className={styles.avatar}>{user?.username?.[0]?.toUpperCase()}</div>
          <span className={styles.username}>{user?.username}</span>
        </div>
        <button className={styles.logout} onClick={logout}>Déconnexion</button>
      </div>
    </aside>
  )
}
