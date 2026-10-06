<script setup lang="ts">
const props = defineProps<{ answered: number; total: number }>()
const pct = computed(() => (props.total ? Math.round((props.answered / props.total) * 100) : 0))
</script>

<template>
  <div class="mb-6" aria-label="Avanzamento">
    <div class="mb-1 flex justify-between text-xs font-medium text-stone-500">
      <span>Domanda {{ Math.min(answered + 1, total) }} di {{ total }}</span>
      <span>{{ pct }}%</span>
    </div>
    <div class="h-2 overflow-hidden rounded-full bg-stone-200">
      <div class="h-full rounded-full bg-brand-500 transition-all duration-300" :style="{ width: `${pct}%` }" />
    </div>
  </div>
</template>
