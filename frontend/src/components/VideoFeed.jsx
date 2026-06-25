// The live annotated camera frame plus overlay chrome (LIVE pill, status
// messages, and a red hazard border when a battery is in view).
export default function VideoFeed({ data, connected, hazard }) {
  const frame = data?.frame
  const status = data?.status
  const error = data?.error
  const fps = data?.fps ?? 0

  return (
    <div
      className={`relative aspect-video w-full overflow-hidden rounded-2xl border bg-black transition-all duration-300 ${
        hazard
          ? 'border-red-500 shadow-[0_0_45px_rgba(239,68,68,0.45)]'
          : 'border-white/10'
      }`}
    >
      {frame ? (
        <img
          src={`data:image/jpeg;base64,${frame}`}
          alt="detection"
          className="h-full w-full object-contain"
        />
      ) : (
        <Placeholder connected={connected} status={status} error={error} />
      )}

      {/* top-left LIVE / state pill */}
      <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-1.5 backdrop-blur">
        <span
          className={`h-2 w-2 rounded-full ${
            frame ? 'bg-red-500 animate-blink' : 'bg-slate-500'
          }`}
        />
        <span className="text-[10px] font-bold tracking-[0.25em] text-white/80">
          {frame ? 'LIVE' : 'STANDBY'}
        </span>
      </div>

      {/* top-right FPS */}
      {frame && (
        <div className="absolute right-4 top-4 rounded-full border border-white/10 bg-black/50 px-3 py-1.5 font-mono text-[11px] tracking-widest text-cyan-300 backdrop-blur">
          {fps.toFixed(1)} FPS
        </div>
      )}

      {/* hazard ribbon */}
      {hazard && (
        <div className="animate-hazard absolute bottom-0 left-0 right-0 bg-red-600/80 py-2 text-center text-xs font-bold tracking-[0.35em] text-white backdrop-blur">
          ⚠ LITHIUM BATTERY — HAZARD
        </div>
      )}
    </div>
  )
}

function Placeholder({ connected, status, error }) {
  let title = 'CONNECTING TO BACKEND…'
  let detail = `ws · ${location.hostname}:8000`
  let tone = 'text-slate-500'

  if (connected && status === 'error') {
    title = 'MODEL NOT LOADED'
    detail = error || 'Train model/best.pt (Phase 2) to start detecting.'
    tone = 'text-amber-400'
  } else if (connected) {
    title = 'WAITING FOR CAMERA…'
    detail = 'Grant camera permission and present an item.'
    tone = 'text-slate-400'
  }

  return (
    <div className="bg-grid absolute inset-0 flex flex-col items-center justify-center px-8 text-center">
      <div className={`text-sm font-bold tracking-[0.35em] ${tone}`}>{title}</div>
      <div className="mt-3 max-w-md text-xs leading-relaxed text-slate-600">{detail}</div>
    </div>
  )
}
