<script setup lang="ts">
defineProps<{ canBack: boolean; showNext: boolean; nextDisabled?: boolean; loading?: boolean }>()
defineEmits<{ back: []; next: [] }>()
</script>

<template>
  <div class="mt-6 flex items-center justify-between">
    <button
      type="button"
      class="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-200 disabled:invisible"
      :disabled="!canBack || loading"
      @click="$emit('back')"
    >
      ← Indietro
    </button>
    <button
      v-if="showNext"
      type="button"
      class="rounded-lg bg-brand-600 px-6 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:opacity-40"
      :disabled="nextDisabled || loading"
      @click="$emit('next')"
    >
      Avanti →
    </button>
  </div>
</template>
