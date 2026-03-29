import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import MainLayout from '../components/Layout/MainLayout'
import Dashboard from '../pages/Dashboard'
import Transactions from '../pages/Transactions'
import Budget from '../pages/Budget'
import Savings from '../pages/Savings'
import Analytics from '../pages/Analytics'
import Reconciliation from '../pages/Reconciliation'
import Categories from '../pages/Categories'
import Accounts from '../pages/Accounts'
import Recurring from '../pages/Recurring'
import Profile from '../pages/Profile'
import Notifications from '../pages/Notifications'
import Login from '../pages/Auth/Login'
import Register from '../pages/Auth/Register'

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--accent-gold)', fontFamily: 'var(--font-display)', fontSize: '1.5rem' }}>Budget Master</div>
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}

function PublicRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return null
  return isAuthenticated ? <Navigate to="/" replace /> : <Outlet />
}

export default function AppRouter() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/budget" element={<Budget />} />
          <Route path="/savings" element={<Savings />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/reconciliation" element={<Reconciliation />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/recurring" element={<Recurring />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/goals" element={<Navigate to="/savings" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
