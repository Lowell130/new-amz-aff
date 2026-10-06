<script setup lang="ts">
import type { QuickReply } from '~/types/api'

defineProps<{ replies: QuickReply[]; disabled?: boolean }>()
defineEmits<{ pick: [reply: QuickReply] }>()
</script>

<template>
  <div class="flex flex-wrap gap-2" role="group" aria-label="Risposte rapide">
    <button
      v-for="r in replies"
      :key="`${r.question_id}-${r.label}`"
      type="button"
      class="rounded-full border-2 border-brand-500 bg-white px-4 py-1.5 text-sm font-medium text-brand-700 transition hover:bg-brand-50 disabled:opacity-40"
      :disabled="disabled"
      @click="$emit('pick', r)"
    >
      {{ r.label }}
    </button>
  </div>
</template>
