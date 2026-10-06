<script setup lang="ts">
defineProps<{ compact?: boolean }>()
</script>

<template>
  <p :class="compact ? 'text-xs text-stone-500' : 'text-sm text-stone-600'">
    In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei.
    <template v-if="!compact">
      Prezzi e disponibilità possono cambiare: quelli validi sono indicati su Amazon al momento dell'acquisto.
    </template>
  </p>
</template>
