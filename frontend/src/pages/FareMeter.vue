<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const STATE_LABEL = { idle: '空闲', running: '在跑', stopped: '已停表' }

const meter = ref(null)
const night = ref(false)
const distance_km = ref(0)
const slow_min = ref(0)
const err = ref('')
const settledId = ref(null)

const state = computed(() => meter.value?.state || 'idle')
const live = computed(() => meter.value?.live)
const snapshot = computed(() => meter.value?.snapshot)

const refresh = async () => { meter.value = await getJSON('/api/meter') }
const act = async (p) => {
  err.value = ''
  try { const r = await p; await refresh(); return r } catch (e) { err.value = e.message }
}
const start = () => { settledId.value = null; act(postJSON('/api/meter/start', { night: night.value })) }
const update = () => act(postJSON('/api/meter/reading', { distance_km: distance_km.value, slow_min: slow_min.value }))
const stop = () => act(postJSON('/api/meter/stop', {}))
const settle = async () => { const r = await act(postJSON('/api/meter/settle', {})); if (r) settledId.value = r.run_id }

onMounted(async () => {
  await refresh()
  const r = meter.value.reading
  distance_km.value = r.distance_km
  slow_min.value = r.slow_min
  night.value = r.night
})
</script>
<template>
  <div class="page"><h1>打表</h1>
    <div class="panel">
      <span class="badge" :class="state">{{ STATE_LABEL[state] }}</span>
      <span v-if="settledId" class="ok">已落表，记录 #{{ settledId }}</span>
      <p v-if="err" class="err">{{ err }}</p>
    </div>
    <div class="panel">
      <label><input type="checkbox" v-model="night" :disabled="state !== 'idle'" /> 夜间</label>
      <label>公里 <input type="number" v-model.number="distance_km" :disabled="state !== 'running'" /></label>
      <label>低速分钟 <input type="number" v-model.number="slow_min" :disabled="state !== 'running'" /></label>
      <div class="actions">
        <button @click="start" :disabled="state !== 'idle'">开表</button>
        <button @click="update" :disabled="state !== 'running'">更新读数</button>
        <button @click="stop" :disabled="state !== 'running'">停表</button>
        <button @click="settle" :disabled="state !== 'stopped'">落表</button>
      </div>
    </div>
    <div v-if="state === 'running' && live" class="panel">
      <h2>在跑读数</h2>
      <p class="hero-num">¥{{ live.total }}</p>
      <p>起步 {{ live.start }} · 里程 {{ live.mileage }} · 低速 {{ live.slow_fee }}</p>
    </div>
    <div v-if="state === 'stopped' && snapshot" class="panel">
      <h2>停表快照（已冻结）</h2>
      <p class="hero-num">¥{{ snapshot.total }}</p>
      <p>起步 {{ snapshot.start }} · 里程 {{ snapshot.mileage }} · 低速 {{ snapshot.slow_fee }}</p>
    </div>
  </div>
</template>
