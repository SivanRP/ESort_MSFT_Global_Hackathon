import { useEffect, useState } from 'react'
import { useSocket } from './useSocket'
import { WS_URL, CLASS_ORDER, CLASS_META } from './constants'
import VideoFeed from './components/VideoFeed'
import ConfidenceRing from './components/ConfidenceRing'
import TallyCard from './components/TallyCard'
import CommitFlash from './components/CommitFlash'

export default function App() {
  const { data, connected } = useSocket(WS_URL)
  const [flash, setFlash] = useState(null)

  // `committed` is non-null only on the commit frame -> fire the flash once.
  useEffect(() => {
    if (data?.committed) setFlash({ cls: data.committed, id: Date.now() })
  }, [data])

  const status = data?.status
  const topClass = data?.top_class || null
  const topConf = data?.top_conf || 0
  const stability = data?.stability || 0
  const fps = data?.fps || 0
  const hazard = !!data?.hazard
  const tallies = data?.tallies || { pcb: 0, battery: 0, metal: 0, plastic: 0 }
  const meta = topClass ? CLASS_META[topClass] : null
  const total = CLASS_ORDER.reduce((s, c) => s + (tallies[c] || 0), 0)

  return (
    <div className="bg-grid min-h-screen bg-[#070a0f] font-mono text-slate-100">
      {/* ---- header ---- */}
      <header className="flex items-center justify-between border-b border-white/5 px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="h-3 w-3 rounded-full bg-cyan-400 shadow-[0_0_12px_#22d3ee] animate-blink" />
          <h1 className="text-xl font-bold tracking-[0.3em] text-white">E·WASTE SORTER</h1>
          <span className="hidden text-[10px] tracking-[0.3em] text-slate-600 sm:inline">
            CV SIGNAL PIPELINE
          </span>
        </div>
        <div className="flex items-center gap-5 text-xs">
          <Stat label="FPS" value={fps.toFixed(1)} />
          <Stat label="SORTED" value={total} />
          <ConnPill connected={connected} status={status} />
        </div>
      </header>

      {/* ---- main ---- */}
      <main className="grid grid-cols-1 gap-5 p-5 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <VideoFeed data={data} connected={connected} hazard={hazard} />
        </section>

        <aside className="flex flex-col gap-5">
          {/* current detection */}
          <div className="flex flex-col items-center rounded-2xl border border-white/5 bg-white/[0.02] p-6">
            <div className="mb-5 text-[11px] tracking-[0.3em] text-slate-500">
              CURRENT DETECTION
            </div>
            <ConfidenceRing value={topConf} color={meta?.color || '#334155'} />
            <div className="mt-5 text-center">
              {meta ? (
                <>
                  <div className="text-3xl font-bold" style={{ color: meta.color }}>
                    {meta.label}
                  </div>
                  <div className="mt-1 text-[10px] tracking-[0.2em] text-slate-400">
                    SIGNAL ‘{meta.char}’ · {meta.disposal.toUpperCase()}
                  </div>
                </>
              ) : (
                <div className="text-2xl font-bold text-slate-700">— NONE —</div>
              )}
            </div>

            {/* stability / "locking in" bar */}
            <div className="mt-6 w-full">
              <div className="mb-1.5 flex justify-between text-[10px] tracking-[0.2em] text-slate-500">
                <span>{stability >= 1 ? 'LOCKED' : 'LOCKING IN'}</span>
                <span>{Math.round(stability * 100)}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full transition-all duration-150"
                  style={{
                    width: `${Math.min(stability, 1) * 100}%`,
                    background: meta?.color || '#22d3ee',
                  }}
                />
              </div>
            </div>
          </div>

          {/* hazard callout */}
          {hazard && (
            <div className="animate-hazard rounded-2xl border-2 border-red-500/60 bg-red-500/10 p-5 text-center">
              <div className="text-sm font-bold tracking-[0.3em] text-red-400">
                ⚠ LITHIUM HAZARD
              </div>
              <div className="mt-1.5 text-xs text-red-300/80">
                Battery detected — fire risk if mis-binned
              </div>
            </div>
          )}
        </aside>
      </main>

      {/* ---- tallies ---- */}
      <footer className="grid grid-cols-2 gap-5 px-5 pb-6 lg:grid-cols-4">
        {CLASS_ORDER.map((c) => (
          <TallyCard key={c} cls={c} count={tallies[c] || 0} active={topClass === c} />
        ))}
      </footer>

      <CommitFlash flash={flash} />
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="text-right">
      <div className="text-[9px] tracking-[0.25em] text-slate-600">{label}</div>
      <div className="font-bold tabular-nums text-white">{value}</div>
    </div>
  )
}

function ConnPill({ connected, status }) {
  let color = '#ef4444'
  let text = 'OFFLINE'
  if (connected && status === 'error') {
    color = '#fbbf24'
    text = 'NO MODEL'
  } else if (connected) {
    color = '#34d399'
    text = 'LIVE'
  }
  return (
    <div
      className="flex items-center gap-2 rounded-full border px-3 py-1.5"
      style={{ borderColor: `${color}55`, background: `${color}14` }}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      <span className="text-[10px] font-bold tracking-[0.2em]" style={{ color }}>
        {text}
      </span>
    </div>
  )
}
