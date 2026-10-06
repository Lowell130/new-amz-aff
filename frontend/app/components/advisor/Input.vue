<script setup lang="ts">
const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ send: [text: string] }>()
const text = ref('')

function submit() {
  if (props.disabled || !text.value.trim()) return
  emit('send', text.value)
  text.value = ''
}
</script>

<template>
  <form class="flex gap-2" @submit.prevent="submit">
    <label for="advisor-input" class="sr-only">Scrivi al consulente</label>
    <textarea
      id="advisor-input"
      v-model="text"
      rows="2"
      maxlength="1000"
      class="min-h-[3rem] flex-1 resize-none rounded-xl border border-stone-300 bg-white px-4 py-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
      placeholder="Es. Ho 300 euro, voglio iniziare a fare escursioni in montagna…"
      @keydown.enter.exact.prevent="submit"
    />
    <button
      type="submit"
      class="shrink-0 self-end rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-40"
      :disabled="disabled || !text.trim()"
    >
      Invia
    </button>
  </form>
</template>
