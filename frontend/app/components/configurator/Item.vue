<script setup lang="ts">
import type { ConfigItemOut } from '~/types/api'

const props = defineProps<{ item: ConfigItemOut; sessionId: string; loading: boolean }>()
defineEmits<{ swap: [productId: string] }>()

const p = computed(() => props.item.product)
const reasons = computed(() => props.item.explain.reasons.slice(0, 3))

function delta(d: number | null) {
  if (d === null) return ''
  return formatPrice(Math.abs(d))
}
</script>

<template>
  <article class="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-5 sm:flex-row">
      <div class="min-w-0 flex-1">
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <span class="text-sm font-semibold uppercase tracking-wide text-brand-700">{{ item.label }}</span>
          <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="item.required ? 'bg-stone-100 text-stone-600' : 'bg-brand-50 text-brand-700'">
            {{ item.required ? 'Essenziale' : 'Opzionale' }}
          </span>
          <span v-if="p.is_demo" class="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Prodotto demo</span>
        </div>
        <p class="text-sm text-stone-500">{{ p.brand }}</p>
        <h3 class="text-lg font-semibold leading-tight">{{ p.name }}</h3>
        <p v-if="item.why" class="mt-1 text-sm italic text-stone-500">{{ item.why }}</p>

        <ul class="mt-3 space-y-1">
          <RecommendationReason v-for="r in reasons" :key="r" :text="r" kind="ok" />
          <RecommendationReason v-for="r in item.explain.penalties" :key="r" :text="r" kind="penalty" />
        </ul>

        <div v-if="item.downgrade || item.upgrade" class="mt-4 flex flex-wrap gap-2">
          <button
            v-if="item.downgrade"
            type="button"
            class="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100 disabled:opacity-50"
            :disabled="loading"
            :title="item.downgrade.product.name"
            @click="$emit('swap', item.downgrade.product.id)"
          >
            Risparmia {{ delta(item.downgrade.price_delta) }}<span v-if="item.downgrade.price_is_estimate">*</span>
          </button>
          <button
            v-if="item.upgrade"
            type="button"
            class="rounded-lg border border-brand-500 px-3 py-1.5 text-sm text-brand-700 hover:bg-brand-50 disabled:opacity-50"
            :disabled="loading"
            :title="item.upgrade.product.name"
            @click="$emit('swap', item.upgrade.product.id)"
          >
            Migliora (+{{ delta(item.upgrade.price_delta) }}<span v-if="item.upgrade.price_is_estimate">*</span>)
          </button>
        </div>
      </div>

      <div class="sm:w-56">
        <ProductPriceCta :product="p" :session-id="sessionId" context="configurator" />
      </div>
    </div>
  </article>
</template>
