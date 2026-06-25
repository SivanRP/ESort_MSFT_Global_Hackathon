import { useEffect, useRef, useState } from 'react'
import { CLASS_META } from '../constants'

// One category tally. Pops + glows when its count increments, and brightens
// while that class is the current top detection.
export default function TallyCard({ cls, count, active }) {
  const meta = CLASS_META[cls]
  const prev = useRef(count)
  const [bump, setBump] = useState(false)

  useEffect(() => {
    if (count > prev.current) {
      setBump(true)
      const t = setTimeout(() => setBump(false), 600)
      prev.current = count
      return () => clearTimeout(t)
    }
    prev.current = count
  }, [count])

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border p-5 transition-all duration-300 ${
        bump ? 'animate-bump' : ''
      } ${active ? 'border-white/20' : 'border-white/5'}`}
      style={{
        background: active ? `${meta.color}14` : 'rgba(255,255,255,0.02)',
        boxShadow: bump ? `0 0 32px ${meta.glow}` : 'none',
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <div
            className="text-sm font-bold tracking-[0.2em]"
            style={{ color: meta.color }}
          >
            {meta.label.toUpperCase()}
          </div>
          <div className="mt-0.5 text-[10px] tracking-widest text-slate-500">
            SIGNAL ‘{meta.char}’ · {meta.disposal}
          </div>
        </div>
        {meta.hazard && (
          <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[9px] font-bold tracking-widest text-red-300">
            HAZARD
          </span>
        )}
      </div>

      <div className="mt-4 flex items-end justify-between">
        <div
          className="text-5xl font-bold tabular-nums transition-colors duration-300"
          style={{ color: bump ? meta.color : '#ffffff' }}
        >
          {count}
        </div>
        <div
          className="h-10 w-1.5 rounded-full transition-all duration-300"
          style={{
            background: meta.color,
            opacity: active ? 1 : 0.3,
            boxShadow: active ? `0 0 12px ${meta.color}` : 'none',
          }}
        />
      </div>
    </div>
  )
}
