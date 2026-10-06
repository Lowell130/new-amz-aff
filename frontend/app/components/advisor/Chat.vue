<script setup lang="ts">
const chat = useAdvisor()
const list = ref<HTMLElement | null>(null)

onMounted(() => chat.start())

watch(
  () => chat.messages.value.length,
  async () => {
    await nextTick()
    list.value?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  },
)
</script>

<template>
  <div class="flex flex-col gap-4 rounded-3xl bg-stone-100/70 p-4 ring-1 ring-stone-200 sm:p-6">
    <div ref="list" class="space-y-4" aria-live="polite">
      <AdvisorMessage v-for="m in chat.messages.value" :key="m.id" :message="m" />
      <div v-if="chat.loading.value" class="flex gap-3" aria-label="Il consulente sta scrivendo">
        <div class="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">AI</div>
        <p class="rounded-2xl bg-white px-4 py-2.5 text-stone-400 shadow-sm ring-1 ring-stone-200">Sto pensando…</p>
      </div>
    </div>

    <p v-if="chat.error.value" class="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{{ chat.error.value }}</p>

    <AdvisorQuickReply
      v-if="chat.lastReply.value?.quick_replies.length"
      :replies="chat.lastReply.value.quick_replies"
      :disabled="chat.loading.value"
      @pick="chat.quick"
    />
    <AdvisorInput :disabled="chat.loading.value || !chat.sessionId.value" @send="chat.send" />
    <p class="text-xs text-stone-500">
      I prodotti sono scelti dal nostro motore di confronto in base alle tue risposte; il testo è generato
      automaticamente a partire da quei dati. Non salviamo il testo dei tuoi messaggi.
    </p>
  </div>
</template>
