<script setup lang="ts">
const props = defineProps<{ min: number; max: number; step: number; unit?: string | null }>()
const model = defineModel<number>({ required: true })
const label = computed(() => (props.unit === '€' ? formatPrice(model.value) : `${model.value} ${props.unit ?? ''}`))
</script>

<template>
  <div class="rounded-xl border-2 border-stone-200 bg-white p-5">
    <div class="mb-4 text-center text-3xl font-semibold text-brand-700">{{ label }}</div>
    <input
      v-model.number="model"
      type="range"
      :min="min"
      :max="max"
      :step="step"
      class="w-full accent-brand-500"
      aria-label="Seleziona un valore"
    />
    <div class="mt-1 flex justify-between text-xs text-stone-500">
      <span>{{ unit === '€' ? formatPrice(min) : min }}</span>
      <span>{{ unit === '€' ? formatPrice(max) : max }}</span>
    </div>
  </div>
</template>
