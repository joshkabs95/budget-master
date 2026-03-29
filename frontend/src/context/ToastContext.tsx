import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

let _nextId = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((message: string, type: ToastType = 'success') => {
    const id = ++_nextId
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3200)
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', zIndex: 9999, pointerEvents: 'none' }}>
        {toasts.map(t => (
          <div
            key={t.id}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.625rem',
              background: t.type === 'error' ? 'rgba(239,68,68,0.95)' : t.type === 'info' ? 'rgba(59,130,246,0.95)' : 'rgba(34,197,94,0.95)',
              color: '#fff', padding: '0.65rem 1rem', borderRadius: '10px',
              fontSize: '0.85rem', fontWeight: 500,
              boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
              animation: 'toastIn 0.2s ease',
              pointerEvents: 'auto',
              maxWidth: '320px',
            }}
          >
            <span>{t.type === 'error' ? '✕' : t.type === 'info' ? 'ℹ' : '✓'}</span>
            {t.message}
          </div>
        ))}
      </div>
      <style>{`@keyframes toastIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }`}</style>
    </ToastContext.Provider>
  )
}
