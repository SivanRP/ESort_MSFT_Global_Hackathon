import { useEffect, useState } from 'react'
import { CLASS_META } from '../constants'

// Full-screen "SORTED → BIN X" flash, fired once per commit. `flash` is
// { cls, id }; a new id re-triggers the animation.
export default function CommitFlash({ flash }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!flash) return
    setShow(true)
    const t = setTimeout(() => setShow(false), 1300)
    return () => clearTimeout(t)
  }, [flash?.id])

  if (!flash) return null
  const meta = CLASS_META[flash.cls]
  if (!meta) return null

  return (
    <div
      className={`pointer-events-none fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-300 ${
        show ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(circle at center, ${meta.glow} 0%, transparent 62%)`,
        }}
      />
      <div className={`relative text-center ${show ? 'animate-commit' : ''}`}>
        <div className="text-xs font-bold tracking-[0.5em] text-white/70">SORTED</div>
        <div
          className="mt-2 text-7xl font-black"
          style={{ color: meta.color, textShadow: `0 0 32px ${meta.color}` }}
        >
          {meta.label.toUpperCase()}
        </div>
        <div className="mt-2 text-lg tracking-[0.3em] text-white/80">
          → BIN ‘{meta.char}’
        </div>
      </div>
    </div>
  )
}
