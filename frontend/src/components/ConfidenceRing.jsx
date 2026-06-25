// Animated circular confidence gauge. `value` is 0..1.
export default function ConfidenceRing({ value = 0, color = '#22d3ee', size = 170 }) {
  const stroke = 11
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const clamped = Math.min(Math.max(value, 0), 1)
  const offset = circ * (1 - clamped)
  const pct = Math.round(clamped * 100)

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{
            transition: 'stroke-dashoffset 150ms linear, stroke 250ms ease',
            filter: `drop-shadow(0 0 7px ${color})`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-5xl font-bold tabular-nums" style={{ color }}>
          {pct}
          <span className="text-xl align-top">%</span>
        </div>
        <div className="mt-1 text-[10px] tracking-[0.3em] text-slate-500">CONFIDENCE</div>
      </div>
    </div>
  )
}
