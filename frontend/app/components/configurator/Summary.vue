<script setup lang="ts">
import type { ConfigurationOut } from '~/types/api'

const props = defineProps<{ config: ConfigurationOut }>()
defineEmits<{ edit: [] }>()

const pct = computed(() => Math.min(100, Math.round((props.config.total_valid / props.config.budget) * 100)))
const chips = computed(() => {
  const p = props.config.profile
  return [...p.use_cases, p.experience, ...p.priorities, ...p.requirements].filter(Boolean) as string[]
})
</script>

<template>
  <section class="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-sm text-stone-500">Totale del kit</p>
        <p class="text-3xl font-bold">{{ formatPrice(config.total_valid) }}</p>
        <p class="text-sm text-stone-500">su un budget di {{ formatPrice(config.budget) }}</p>
      </div>
      <div class="text-right">
        <p v-if="config.residual !== null && config.residual >= 0" class="text-lg font-semibold text-brand-700">
          Ti restano {{ formatPrice(config.residual) }}
        </p>
        <p v-else-if="config.residual !== null" class="text-lg font-semibold text-accent">
          Oltre il budget di {{ formatPrice(-config.residual) }}
        </p>
        <button type="button" class="mt-2 rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100" @click="$emit('edit')">
          Modifica le scelte
        </button>
      </div>
    </div>

    <div class="mt-4 h-3 overflow-hidden rounded-full bg-stone-200" aria-hidden="true">
      <div class="h-full rounded-full transition-all" :class="config.over_budget ? 'bg-accent' : 'bg-brand-500'" :style="{ width: `${pct}%` }" />
    </div>

    <p v-if="config.missing_prices" class="mt-3 text-sm text-stone-600">
      {{ config.missing_prices }} {{ config.missing_prices === 1 ? 'componente non ha' : 'componenti non hanno' }} un prezzo aggiornato:
      il totale comprende solo i prezzi disponibili.
    </p>
    <p v-if="config.over_budget" class="mt-3 text-sm text-accent">
      Con le sostituzioni che hai fatto il kit supera il budget indicato.
    </p>
    <p v-else-if="config.residual !== null && config.residual > config.budget * 0.15" class="mt-3 text-sm text-stone-600">
      Non abbiamo speso tutto il budget: per il tuo profilo i prodotti più costosi non risultavano migliori.
    </p>

    <div class="mt-4 flex flex-wrap gap-2">
      <span v-for="c in chips" :key="c" class="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">{{ c }}</span>
    </div>
  </section>
</template>
