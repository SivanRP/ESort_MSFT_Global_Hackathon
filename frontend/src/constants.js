// Per-class presentation metadata. Colors are the neon accents; char is the
// serial signal the backend sends; disposal drives the label copy. Keep the
// keys in sync with the backend class names (pcb/battery/metal/plastic).
export const CLASS_META = {
  pcb: {
    label: 'PCB',
    char: 'P',
    color: '#34d399',
    glow: 'rgba(52, 211, 153, 0.55)',
    disposal: 'Recyclable',
  },
  battery: {
    label: 'Battery',
    char: 'B',
    color: '#ef4444',
    glow: 'rgba(239, 68, 68, 0.65)',
    disposal: 'Hazardous',
    hazard: true,
  },
  metal: {
    label: 'Metal',
    char: 'M',
    color: '#38bdf8',
    glow: 'rgba(56, 189, 248, 0.55)',
    disposal: 'Recyclable',
  },
  plastic: {
    label: 'Plastic',
    char: 'L',
    color: '#fbbf24',
    glow: 'rgba(251, 191, 36, 0.55)',
    disposal: 'Recyclable',
  },
}

export const CLASS_ORDER = ['pcb', 'battery', 'metal', 'plastic']

// Connect straight to the FastAPI WebSocket. Defaults to the same host the
// dashboard is served from, on the backend's port. Override with VITE_WS_URL.
export const WS_URL =
  import.meta.env.VITE_WS_URL || `ws://${location.hostname}:8000/ws`
