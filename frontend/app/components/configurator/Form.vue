<script setup lang="ts">
import type { ConfiguratorDetail } from '~/types/api'

const props = defineProps<{ detail: ConfiguratorDetail; loading: boolean }>()
const answers = defineModel<Record<string, unknown>>('answers', { required: true })
const optional = defineModel<string[]>('optional', { required: true })
defineEmits<{ submit: [] }>()

const optionalComponents = computed(() => props.detail.components.filter((c) => !c.required))
const requiredComponents = computed(() => props.detail.components.filter((c) => c.required))

function pick(id: string, value: string) {
  answers.value = { ...answers.value, [id]: value }
}

function toggle(id: string, value: string, max?: number | null) {
  const cur = (answers.value[id] as string[] | undefined) ?? []
  let next = cur.includes(value) ? cur.filter((x) => x !== value) : [...cur, value]
  if (max && next.length > max) next = next.slice(next.length - max)
  answers.value = { ...answers.value, [id]: next }
}

function toggleOptional(key: string) {
  optional.value = optional.value.includes(key) ? optional.value.filter((k) => k !== key) : [...optional.value, key]
}

const budget = computed({
  get: () => Number(answers.value.budget ?? 0),
  set: (v: number) => (answers.value = { ...answers.value, budget: v }),
})
</script>

<template>
  <form class="space-y-7" @submit.prevent="$emit('submit')">
    <fieldset v-for="q in detail.inputs" :key="q.id">
      <legend class="mb-2 font-semibold">{{ q.question }}</legend>

      <div v-if="q.type === 'single_choice'" class="flex flex-wrap gap-2">
        <button
          v-for="o in q.options"
          :key="o.value"
          type="button"
          class="rounded-full border-2 px-4 py-2 text-sm font-medium transition"
          :class="answers[q.id] === o.value ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-stone-200 bg-white hover:border-brand-500'"
          :aria-pressed="answers[q.id] === o.value"
          @click="pick(q.id, o.value)"
        >
          {{ o.label }}
        </button>
      </div>

      <div v-else-if="q.type === 'multiple_choice'" class="flex flex-wrap gap-2">
        <button
          v-for="o in q.options"
          :key="o.value"
          type="button"
          class="rounded-full border-2 px-4 py-2 text-sm font-medium transition"
          :class="(answers[q.id] as string[] | undefined)?.includes(o.value) ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-stone-200 bg-white hover:border-brand-500'"
          :aria-pressed="(answers[q.id] as string[] | undefined)?.includes(o.value) ?? false"
          @click="toggle(q.id, o.value, q.max_choices)"
        >
          {{ o.label }}
        </button>
      </div>

      <FinderRange
        v-else-if="q.id === 'budget'"
        v-model="budget"
        :min="q.min ?? 0"
        :max="q.max ?? 1000"
        :step="q.step ?? 10"
        :unit="q.unit"
      />
    </fieldset>

    <fieldset>
      <legend class="mb-2 font-semibold">Componenti del kit</legend>
      <div class="flex flex-wrap gap-2">
        <span v-for="c in requiredComponents" :key="c.key" class="rounded-full bg-stone-200 px-4 py-2 text-sm font-medium text-stone-700">
          {{ c.label }} · essenziale
        </span>
        <label
          v-for="c in optionalComponents"
          :key="c.key"
          class="flex cursor-pointer items-center gap-2 rounded-full border-2 px-4 py-2 text-sm font-medium"
          :class="optional.includes(c.key) ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-stone-200 bg-white'"
        >
          <input type="checkbox" class="accent-brand-500" :checked="optional.includes(c.key)" @change="toggleOptional(c.key)" />
          {{ c.label }}
        </label>
      </div>
      <p class="mt-2 text-xs text-stone-500">Gli accessori vengono aggiunti solo se il budget lo consente senza sacrificare l'essenziale.</p>
    </fieldset>

    <button
      type="submit"
      class="w-full rounded-xl bg-brand-600 px-8 py-3 text-lg font-semibold text-white hover:bg-brand-700 disabled:opacity-50 sm:w-auto"
      :disabled="loading"
    >
      {{ loading ? 'Sto componendo il kit…' : 'Crea il mio kit' }}
    </button>
  </form>
</template>
