import { useState, useEffect, useRef } from 'react'
import { Bell } from 'lucide-react'
import { notificationsAPI } from '../../services/api'
import styles from './NotificationBell.module.css'

interface Notification {
  id: number
  type: string
  severity: 'green' | 'orange' | 'red'
  message: string
  read: boolean
  created_at: string
}

const SEVERITY_COLOR: Record<string, string> = {
  green: '#4ade80',
  orange: '#fb923c',
  red: '#f87171',
}

function timeAgo(dateStr: string): string {
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000
  if (diff < 60) return 'à l\'instant'
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`
  return `il y a ${Math.floor(diff / 86400)} j`
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unread, setUnread] = useState(0)
  const ref = useRef<HTMLDivElement>(null)

  const fetchUnread = async () => {
    try {
      const { data } = await notificationsAPI.unreadCount()
      setUnread(data.count)
    } catch {
      // silent
    }
  }

  const fetchNotifications = async () => {
    try {
      const { data } = await notificationsAPI.list()
      setNotifications(data.results ?? data)
    } catch {
      // silent
    }
  }

  useEffect(() => {
    fetchUnread()
    const interval = setInterval(fetchUnread, 30_000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (open) fetchNotifications()
  }, [open])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const markRead = async (id: number) => {
    await notificationsAPI.markRead(id)
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
    setUnread((c) => Math.max(0, c - 1))
  }

  const markAllRead = async () => {
    await notificationsAPI.markAllRead()
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    setUnread(0)
  }

  return (
    <div className={styles.wrapper} ref={ref}>
      <button
        className={styles.bell}
        onClick={() => setOpen((v) => !v)}
        title="Notifications"
        aria-label="Notifications"
      >
        <Bell size={18} strokeWidth={1.75} />
        {unread > 0 && (
          <span className={styles.badge}>{unread > 99 ? '99+' : unread}</span>
        )}
      </button>

      {open && (
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Notifications</span>
            {unread > 0 && (
              <button className={styles.markAll} onClick={markAllRead}>
                Tout lire
              </button>
            )}
          </div>

          <div className={styles.list}>
            {notifications.length === 0 ? (
              <div className={styles.empty}>Aucune notification</div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`${styles.item} ${n.read ? styles.read : ''}`}
                  onClick={() => !n.read && markRead(n.id)}
                >
                  <span
                    className={styles.dot}
                    style={{ background: SEVERITY_COLOR[n.severity] ?? '#fb923c' }}
                  />
                  <div className={styles.itemBody}>
                    <p className={styles.itemMsg}>{n.message}</p>
                    <span className={styles.itemTime}>{timeAgo(n.created_at)}</span>
                  </div>
                  {!n.read && <span className={styles.unreadDot} />}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
