<script setup lang="ts">
import type { ConfiguratorDetail } from '~/types/api'

const route = useRoute()
const slug = route.params.slug as string
const api = useApi()
const config = useRuntimeConfig()

const { data: detail, error: loadError } = await useAsyncData(`configurator-${slug}`, () =>
  api.get<ConfiguratorDetail>(`/api/configurators/${slug}`),
)
if (loadError.value || !detail.value) {
  throw createError({ statusCode: 404, statusMessage: 'Pagina non trovata', fatal: true })
}

const cfg = useConfigurator(detail.value)
const sessionFromUrl = computed(() => (typeof route.query.c === 'string' ? route.query.c : null))
const canonical = `${config.public.siteUrl}/configura/${slug}`

onMounted(() => {
  if (sessionFromUrl.value) cfg.load(sessionFromUrl.value)
})
watch(sessionFromUrl, (id) => {
  if (id) cfg.load(id)
})

useSeoMeta({
  title: () => detail.value!.seo.title,
  description: () => detail.value!.seo.description,
  ogTitle: () => detail.value!.seo.title,
  ogDescription: () => detail.value!.seo.description,
  ogUrl: canonical,
  ogType: 'website',
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
          { '@type': 'ListItem', position: 2, name: detail.value.title, item: canonical },
        ],
      }),
    },
  ],
})
</script>

<template>
  <div v-if="detail">
    <nav class="mb-4 text-sm text-stone-500" aria-label="Breadcrumb">
      <NuxtLink to="/" class="hover:underline">Home</NuxtLink> / <span>{{ detail.title }}</span>
    </nav>
    <header class="mb-8">
      <h1 class="text-3xl font-bold tracking-tight sm:text-4xl">{{ detail.seo.h1 }}</h1>
      <p class="mt-3 max-w-3xl text-lg text-stone-600">{{ detail.seo.intro }}</p>
    </header>

    <ClientOnly>
      <p v-if="cfg.error.value" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{{ cfg.error.value }}</p>

      <div v-if="!cfg.result.value" class="rounded-3xl bg-white/60 p-5 shadow-sm ring-1 ring-stone-200 sm:p-8">
        <p v-if="sessionFromUrl && cfg.loading.value" class="text-center text-stone-500">Caricamento del kit…</p>
        <ConfiguratorForm
          v-else
          v-model:answers="cfg.answers.value"
          v-model:optional="cfg.optional.value"
          :detail="detail"
          :loading="cfg.loading.value"
          @submit="cfg.build"
        />
      </div>

      <div v-else class="space-y-5">
        <ConfiguratorSummary :config="cfg.result.value" @edit="cfg.edit" />
        <ConfiguratorItem
          v-for="it in cfg.result.value.items"
          :key="it.component_key"
          :item="it"
          :session-id="cfg.result.value.session_id"
          :loading="cfg.loading.value"
          @swap="(pid: string) => cfg.swap(it.component_key, pid)"
        />
        <div v-if="cfg.result.value.skipped.length" class="rounded-2xl bg-stone-100 p-4 text-sm text-stone-600">
          <p class="font-semibold text-stone-700">Componenti non inclusi</p>
          <ul class="mt-1 list-inside list-disc">
            <li v-for="s in cfg.result.value.skipped" :key="s.component_key">{{ s.label }}: {{ s.reason.toLowerCase() }}</li>
          </ul>
        </div>
        <p class="text-xs text-stone-500">* Differenza calcolata su un prezzo stimato: verifica il prezzo aggiornato su Amazon.</p>
        <AffiliateDisclosure />
      </div>

      <template #fallback>
        <div class="rounded-3xl bg-white/60 p-8 text-center text-stone-500 ring-1 ring-stone-200">Caricamento…</div>
      </template>
    </ClientOnly>
  </div>
</template>
