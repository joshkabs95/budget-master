import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard, ArrowLeftRight, PieChart,
  Wallet, TrendingUp, Target, LogOut
} from 'lucide-react'
import styles from './Sidebar.module.css'

const NAV = [
  { to: '/',             icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/transactions', icon: ArrowLeftRight,  label: 'Transactions' },
  { to: '/budget',       icon: PieChart,        label: 'Budget' },
  { to: '/savings',      icon: Wallet,          label: 'Épargne' },
  { to: '/analytics',    icon: TrendingUp,      label: 'Analytics' },
  { to: '/goals',        icon: Target,          label: 'Objectifs' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div className={styles.brandMark}>B</div>
        <span className={styles.brandName}>Budget<strong>Master</strong></span>
      </div>

      <nav className={styles.nav}>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            <Icon size={18} strokeWidth={1.75} className={styles.navIcon} />
            <span className={styles.navLabel}>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className={styles.footer}>
        <div className={styles.user}>
          <div className={styles.avatar}>{user?.username?.[0]?.toUpperCase()}</div>
          <div className={styles.userInfo}>
            <div className={styles.username}>{user?.first_name || user?.username}</div>
            <div className={styles.userSub}>Compte personnel</div>
          </div>
        </div>
        <button className={styles.logout} onClick={logout} title="Déconnexion">
          <LogOut size={16} strokeWidth={1.75} />
        </button>
      </div>
    </aside>
  )
}
