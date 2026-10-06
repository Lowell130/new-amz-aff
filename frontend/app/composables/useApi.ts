/** Client API: durante SSR usa l'URL interno, nel browser quello pubblico. */
export function useApi() {
  const config = useRuntimeConfig()
  const baseURL = import.meta.server ? (config.apiBaseServer as string) : config.public.apiBase

  return {
    baseURL,
    get: <T>(path: string) => $fetch<T>(path, { baseURL }),
    post: <T>(path: string, body?: Record<string, unknown>) => $fetch<T>(path, { baseURL, method: 'POST', body }),
  }
}

/** Estrae un messaggio leggibile da un errore $fetch/FastAPI. */
export function apiErrorMessage(e: unknown): string {
  const detail = (e as { data?: { detail?: unknown } })?.data?.detail
  if (typeof detail === 'string') return detail
  return 'Si è verificato un errore. Riprova tra poco.'
}
