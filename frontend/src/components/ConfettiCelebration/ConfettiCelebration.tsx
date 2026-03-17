import { useEffect } from 'react'
import confetti from 'canvas-confetti'

export default function ConfettiCelebration({ trigger }: { trigger: boolean }) {
  useEffect(() => {
    if (!trigger) return
    const end = Date.now() + 2000
    const colors = ['#c9a84c', '#22c55e', '#3b82f6', '#a855f7', '#f97316']
    const frame = () => {
      confetti({ particleCount: 3, angle: 60, spread: 55, origin: { x: 0 }, colors })
      confetti({ particleCount: 3, angle: 120, spread: 55, origin: { x: 1 }, colors })
      if (Date.now() < end) requestAnimationFrame(frame)
    }
    requestAnimationFrame(frame)
  }, [trigger])
  return null
}
