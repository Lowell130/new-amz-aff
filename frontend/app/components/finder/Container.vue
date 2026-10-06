<script setup lang="ts">
import type { FinderDetail } from '~/types/api'

const props = defineProps<{ finder: FinderDetail; sessionFromUrl?: string | null }>()
const f = useFinder(props.finder.slug)

onMounted(() => {
  if (props.sessionFromUrl) f.loadResult(props.sessionFromUrl)
})
watch(
  () => props.sessionFromUrl,
  (id) => { if (id) f.loadResult(id) },
)

async function restart() {
  await navigateTo({ query: {} }, { replace: true })
  await f.start()
}
</script>

<template>
  <div class="rounded-3xl bg-white/60 p-5 shadow-sm ring-1 ring-stone-200 sm:p-8">
    <p v-if="f.error.value" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{{ f.error.value }}</p>

    <div v-if="f.phase.value === 'intro'" class="text-center">
      <p class="mx-auto max-w-xl text-stone-600">
        {{ finder.questions }} domande al massimo, meno di un minuto. Nessuna registrazione.
      </p>
      <button
        type="button"
        class="mt-5 rounded-xl bg-brand-600 px-8 py-3 text-lg font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        :disabled="f.loading.value"
        @click="f.start()"
      >
        {{ f.loading.value ? 'Un attimo…' : 'Inizia' }}
      </button>
    </div>

    <div v-else-if="f.phase.value === 'questions' && f.question.value">
      <FinderProgress :answered="f.progress.value.answered" :total="f.progress.value.total" />
      <FinderQuestion
        :question="f.question.value"
        :initial="f.answers.value[f.question.value.id]"
        :can-back="f.history.value.length > 0"
        :loading="f.loading.value"
        @submit="f.submit"
        @back="f.back"
      />
    </div>

    <FinderResult
      v-else-if="f.result.value"
      :result="f.result.value"
      @edit="f.editAnswers"
      @restart="restart"
    />
  </div>
</template>
