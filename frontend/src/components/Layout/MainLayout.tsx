import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import BottomNav from './BottomNav'
import OnboardingWizard from '../OnboardingWizard/OnboardingWizard'
import { useAuth } from '../../context/AuthContext'
import styles from './MainLayout.module.css'

export default function MainLayout() {
  const { user, isLoading } = useAuth()
  const [wizardDone, setWizardDone] = useState(false)

  const showWizard = !isLoading && user && !user.onboarding_done && !wizardDone

  return (
    <div className={styles.layout}>
      <Sidebar />
      <main className={styles.main}>
        <Outlet />
      </main>
      <BottomNav />
      {showWizard && <OnboardingWizard onDone={() => setWizardDone(true)} />}
    </div>
  )
}
