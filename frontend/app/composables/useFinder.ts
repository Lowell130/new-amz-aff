import type { QuestionOut, ResultOut, StepOut } from '~/types/api'

/** Stato e azioni del wizard del Product Finder. */
export function useFinder(slug: string) {
  const api = useApi()
  const track = useTrack()

  const sessionId = ref<string | null>(null)
  const question = ref<QuestionOut | null>(null)
  const progress = ref({ answered: 0, total: 0 })
  const answers = ref<Record<string, unknown>>({})
  const history = ref<string[]>([])
  const result = ref<ResultOut | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const phase = computed<'intro' | 'questions' | 'result'>(() => {
    if (result.value) return 'result'
    if (sessionId.value && question.value) return 'questions'
    return 'intro'
  })

  function applyStep(s: StepOut) {
    sessionId.value = s.session_id
    question.value = s.question
    progress.value = s.progress
    answers.value = s.answers
    if (s.question) track('finder_question_viewed', { finder_slug: slug, question_id: s.question.id }, s.session_id)
  }

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    loading.value = true
    error.value = null
    try {
      return await fn()
    } catch (e) {
      error.value = apiErrorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function start() {
    await run(async () => {
      result.value = null
      history.value = []
      applyStep(await api.post<StepOut>(`/api/finder/${slug}/start`))
      track('finder_started', { finder_slug: slug }, sessionId.value)
    })
  }

  async function submit(value: unknown) {
    const q = question.value
    if (!q || !sessionId.value) return
    const step = await run(() =>
      api.post<StepOut>(`/api/finder/session/${sessionId.value}/answer`, { question_id: q.id, value }),
    )
    if (!step) return
    history.value.push(q.id)
    applyStep(step)
    track('finder_answered', { finder_slug: slug, question_id: q.id }, sessionId.value)
    if (step.done) await complete()
  }

  async function complete() {
    const res = await run(() => api.post<ResultOut>(`/api/finder/session/${sessionId.value}/complete`))
    if (!res) return
    result.value = res
    track('finder_completed', { finder_slug: slug }, sessionId.value)
    // risultato condivisibile via URL (la pagina con ?s= è noindex)
    await navigateTo({ query: { s: res.session_id } }, { replace: true })
  }

  async function back() {
    const prev = history.value.pop()
    if (!prev || !sessionId.value) return
    const q = await run(() => api.get<QuestionOut>(`/api/finder/session/${sessionId.value}/question/${prev}`))
    if (q) {
      question.value = q
      progress.value = { ...progress.value, answered: Math.max(0, progress.value.answered - 1) }
    }
  }

  async function loadResult(id: string) {
    if (result.value?.session_id === id) return
    await run(async () => {
      result.value = await api.get<ResultOut>(`/api/finder/session/${id}/result`)
      sessionId.value = id
    })
  }

  /** Dal risultato torna all'ultima domanda per modificare le risposte. */
  async function editAnswers() {
    if (!sessionId.value) return
    const state = await run(() => api.get<StepOut>(`/api/finder/session/${sessionId.value}`))
    if (!state) return
    applyStep(state)
    history.value = Object.keys(state.answers)
    result.value = null
    await navigateTo({ query: {} }, { replace: true })
    await back()
  }

  return {
    sessionId, question, progress, answers, history, result, loading, error, phase,
    start, submit, back, loadResult, editAnswers,
  }
}
