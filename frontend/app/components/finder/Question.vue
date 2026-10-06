<script setup lang="ts">
import type { QuestionOut } from '~/types/api'

const props = defineProps<{ question: QuestionOut; initial?: unknown; canBack: boolean; loading: boolean }>()
const emit = defineEmits<{ submit: [value: unknown]; back: [] }>()

const single = ref<string | null>(null)
const multi = ref<string[]>([])
const num = ref<number>(0)

function reset() {
  const q = props.question
  const init = props.initial
  single.value = typeof init === 'string' ? init : null
  multi.value = Array.isArray(init) ? [...(init as string[])] : []
  const fallback = typeof q.default === 'number' ? q.default : (q.min ?? 0)
  num.value = typeof init === 'number' ? init : fallback
}
watch(() => props.question.id, reset, { immediate: true })

const showNext = computed(() => ['multiple_choice', 'range', 'number'].includes(props.question.type))
const nextDisabled = computed(() => props.question.type === 'multiple_choice' && props.question.required && !multi.value.length)

function pickSingle(v: string) {
  single.value = v
  emit('submit', v)
}

function toggle(v: string) {
  const max = props.question.max_choices ?? Infinity
  if (multi.value.includes(v)) multi.value = multi.value.filter((x) => x !== v)
  else if (multi.value.length < max) multi.value = [...multi.value, v]
}

function next() {
  if (props.question.type === 'multiple_choice') emit('submit', multi.value)
  else emit('submit', num.value)
}
</script>

<template>
  <section>
    <h2 class="text-2xl font-semibold tracking-tight">{{ question.question }}</h2>
    <p v-if="question.help" class="mt-1 text-stone-500">{{ question.help }}</p>

    <div class="mt-5 grid gap-3">
      <template v-if="question.type === 'single_choice'">
        <FinderOption
          v-for="o in question.options"
          :key="o.value"
          :option="o"
          :selected="single === o.value"
          @select="pickSingle(o.value)"
        />
      </template>

      <template v-else-if="question.type === 'multiple_choice'">
        <FinderOption
          v-for="o in question.options"
          :key="o.value"
          :option="o"
          multiple
          :selected="multi.includes(o.value)"
          @select="toggle(o.value)"
        />
      </template>

      <FinderRange
        v-else-if="question.type === 'range' || question.type === 'number'"
        v-model="num"
        :min="question.min ?? 0"
        :max="question.max ?? 100"
        :step="question.step ?? 1"
        :unit="question.unit"
      />

      <div v-else-if="question.type === 'boolean'" class="grid grid-cols-2 gap-3">
        <FinderOption :option="{ value: 'yes', label: 'Sì' }" :selected="initial === true" @select="emit('submit', true)" />
        <FinderOption :option="{ value: 'no', label: 'No' }" :selected="initial === false" @select="emit('submit', false)" />
      </div>
    </div>

    <FinderNavigation
      :can-back="canBack"
      :show-next="showNext"
      :next-disabled="nextDisabled"
      :loading="loading"
      @back="emit('back')"
      @next="next"
    />
  </section>
</template>
