<script setup lang="ts">
import type { ConfiguratorSummary, FinderSummary } from '~/types/api'

const api = useApi()
const config = useRuntimeConfig()
const { data: finders } = await useAsyncData('finders', () => api.get<FinderSummary[]>('/api/finders'))
const { data: configurators } = await useAsyncData('configurators', () =>
  api.get<ConfiguratorSummary[]>('/api/configurators'),
)

useSeoMeta({
  title: `${config.public.siteName} · Scopri cosa comprare in base a come lo userai`,
  description: 'Strumenti gratuiti che ti aiutano a scegliere il prodotto giusto in base a uso, esperienza e budget.',
  ogTitle: config.public.siteName,
})
useHead({ link: [{ rel: 'canonical', href: `${config.public.siteUrl}/` }] })
</script>

<template>
  <div>
    <section class="py-6 text-center sm:py-12">
      <h1 class="text-4xl font-bold tracking-tight sm:text-5xl">Non il prodotto migliore.<br />Quello giusto per te.</h1>
      <p class="mx-auto mt-4 max-w-2xl text-lg text-stone-600">
        Rispondi a poche domande su come userai il prodotto e quanto vuoi spendere:
        confrontiamo i modelli e ti spieghiamo perché te li consigliamo.
      </p>
    </section>

    <NuxtLink
      to="/consulente"
      class="mb-5 block rounded-2xl bg-brand-600 p-6 text-white shadow-sm transition hover:bg-brand-700"
    >
      <h2 class="text-xl font-semibold">Non sai da dove iniziare? Chiedi al consulente</h2>
      <p class="mt-1 text-brand-50">Scrivi con parole tue cosa ti serve e quanto vuoi spendere.</p>
    </NuxtLink>

    <section class="grid gap-5 sm:grid-cols-2">
      <NuxtLink
        v-for="f in finders ?? []"
        :key="f.slug"
        :to="`/trova/${f.slug}`"
        class="group rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition hover:border-brand-500"
      >
        <h2 class="text-xl font-semibold group-hover:text-brand-700">{{ f.title }}</h2>
        <p class="mt-2 text-stone-600">{{ f.short_description }}</p>
        <span class="mt-4 inline-block font-semibold text-brand-600">Trova il prodotto giusto →</span>
      </NuxtLink>
      <NuxtLink
        v-for="c in configurators ?? []"
        :key="c.slug"
        :to="`/configura/${c.slug}`"
        class="group rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition hover:border-brand-500"
      >
        <h2 class="text-xl font-semibold group-hover:text-brand-700">{{ c.title }}</h2>
        <p class="mt-2 text-stone-600">{{ c.short_description }}</p>
        <span class="mt-4 inline-block font-semibold text-brand-600">Componi il kit →</span>
      </NuxtLink>
    </section>
  </div>
</template>
