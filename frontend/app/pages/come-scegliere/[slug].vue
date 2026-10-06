<script setup lang="ts">
import type { FinderDetail } from '~/types/api'

const route = useRoute()
const slug = route.params.slug as string
const api = useApi()
const config = useRuntimeConfig()

const { data: finder, error } = await useAsyncData(`guide-${slug}`, () => api.get<FinderDetail>(`/api/finders/${slug}`))
if (error.value || !finder.value) {
  throw createError({ statusCode: 404, statusMessage: 'Pagina non trovata', fatal: true })
}

const title = `Come scegliere: ${finder.value.title.toLowerCase()}`
const canonical = `${config.public.siteUrl}/come-scegliere/${slug}`

useSeoMeta({
  title: `${title} | Guida pratica`,
  description: finder.value.seo.description,
  ogTitle: title,
  ogUrl: canonical,
  ogType: 'article',
})
useHead({
  link: [{ rel: 'canonical', href: canonical }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: finder.value.seo.faq.map((x) => ({
          '@type': 'Question',
          name: x.q,
          acceptedAnswer: { '@type': 'Answer', text: x.a },
        })),
      }),
    },
  ],
})
</script>

<template>
  <article v-if="finder" class="mx-auto max-w-3xl">
    <nav class="mb-4 text-sm text-stone-500" aria-label="Breadcrumb">
      <NuxtLink to="/" class="hover:underline">Home</NuxtLink> / <span>Guida</span>
    </nav>
    <h1 class="text-3xl font-bold tracking-tight sm:text-4xl">{{ title }}</h1>
    <p class="mt-3 text-lg text-stone-600">{{ finder.seo.intro }}</p>

    <section v-for="s in finder.seo.guide_sections" :key="s.title" class="mt-8">
      <h2 class="text-xl font-semibold">{{ s.title }}</h2>
      <p class="mt-2 leading-relaxed text-stone-700">{{ s.body }}</p>
    </section>

    <div class="my-10 rounded-2xl bg-brand-50 p-6">
      <p class="font-semibold">Preferisci una risposta su misura?</p>
      <NuxtLink :to="`/trova/${finder.slug}`" class="mt-3 inline-block rounded-xl bg-brand-600 px-6 py-3 font-semibold text-white hover:bg-brand-700">
        Usa lo strumento di scelta
      </NuxtLink>
    </div>

    <section v-if="finder.seo.faq.length">
      <h2 class="text-xl font-semibold">Domande frequenti</h2>
      <details v-for="x in finder.seo.faq" :key="x.q" class="mt-3 rounded-xl border border-stone-200 bg-white p-4">
        <summary class="cursor-pointer font-medium">{{ x.q }}</summary>
        <p class="mt-2 text-stone-700">{{ x.a }}</p>
      </details>
    </section>
  </article>
</template>
