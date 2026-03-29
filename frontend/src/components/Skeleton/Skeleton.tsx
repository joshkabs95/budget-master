import styles from './Skeleton.module.css'

interface SkeletonProps {
  width?: string | number
  height?: string | number
  borderRadius?: string | number
  className?: string
}

export function Skeleton({ width = '100%', height = '1rem', borderRadius = 6, className }: SkeletonProps) {
  return (
    <div
      className={`${styles.skeleton} ${className ?? ''}`}
      style={{ width, height, borderRadius }}
    />
  )
}

export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div className={styles.card}>
      <Skeleton width="40%" height="1rem" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} width={i % 2 === 0 ? '100%' : '70%'} height="0.75rem" />
      ))}
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className={styles.row}>
      <Skeleton width={36} height={36} borderRadius="50%" />
      <div className={styles.rowLines}>
        <Skeleton width="50%" height="0.875rem" />
        <Skeleton width="30%" height="0.7rem" />
      </div>
      <Skeleton width={72} height="0.875rem" />
    </div>
  )
}

export function SkeletonList({ count = 5 }: { count?: number }) {
  return (
    <div className={styles.list}>
      {Array.from({ length: count }).map((_, i) => <SkeletonRow key={i} />)}
    </div>
  )
}
