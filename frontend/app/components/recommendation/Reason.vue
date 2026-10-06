<script setup lang="ts">
defineProps<{ text: string; kind: 'ok' | 'weak' | 'penalty' }>()
</script>

<template>
  <li class="flex gap-2 text-sm">
    <span
      class="mt-0.5 shrink-0 font-bold"
      :class="{ 'text-brand-600': kind === 'ok', 'text-stone-400': kind === 'weak', 'text-accent': kind === 'penalty' }"
      aria-hidden="true"
    >{{ kind === 'ok' ? '✓' : kind === 'weak' ? '~' : '!' }}</span>
    <span :class="kind === 'ok' ? 'text-stone-700' : 'text-stone-500'">{{ text }}</span>
  </li>
</template>
