import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ArrowLeftRight, PieChart, Wallet, Target } from 'lucide-react'
import styles from './BottomNav.module.css'

const NAV = [
  { to: '/',             icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/transactions', icon: ArrowLeftRight,  label: 'Transactions' },
  { to: '/budget',       icon: PieChart,        label: 'Budget' },
  { to: '/savings',      icon: Wallet,          label: 'Épargne' },
  { to: '/goals',        icon: Target,          label: 'Objectifs' },
]

export default function BottomNav() {
  return (
    <nav className={styles.nav}>
      {NAV.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `${styles.item} ${isActive ? styles.active : ''}`}
        >
          <Icon size={22} strokeWidth={1.75} className={styles.icon} />
          <span className={styles.label}>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
