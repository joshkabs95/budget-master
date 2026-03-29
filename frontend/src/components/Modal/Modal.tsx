import { useEffect, useId, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import styles from './Modal.module.css'

interface Props {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  width?: number
}

export default function Modal({ open, onClose, title, children, width = 480 }: Props) {
  const titleId = useId()
  const modalRef = useRef<HTMLDivElement>(null)

  // Escape key to close
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  // Focus the modal panel when it opens
  useEffect(() => {
    if (open) {
      // Small delay to let AnimatePresence mount the element
      const t = setTimeout(() => modalRef.current?.focus(), 50)
      return () => clearTimeout(t)
    }
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <div
          className={styles.overlay}
          onClick={onClose}
          aria-hidden="true"
        >
          <motion.div
            ref={modalRef}
            className={styles.modal}
            style={{ width, maxWidth: '95vw' }}
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
          >
            <div className={styles.header}>
              <h3 id={titleId} className={styles.title}>{title}</h3>
              <button className={styles.close} onClick={onClose} aria-label="Fermer">✕</button>
            </div>
            <div className={styles.body}>{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
