<script setup lang="ts">
import type { ResultOut } from '~/types/api'

const props = defineProps<{ result: ResultOut }>()
defineEmits<{ edit: []; restart: [] }>()

const chips = computed(() => {
  const p = props.result.profile
  return [
    ...p.use_cases,
    p.experience,
    ...p.priorities,
    ...p.requirements,
    p.budget_max ? `fino a ${formatPrice(p.budget_max)}` : null,
  ].filter(Boolean) as string[]
})
</script>

<template>
  <section>
    <div class="mb-6">
      <h2 class="text-2xl font-semibold tracking-tight">Ecco cosa ti consigliamo</h2>
      <p class="mt-1 text-stone-500">
        Abbiamo confrontato {{ result.considered }} modelli; {{ result.excluded }} non erano compatibili con le tue risposte.
      </p>
      <div class="mt-3 flex flex-wrap gap-2">
        <span v-for="c in chips" :key="c" class="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">{{ c }}</span>
      </div>
      <div class="mt-4 flex gap-3">
        <button type="button" class="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100" @click="$emit('edit')">
          Modifica le risposte
        </button>
        <button type="button" class="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100" @click="$emit('restart')">
          Ricomincia
        </button>
      </div>
    </div>

    <p v-if="!result.slots.length" class="rounded-xl bg-white p-6 text-stone-600">
      Nessun prodotto rispetta tutti i vincoli indicati. Prova ad alzare il budget o ad allentare qualche requisito.
    </p>

    <div v-else class="grid gap-5 md:grid-cols-2">
      <RecommendationCard
        v-for="(s, i) in result.slots"
        :key="s.product.id"
        :item="s"
        :position="i + 1"
        :session-id="result.session_id"
        :finder-slug="result.finder_slug"
      />
    </div>

    <div v-if="result.slots.length > 1" class="mt-10">
      <h3 class="mb-3 text-lg font-semibold">Confronto rapido</h3>
      <RecommendationComparison :slots="result.slots.slice(0, 4)" :labels="result.attribute_labels" />
    </div>

    <AffiliateDisclosure class="mt-8" />
  </section>
</template>
