<script setup lang="ts">
import type { ChatMessage } from '~/composables/useAdvisor'

defineProps<{ message: ChatMessage }>()
</script>

<template>
  <div v-if="message.role === 'user'" class="flex justify-end">
    <p class="max-w-[85%] whitespace-pre-line rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-white">{{ message.text }}</p>
  </div>

  <div v-else class="flex gap-3">
    <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700" aria-hidden="true">AI</div>
    <div class="min-w-0 max-w-[92%] space-y-3">
      <p class="whitespace-pre-line rounded-2xl rounded-tl-sm bg-white px-4 py-2.5 shadow-sm ring-1 ring-stone-200">{{ message.text }}</p>

      <div v-if="message.reply?.understood.length" class="flex flex-wrap gap-1.5">
        <span class="text-xs text-stone-500">Ho capito:</span>
        <span v-for="u in message.reply.understood" :key="u" class="rounded-full bg-stone-100 px-2.5 py-0.5 text-xs text-stone-600">{{ u }}</span>
      </div>

      <!-- risultato Product Finder: prime 3 proposte -->
      <div v-if="message.reply?.finder_result?.slots.length" class="grid gap-3 sm:grid-cols-3">
        <div
          v-for="s in message.reply.finder_result.slots.slice(0, 3)"
          :key="s.product.id"
          class="flex flex-col rounded-xl bg-white p-4 shadow-sm ring-1 ring-stone-200"
        >
          <p class="text-xs font-semibold text-brand-700">{{ s.label }}</p>
          <p class="mt-1 text-sm text-stone-500">{{ s.product.brand }}</p>
          <p class="font-semibold leading-tight">{{ s.product.name }}</p>
          <p v-if="s.explain.reasons[0]" class="mt-2 text-sm text-stone-600">{{ s.explain.reasons[0] }}</p>
          <div class="mt-auto pt-3">
            <ProductPriceCta :product="s.product" :session-id="message.reply.finder_result.session_id" context="advisor" />
          </div>
        </div>
      </div>

      <!-- risultato Configuratore: riepilogo kit -->
      <div v-if="message.reply?.configuration" class="rounded-xl bg-white p-4 shadow-sm ring-1 ring-stone-200">
        <ul class="divide-y divide-stone-100">
          <li v-for="it in message.reply.configuration.items" :key="it.component_key" class="flex items-center justify-between gap-3 py-2 text-sm">
            <span><span class="text-stone-500">{{ it.label }}:</span> <span class="font-medium">{{ it.product.name }}</span></span>
            <span class="shrink-0 font-semibold">{{ it.product.offer?.price != null ? formatPrice(it.product.offer.price) : '—' }}</span>
          </li>
        </ul>
        <p class="mt-2 flex justify-between border-t border-stone-200 pt-2 font-semibold">
          <span>Totale (prezzi aggiornati)</span><span>{{ formatPrice(message.reply.configuration.total_valid) }}</span>
        </p>
      </div>

      <NuxtLink
        v-if="message.reply?.open_url"
        :to="message.reply.open_url"
        class="inline-block rounded-xl bg-brand-600 px-5 py-2.5 font-semibold text-white hover:bg-brand-700"
      >
        {{ message.reply.open_label }} →
      </NuxtLink>
    </div>
  </div>
</template>
