<script setup lang="ts">
const config = useRuntimeConfig()
const siteName = config.public.siteName
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <header class="border-b border-stone-200 bg-white">
      <nav class="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <NuxtLink to="/" class="text-lg font-bold text-brand-700">{{ siteName }}</NuxtLink>
        <div class="flex gap-5">
          <NuxtLink to="/trova/scarpe-trekking" class="text-sm font-medium text-stone-600 hover:text-brand-700">Trova la scarpa</NuxtLink>
          <NuxtLink to="/configura/kit-trekking" class="text-sm font-medium text-stone-600 hover:text-brand-700">Componi il kit</NuxtLink>
        </div>
      </nav>
    </header>
    <main class="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:py-12">
      <slot />
    </main>
    <footer class="border-t border-stone-200 bg-white">
      <div class="mx-auto max-w-5xl space-y-2 px-4 py-6">
        <AffiliateDisclosure compact />
        <p class="text-xs text-stone-500">
          © {{ new Date().getFullYear() }} {{ siteName }} ·
          <NuxtLink to="/informativa-affiliazione" class="underline">Informativa affiliazione</NuxtLink>
        </p>
      </div>
    </footer>
  </div>
</template>
