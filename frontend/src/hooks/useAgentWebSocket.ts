import { useEffect, useRef, useState, useCallback } from 'react'

interface UseAgentWebSocketOptions {
  apiUrl: string
  onMessage: (data: any) => void
  enabled?: boolean
  onReconnect?: () => void
}

/**
 * Native WebSocket hook with auto-reconnect (exponential backoff).
 * Derives WS URL from apiUrl: http:// → ws://, https:// → wss://
 */
export function useAgentWebSocket({
  apiUrl,
  onMessage,
  enabled = true,
  onReconnect,
}: UseAgentWebSocketOptions) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(1000) // start at 1s
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  // Store latest callbacks in refs to avoid reconnect on every render
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage
  const onReconnectRef = useRef(onReconnect)
  onReconnectRef.current = onReconnect

  const connect = useCallback(() => {
    if (!mountedRef.current || !enabled) return

    // Derive WS URL: http(s)://host → ws(s)://host/ws
    const wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws'

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      setConnected(true)
      retryRef.current = 1000 // reset backoff
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessageRef.current(data)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setConnected(false)
      wsRef.current = null

      // Auto-reconnect with exponential backoff (max 30s)
      const delay = retryRef.current
      retryRef.current = Math.min(retryRef.current * 2, 30000)
      timerRef.current = setTimeout(() => {
        if (mountedRef.current && enabled) {
          onReconnectRef.current?.()
          connect()
        }
      }, delay)
    }

    ws.onerror = () => {
      // onclose will fire after onerror, so reconnect is handled there
      ws.close()
    }
  }, [apiUrl, enabled])

  useEffect(() => {
    mountedRef.current = true

    if (enabled) {
      connect()
    }

    return () => {
      mountedRef.current = false
      if (timerRef.current) clearTimeout(timerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent reconnect on unmount
        wsRef.current.close()
      }
    }
  }, [connect, enabled])

  return { connected }
}
