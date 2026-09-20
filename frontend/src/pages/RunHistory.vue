<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const open = ref(null)
const parse = (s) => { try { return JSON.parse(s) } catch { return null } }
const toggle = (id) => { open.value = open.value === id ? null : id }
onMounted(async () => {
  const raw = (await getJSON('/api/history')).items
  items.value = raw.map(h => ({ ...h, r: parse(h.result_json) }))
})
</script>
<template>
  <div class="page"><h1>记录</h1>
    <table>
      <template v-for="h in items" :key="h.id">
        <tr class="rowlink" @click="toggle(h.id)">
          <td>#{{ h.id }}</td><td>{{ h.kind }}</td><td>{{ h.created_at }}</td>
        </tr>
        <tr v-if="open === h.id && h.r" class="breakdown"><td colspan="3">
          <template v-if="h.r.total !== undefined">
            起步 {{ h.r.start }} · 里程 {{ h.r.mileage }} · 低速 {{ h.r.slow_fee }} · 应付 {{ h.r.total }}
          </template>
          <template v-else-if="h.r.day_total !== undefined">
            白天 ¥{{ h.r.day_total }} · 夜间 ¥{{ h.r.night_total }} · 差 ¥{{ h.r.delta }}
          </template>
        </td></tr>
      </template>
    </table>
  </div>
</template>
