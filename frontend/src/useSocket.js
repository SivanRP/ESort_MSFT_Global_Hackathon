import { useEffect, useRef, useState } from 'react'

/**
 * Subscribe to the backend WebSocket with automatic reconnect.
 * Returns { data, connected } where data is the latest parsed JSON frame.
 */
export function useSocket(url) {
  const [data, setData] = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const retryRef = useRef(null)

  useEffect(() => {
    let closed = false

    function connect() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onmessage = (e) => {
        try {
          setData(JSON.parse(e.data))
        } catch {
          /* ignore malformed frames */
        }
      }
      ws.onclose = () => {
        setConnected(false)
        if (!closed) retryRef.current = setTimeout(connect, 1500)
      }
      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      closed = true
      clearTimeout(retryRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [url])

  return { data, connected }
}
