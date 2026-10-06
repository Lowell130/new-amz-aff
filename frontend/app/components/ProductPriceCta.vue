<script setup lang="ts">
import type { ProductCard } from '~/types/api'

const props = defineProps<{ product: ProductCard; sessionId?: string | null; context?: string }>()
const track = useTrack()

function onClick() {
  track(
    'affiliate_link_clicked',
    { product_id: props.product.id, asin: props.product.asin, page: props.context ?? null },
    props.sessionId ?? null,
  )
}
</script>

<template>
  <div>
    <div v-if="product.offer?.price != null" class="mb-2">
      <span class="text-xl font-bold">{{ formatPrice(product.offer.price, product.offer.currency ?? 'EUR') }}</span>
      <p class="text-xs text-stone-500">
        Prezzo aggiornato al {{ formatDateTime(product.offer.fetched_at) }}. Prezzi e disponibilità possono variare.
      </p>
    </div>
    <p v-else class="mb-2 text-sm text-stone-500">{{ product.offer?.availability ?? 'Prezzo non disponibile al momento' }}</p>

    <a
      v-if="product.affiliate_url && !product.is_demo"
      :href="product.affiliate_url"
      target="_blank"
      rel="sponsored nofollow noopener"
      class="block rounded-xl bg-accent px-4 py-2.5 text-center font-semibold text-white hover:brightness-95"
      @click="onClick"
    >
      Vedi su Amazon
    </a>
    <button
      v-else
      type="button"
      disabled
      class="block w-full cursor-not-allowed rounded-xl bg-stone-200 px-4 py-2.5 text-center text-sm font-semibold text-stone-500"
      title="I prodotti demo non hanno un link reale"
    >
      Vedi su Amazon (link non attivo in demo)
    </button>
  </div>
</template>
