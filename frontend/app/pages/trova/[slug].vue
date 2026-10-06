<script setup lang="ts">
import type { FinderDetail } from '~/types/api'

const route = useRoute()
const slug = route.params.slug as string
const api = useApi()
const config = useRuntimeConfig()

const { data: finder, error } = await useAsyncData(`finder-${slug}`, () => api.get<FinderDetail>(`/api/finders/${slug}`))
if (error.value || !finder.value) {
  throw createError({ statusCode: 404, statusMessage: 'Pagina non trovata', fatal: true })
}

const sessionFromUrl = computed(() => (typeof route.query.s === 'string' ? route.query.s : null))
const canonical = `${config.public.siteUrl}/trova/${slug}`

useSeoMeta({
  title: () => finder.value!.seo.title,
  description: () => finder.value!.seo.description,
  ogTitle: () => finder.value!.seo.title,
  ogDescription: () => finder.value!.seo.description,
  ogUrl: canonical,
  ogType: 'website',
  // i risultati personali (?s=...) non vanno indicizzati
  robots: () => (sessionFromUrl.value ? 'noindex, follow' : 'index, follow'),
})

useHead({
  link: [{ rel: 'canonical', href: canonical }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: `${config.public.siteUrl}/` },
          { '@type': 'ListItem', position: 2, name: finder.value.title, item: canonical },
        ],
      }),
    },
  ],
})
</script>

<template>
  <div v-if="finder">
    <nav class="mb-4 text-sm text-stone-500" aria-label="Breadcrumb">
      <NuxtLink to="/" class="hover:underline">Home</NuxtLink> / <span>{{ finder.title }}</span>
    </nav>
    <header class="mb-8">
      <h1 class="text-3xl font-bold tracking-tight sm:text-4xl">{{ finder.seo.h1 }}</h1>
      <p class="mt-3 max-w-3xl text-lg text-stone-600">{{ finder.seo.intro }}</p>
    </header>

    <ClientOnly>
      <FinderContainer :finder="finder" :session-from-url="sessionFromUrl" />
      <template #fallback>
        <div class="rounded-3xl bg-white/60 p-8 text-center text-stone-500 ring-1 ring-stone-200">Caricamento…</div>
      </template>
    </ClientOnly>

    <p class="mt-10 text-stone-600">
      Vuoi capire prima cosa guardare?
      <NuxtLink :to="`/come-scegliere/${finder.slug}`" class="font-semibold text-brand-700 underline">Leggi la guida alla scelta</NuxtLink>.
    </p>
  </div>
</template>
