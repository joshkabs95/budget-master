import { useEffect, useState } from 'react'
import { notificationsAPI } from '../../services/api'
import styles from './Notifications.module.css'

interface Notification {
  id: number
  type: string
  severity: 'green' | 'orange' | 'red'
  message: string
  read: boolean
  created_at: string
}

const SEV_COLOR = { green: '#4ade80', orange: '#fb923c', red: '#f87171' }
const SEV_LABEL = { green: 'Info', orange: 'Alerte', red: 'Urgent' }

function timeAgo(d: string) {
  const diff = (Date.now() - new Date(d).getTime()) / 1000
  if (diff < 60) return "à l'instant"
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`
  if (diff < 86400 * 7) return `il y a ${Math.floor(diff / 86400)} j`
  return new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Notifications() {
  const [notifs, setNotifs] = useState<Notification[]>([])
  const [filter, setFilter] = useState<'all' | 'unread' | 'green' | 'orange' | 'red'>('all')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const { data } = await notificationsAPI.list()
      setNotifs(data.results ?? data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function markRead(id: number) {
    await notificationsAPI.markRead(id)
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }

  async function markAllRead() {
    await notificationsAPI.markAllRead()
    setNotifs(prev => prev.map(n => ({ ...n, read: true })))
  }

  const filtered = notifs.filter(n => {
    if (filter === 'unread') return !n.read
    if (filter === 'all') return true
    return n.severity === filter
  })

  const unreadCount = notifs.filter(n => !n.read).length

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Notifications</h1>
        {unreadCount > 0 && (
          <button className={styles.btnMarkAll} onClick={markAllRead}>
            Tout marquer comme lu ({unreadCount})
          </button>
        )}
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        {(['all', 'unread', 'green', 'orange', 'red'] as const).map(f => (
          <button
            key={f}
            className={`${styles.filterBtn} ${filter === f ? styles.filterActive : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'Toutes' : f === 'unread' ? `Non lues (${unreadCount})` : SEV_LABEL[f]}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className={styles.empty}>Chargement…</div>
      ) : filtered.length === 0 ? (
        <div className={styles.empty}>Aucune notification</div>
      ) : (
        <div className={styles.list}>
          {filtered.map(n => (
            <div
              key={n.id}
              className={`${styles.item} ${!n.read ? styles.unread : ''}`}
              onClick={() => !n.read && markRead(n.id)}
            >
              <span className={styles.dot} style={{ background: SEV_COLOR[n.severity] }} />
              <div className={styles.body}>
                <div className={styles.message}>{n.message}</div>
                <div className={styles.meta}>
                  <span className={styles.sevBadge} style={{ color: SEV_COLOR[n.severity], borderColor: `${SEV_COLOR[n.severity]}44` }}>
                    {SEV_LABEL[n.severity]}
                  </span>
                  <span className={styles.time}>{timeAgo(n.created_at)}</span>
                </div>
              </div>
              {!n.read && <span className={styles.unreadDot} />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
