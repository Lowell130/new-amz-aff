import type { AdvisorReply, QuickReply } from '~/types/api'

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  text: string
  reply?: AdvisorReply
}

/** Conversazione con l'AI Advisor. Il testo resta solo nel browser: il server salva lo stato strutturato. */
export function useAdvisor() {
  const api = useApi()
  const track = useTrack()
  const sessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  let seq = 0

  const lastReply = computed(() => {
    const last = messages.value[messages.value.length - 1]
    return last?.role === 'assistant' ? last.reply : undefined
  })

  function push(role: ChatMessage['role'], text: string, reply?: AdvisorReply) {
    messages.value = [...messages.value, { id: ++seq, role, text, reply }]
  }

  async function call(fn: () => Promise<AdvisorReply>) {
    loading.value = true
    error.value = null
    try {
      const r = await fn()
      sessionId.value = r.session_id
      push('assistant', r.text, r)
    } catch (e) {
      error.value = apiErrorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function start() {
    messages.value = []
    await call(() => api.post<AdvisorReply>('/api/advisor/session'))
    track('advisor_started', { page: 'consulente' }, sessionId.value)
  }

  async function send(text: string) {
    const t = text.trim()
    if (!t || !sessionId.value || loading.value) return
    push('user', t)
    track('advisor_message', { page: 'consulente' }, sessionId.value)
    await call(() => api.post<AdvisorReply>('/api/advisor/message', { session_id: sessionId.value, text: t }))
  }

  async function quick(q: QuickReply) {
    if (!sessionId.value || loading.value) return
    push('user', q.label)
    track('advisor_message', { page: 'consulente', question_id: q.question_id }, sessionId.value)
    await call(() =>
      api.post<AdvisorReply>('/api/advisor/message', {
        session_id: sessionId.value,
        quick_reply: { question_id: q.question_id, value: q.value },
      }),
    )
  }

  return { sessionId, messages, loading, error, lastReply, start, send, quick }
}
