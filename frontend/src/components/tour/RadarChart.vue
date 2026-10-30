<script setup>
import { computed, ref, onMounted, watch } from 'vue'

const props = defineProps({
  scores: Object,
  labels: Object,
})

const canvasRef = ref(null)

const dimensions = computed(() => Object.entries(props.labels || {}).map(([key, label]) => ({ key, label })))

function drawChart() {
  const canvas = canvasRef.value
  if (!canvas || !props.scores) return

  const ctx = canvas.getContext('2d')
  const w = canvas.width = canvas.offsetWidth * 2
  const h = canvas.height = canvas.offsetHeight * 2
  ctx.scale(2, 2)
  const cw = canvas.offsetWidth
  const ch = canvas.offsetHeight
  const cx = cw / 2
  const cy = ch / 2
  const maxR = Math.min(cx, cy) - 40

  ctx.clearRect(0, 0, cw, ch)

  const n = dimensions.value.length
  if (!n) return
  const angleStep = (Math.PI * 2) / n

  for (let level = 1; level <= 3; level++) {
    const r = (maxR * level) / 3
    ctx.beginPath()
    for (let i = 0; i <= n; i++) {
      const angle = i * angleStep - Math.PI / 2
      const x = cx + r * Math.cos(angle)
      const y = cy + r * Math.sin(angle)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)'
    ctx.stroke()
  }

  for (let i = 0; i < n; i++) {
    const angle = i * angleStep - Math.PI / 2
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(cx + maxR * Math.cos(angle), cy + maxR * Math.sin(angle))
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.05)'
    ctx.stroke()

    const labelR = maxR + 20
    const lx = cx + labelR * Math.cos(angle)
    const ly = cy + labelR * Math.sin(angle)
    ctx.fillStyle = 'rgba(26, 24, 22, 0.6)'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(dimensions.value[i].label, lx, ly)
  }

  ctx.beginPath()
  for (let i = 0; i <= n; i++) {
    const idx = i % n
    const score = props.scores[dimensions.value[idx].key] || 1
    const r = (maxR * score) / 3
    const angle = idx * angleStep - Math.PI / 2
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.fillStyle = 'rgba(169, 76, 44, 0.15)'
  ctx.fill()
  ctx.strokeStyle = '#a94c2c'
  ctx.lineWidth = 2
  ctx.stroke()

  for (let i = 0; i < n; i++) {
    const score = props.scores[dimensions.value[i].key] || 1
    const r = (maxR * score) / 3
    const angle = i * angleStep - Math.PI / 2
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#a94c2c'
    ctx.fill()
  }
}

onMounted(drawChart)
watch(() => [props.scores, props.labels], drawChart, { deep: true })
</script>

<template>
  <div class="radar-chart">
    <h3 class="section-title">游览五型图</h3>
    <canvas ref="canvasRef" class="chart-canvas" />
    <div class="level-legend">
      <span>B级</span><span>A级</span><span>S级</span>
    </div>
  </div>
</template>

<style scoped>
.radar-chart {
  margin-bottom: 32px;
  text-align: center;
}

.section-title {
  font-size: 18px;
  color: var(--color-text-primary);
  margin-bottom: 16px;
}

.chart-canvas {
  width: 300px;
  height: 300px;
  margin: 0 auto;
  display: block;
}

.level-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-muted);
}
</style>
