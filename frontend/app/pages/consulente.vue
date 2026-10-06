<script setup lang="ts">
const config = useRuntimeConfig()
const canonical = `${config.public.siteUrl}/consulente`

useSeoMeta({
  title: `Consulente per l'attrezzatura da trekking | ${config.public.siteName}`,
  description:
    "Descrivi cosa devi fare e quanto vuoi spendere: il consulente ti fa poche domande mirate e ti propone scarpe o un kit completo, spiegandoti il perché.",
  ogTitle: "Consulente per l'attrezzatura da trekking",
  ogUrl: canonical,
  ogType: 'website',
})
useHead({ link: [{ rel: 'canonical', href: canonical }] })
</script>

<template>
  <div class="mx-auto max-w-3xl">
    <nav class="mb-4 text-sm text-stone-500" aria-label="Breadcrumb">
      <NuxtLink to="/" class="hover:underline">Home</NuxtLink> / <span>Consulente</span>
    </nav>
    <header class="mb-6">
      <h1 class="text-3xl font-bold tracking-tight sm:text-4xl">Chiedi al consulente</h1>
      <p class="mt-3 text-lg text-stone-600">
        Scrivi con parole tue cosa devi fare, che esperienza hai e quanto vuoi spendere.
        Ti faccio solo le domande indispensabili e ti propongo cosa comprare.
      </p>
    </header>

    <ClientOnly>
      <AdvisorChat />
      <template #fallback>
        <div class="rounded-3xl bg-stone-100/70 p-8 text-center text-stone-500 ring-1 ring-stone-200">Caricamento…</div>
      </template>
    </ClientOnly>

    <AffiliateDisclosure class="mt-6" />
  </div>
</template>
