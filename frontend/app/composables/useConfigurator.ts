import type { ConfigurationOut, ConfiguratorDetail } from '~/types/api'

/** Stato e azioni del Configuratore. */
export function useConfigurator(detail: ConfiguratorDetail) {
  const api = useApi()
  const track = useTrack()

  const answers = ref<Record<string, unknown>>({})
  const optional = ref<string[]>(detail.components.filter((c) => !c.required).map((c) => c.key))
  const result = ref<ConfigurationOut | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // valori iniziali: default delle domande (es. budget)
  for (const q of detail.inputs) {
    if (q.default !== null && q.default !== undefined) answers.value[q.id] = q.default
    if (q.type === 'multiple_choice' && answers.value[q.id] === undefined) answers.value[q.id] = []
  }

  const missing = computed(() =>
    detail.inputs.filter((q) => q.required && (answers.value[q.id] === undefined || answers.value[q.id] === null)),
  )

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

  async function build() {
    if (missing.value.length) {
      error.value = `Rispondi anche a: ${missing.value.map((q) => q.question).join(' · ')}`
      return
    }
    track('configuration_started', { page: detail.slug })
    const res = await run(() =>
      api.post<ConfigurationOut>(`/api/configurators/${detail.slug}/build`, {
        answers: answers.value,
        include_optional: optional.value,
      }),
    )
    if (!res) return
    result.value = res
    track('configuration_completed', { page: detail.slug }, res.session_id)
    await navigateTo({ query: { c: res.session_id } }, { replace: true })
  }

  async function swap(componentKey: string, productId: string) {
    if (!result.value) return
    const res = await run(() =>
      api.post<ConfigurationOut>(`/api/configuration/${result.value!.session_id}/swap`, {
        component_key: componentKey,
        product_id: productId,
      }),
    )
    if (res) result.value = res
  }

  async function load(id: string) {
    if (result.value?.session_id === id) return
    const res = await run(() => api.get<ConfigurationOut>(`/api/configuration/${id}`))
    if (res) {
      result.value = res
      // modulo già compilato con le risposte della configurazione (es. arrivando dall'AI Advisor)
      answers.value = { ...answers.value, ...res.answers }
      if (res.include_optional) optional.value = [...res.include_optional]
    }
  }

  async function edit() {
    result.value = null
    await navigateTo({ query: {} }, { replace: true })
  }

  return { answers, optional, result, loading, error, build, swap, load, edit }
}
