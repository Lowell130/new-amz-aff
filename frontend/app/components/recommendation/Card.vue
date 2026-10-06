<script setup lang="ts">
import type { SlotOut } from '~/types/api'

const props = defineProps<{ item: SlotOut; position: number; sessionId: string; finderSlug: string }>()
const track = useTrack()
const p = computed(() => props.item.product)
const featured = computed(() => props.item.role === 'best_match')

onMounted(() =>
  track('recommendation_viewed', { finder_slug: props.finderSlug, product_id: p.value.id, slot: props.item.role, position: props.position }, props.sessionId),
)

function onClick() {
  track('affiliate_link_clicked', { finder_slug: props.finderSlug, product_id: p.value.id, asin: p.value.asin, slot: props.item.role, position: props.position }, props.sessionId)
}
</script>

<template>
  <article
    class="flex flex-col rounded-2xl border bg-white p-5 shadow-sm"
    :class="featured ? 'border-brand-500 ring-2 ring-brand-100' : 'border-stone-200'"
  >
    <div class="mb-3 flex items-center justify-between gap-2">
      <span
        class="rounded-full px-3 py-1 text-xs font-semibold"
        :class="featured ? 'bg-brand-600 text-white' : 'bg-stone-100 text-stone-600'"
      >{{ item.label }}</span>
      <span v-if="p.is_demo" class="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Prodotto demo</span>
    </div>

    <div class="flex gap-4">
      <div class="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-stone-100">
        <img v-if="p.offer?.image_url" :src="p.offer.image_url" :alt="p.name" class="h-full w-full object-contain" loading="lazy" />
        <span v-else class="text-2xl font-bold text-stone-400">{{ p.brand.charAt(0) }}</span>
      </div>
      <div class="min-w-0">
        <p class="text-sm text-stone-500">{{ p.brand }}</p>
        <h3 class="text-lg font-semibold leading-tight">{{ p.name }}</h3>
        <p class="mt-1 text-xs text-stone-500">Compatibilità con il tuo profilo: {{ Math.round(item.score) }}/100 · affidabilità dati {{ item.confidence }}</p>
      </div>
    </div>

    <div class="mt-4">
      <p class="mb-1 text-sm font-semibold">Perché te la proponiamo</p>
      <ul class="space-y-1">
        <RecommendationReason v-for="r in item.explain.reasons" :key="r" :text="r" kind="ok" />
        <RecommendationReason v-for="r in item.explain.weak_matches" :key="r" :text="r" kind="weak" />
        <RecommendationReason v-for="r in item.explain.penalties" :key="r" :text="r" kind="penalty" />
      </ul>
    </div>

    <div v-if="p.pros.length || p.cons.length" class="mt-4 grid grid-cols-2 gap-3 text-sm">
      <div>
        <p class="font-semibold text-brand-700">Pro</p>
        <ul class="list-inside list-disc text-stone-600"><li v-for="x in p.pros" :key="x">{{ x }}</li></ul>
      </div>
      <div v-if="p.cons.length">
        <p class="font-semibold text-stone-700">Compromessi</p>
        <ul class="list-inside list-disc text-stone-600"><li v-for="x in p.cons" :key="x">{{ x }}</li></ul>
      </div>
    </div>

    <div class="mt-auto pt-5">
      <div v-if="p.offer?.price != null" class="mb-2">
        <span class="text-2xl font-bold">{{ formatPrice(p.offer.price, p.offer.currency ?? 'EUR') }}</span>
        <p class="text-xs text-stone-500">
          Prezzo aggiornato al {{ formatDateTime(p.offer.fetched_at) }}. Prezzi e disponibilità possono variare.
        </p>
      </div>
      <p v-else-if="p.offer?.availability" class="mb-2 text-sm text-stone-500">{{ p.offer.availability }}</p>

      <a
        v-if="p.affiliate_url && !p.is_demo"
        :href="p.affiliate_url"
        target="_blank"
        rel="sponsored nofollow noopener"
        class="block rounded-xl bg-accent px-4 py-3 text-center font-semibold text-white hover:brightness-95"
        @click="onClick"
      >
        Vedi su Amazon
      </a>
      <button
        v-else
        type="button"
        disabled
        class="block w-full cursor-not-allowed rounded-xl bg-stone-200 px-4 py-3 text-center font-semibold text-stone-500"
        title="I prodotti demo non hanno un link reale"
      >
        Vedi su Amazon (link non attivo in demo)
      </button>
    </div>
  </article>
</template>
