type Payload = Record<string, string | number | boolean | null>

/**
 * Tracking anonimo degli eventi. Usa fetch con keepalive: il click sul link Amazon
 * NON viene intercettato né reindirizzato, l'evento parte in parallelo.
 */
export function useTrack() {
  const config = useRuntimeConfig()
  return (type: string, payload: Payload = {}, sessionId: string | null = null) => {
    if (import.meta.server) return
    try {
      fetch(`${config.public.apiBase}/api/events`, {
        method: 'POST',
        keepalive: true,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, payload, session_id: sessionId }),
      }).catch(() => {})
    } catch {
      /* il tracking non deve mai rompere l'interfaccia */
    }
  }
}
