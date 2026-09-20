<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'

const items = ref([])
const openId = ref(null)

const parse = (raw) => {
  try { return JSON.parse(raw) } catch { return null }
}

const toggle = (id) => { openId.value = openId.value === id ? null : id }

onMounted(async () => {
  const raw = (await getJSON('/api/history')).items
  items.value = raw.map((h) => ({ ...h, result: parse(h.result_json) }))
})
</script>

<template>
  <div class="page">
    <h1>记录</h1>
    <table>
      <tr v-for="h in items" :key="h.id">
        <td>
          <a href="#" @click.prevent="toggle(h.id)">{{ openId === h.id ? '▾' : '▸' }} #{{ h.id }}</a>
        </td>
        <td>{{ h.kind }}</td>
        <td class="amount">¥{{ h.result?.total ?? '—' }}</td>
      </tr>
    </table>

    <div v-for="h in items" :key="'d' + h.id">
      <div v-if="openId === h.id" class="panel breakdown">
        <template v-if="h.kind === 'fare' && h.result">
          <h2>记录 #{{ h.id }} 拆解</h2>
          <p class="hero-num">¥{{ h.result.total }}</p>
          <p>起步 {{ h.result.start }} · 里程 {{ h.result.mileage }} · 低速 {{ h.result.slow_fee }}</p>
          <p class="hint">{{ h.result.distance_km }} 公里 / {{ h.result.slow_min }} 分钟{{ h.result.night ? ' / 夜间（系数 ' + h.result.night_factor + '）' : '' }}</p>
        </template>
        <template v-else>
          <h2>记录 #{{ h.id }} 结果</h2>
          <pre>{{ JSON.stringify(h.result, null, 2) }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.amount { color: var(--accent); font-weight: 700; text-align: right; }
.breakdown h2 { margin: 0 0 0.4rem; font-size: 1rem; color: var(--muted); }
.hint { color: var(--muted); }
pre { white-space: pre-wrap; }
</style>
