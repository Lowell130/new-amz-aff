<script setup lang="ts">
import type { OptionOut } from '~/types/api'

defineProps<{ option: OptionOut; selected: boolean; multiple?: boolean }>()
defineEmits<{ select: [] }>()
</script>

<template>
  <button
    type="button"
    class="flex w-full items-start gap-3 rounded-xl border-2 bg-white p-4 text-left transition hover:border-brand-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    :class="selected ? 'border-brand-500 bg-brand-50' : 'border-stone-200'"
    :aria-pressed="selected"
    @click="$emit('select')"
  >
    <span
      class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border-2"
      :class="[multiple ? 'rounded' : 'rounded-full', selected ? 'border-brand-500 bg-brand-500' : 'border-stone-300']"
    >
      <svg v-if="selected" viewBox="0 0 20 20" class="h-3 w-3 fill-white"><path d="M7.6 13.4 4.2 10l-1.4 1.4 4.8 4.8 10-10-1.4-1.4z" /></svg>
    </span>
    <span>
      <span class="block font-medium">{{ option.label }}</span>
      <span v-if="option.hint" class="block text-sm text-stone-500">{{ option.hint }}</span>
    </span>
  </button>
</template>
