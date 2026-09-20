<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const STATUS_LABEL = { idle: '空闲', running: '在跑', stopped: '已停表' }

const state = ref(null)
const distance_km = ref(0)
const slow_min = ref(0)
const night = ref(false)
const errorMsg = ref('')
const lastRunId = ref(null)

const sync = (s) => {
  state.value = s
  distance_km.value = s.distance_km
  slow_min.value = s.slow_min
  night.value = s.night
}

const refresh = async () => { sync(await getJSON('/api/meter')) }

const call = async (path, body) => {
  errorMsg.value = ''
  try {
    const s = await postJSON(path, body)
    if (path.endsWith('/checkout')) {
      lastRunId.value = s.run_id
      await refresh()
    } else {
      sync(s)
    }
  } catch (e) {
    errorMsg.value = String(e.message || e)
  }
}

const start = () => call('/api/meter/start', { night: night.value })
const update = () => call('/api/meter/readings', { distance_km: distance_km.value, slow_min: slow_min.value })
const stop = () => call('/api/meter/stop')
const checkout = () => call('/api/meter/checkout')

onMounted(refresh)
</script>

<template>
  <div class="page" v-if="state">
    <h1>打表计价器</h1>
    <div class="panel">
      <span class="status-badge" :class="state.status">{{ STATUS_LABEL[state.status] }}</span>
      <span v-if="state.status === 'stopped'" class="hint">快照已冻结，落表后回到空闲才能重新开表</span>
      <span v-if="lastRunId" class="hint">上一单已落表：记录 #{{ lastRunId }}</span>
    </div>

    <div class="panel">
      <label>公里 <input type="number" min="0" v-model.number="distance_km" :disabled="state.status !== 'running'" /></label>
      <label>低速分钟 <input type="number" min="0" v-model.number="slow_min" :disabled="state.status !== 'running'" /></label>
      <label><input type="checkbox" v-model="night" :disabled="state.status !== 'idle'" /> 夜间</label>
    </div>

    <div class="panel meter-actions">
      <button :disabled="state.status !== 'idle'" @click="start">开表</button>
      <button :disabled="state.status !== 'running'" @click="update">更新读数</button>
      <button class="btn-warn" :disabled="state.status !== 'running'" @click="stop">停表</button>
      <button class="btn-primary" :disabled="state.status !== 'stopped'" @click="checkout">落表</button>
    </div>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div v-if="state.status === 'running' && state.live" class="panel breakdown">
      <h2>在跑读数（实时）</h2>
      <p class="hero-num">¥{{ state.live.total }}</p>
      <p>起步 {{ state.live.start }} · 里程 {{ state.live.mileage }} · 低速 {{ state.live.slow_fee }}</p>
    </div>

    <div v-if="state.status === 'stopped' && state.snapshot" class="panel breakdown frozen">
      <h2>停表快照</h2>
      <p class="hero-num">¥{{ state.snapshot.fare.total }}</p>
      <p>起步 {{ state.snapshot.fare.start }} · 里程 {{ state.snapshot.fare.mileage }} · 低速 {{ state.snapshot.fare.slow_fee }}</p>
      <p class="hint">
        读表 {{ state.snapshot.inputs.distance_km }} 公里 / {{ state.snapshot.inputs.slow_min }} 分钟{{ state.snapshot.inputs.night ? ' / 夜间' : '' }}
      </p>
    </div>

    <div v-if="state.status === 'idle'" class="panel hint">空闲中：勾选夜间后开表，在跑期间可多次更新读数，停表后核对快照再落表。</div>
  </div>
</template>

<style scoped>
.status-badge { padding: 0.2rem 0.7rem; border-radius: 999px; font-weight: 700; }
.status-badge.idle { background: #444; color: #ccc; }
.status-badge.running { background: #1f5130; color: #7ee29a; }
.status-badge.stopped { background: #5a3a12; color: var(--accent); }
.meter-actions { display: flex; gap: 0.6rem; }
button:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary { font-weight: 700; }
.btn-warn { background: #d98a2b; }
.hint { color: var(--muted); margin-left: 0.8rem; }
.error { color: #ff8080; }
.breakdown h2 { margin: 0 0 0.4rem; font-size: 1rem; color: var(--muted); }
.frozen { outline: 2px solid var(--accent); }
</style>
