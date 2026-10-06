<script setup lang="ts">
import type { SlotOut } from '~/types/api'

const props = defineProps<{ slots: SlotOut[]; labels: Record<string, string> }>()
const keys = computed(() => Object.keys(props.labels))
</script>

<template>
  <div class="overflow-x-auto rounded-2xl border border-stone-200 bg-white">
    <table class="w-full min-w-[560px] text-sm">
      <thead>
        <tr class="border-b border-stone-200 bg-stone-50 text-left">
          <th class="p-3 font-semibold">Caratteristica</th>
          <th v-for="s in slots" :key="s.product.id" class="p-3 font-semibold">{{ s.product.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="k in keys" :key="k" class="border-b border-stone-100 last:border-0">
          <td class="p-3 text-stone-500">{{ labels[k] }}</td>
          <td v-for="s in slots" :key="s.product.id" class="p-3">{{ formatAttr(k, s.product.attributes[k]) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
