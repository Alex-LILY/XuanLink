<template>
  <canvas ref="canvasEl" class="star-canvas"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  theme: { type: String, default: 'modern' }
})

const canvasEl = ref(null)
let rafId = null
let stars = []
let nebulae = []
let glowDots = []
let shootingStars = []
let nextShootFrame = 0
let w = 0
let h = 0
let t = 0
let cfg = null

function themeConfig() {
  switch (props.theme) {
    case 'cyber':
      return {
        palette: [[0, 240, 255], [255, 0, 212], [0, 180, 230]],
        lineColor: [0, 240, 255],
        starCount: 480,
        glowCount: 35,
        nebulaCount: 6,
        constellationDist: 100,
        shootInterval: 100,
        starAlphaScale: 0.85,
      }
    case 'terminal':
      return {
        palette: [[34, 197, 94], [80, 240, 130], [160, 255, 185]],
        lineColor: [34, 197, 94],
        starCount: 450,
        glowCount: 28,
        nebulaCount: 5,
        constellationDist: 95,
        shootInterval: 130,
        starAlphaScale: 0.85,
      }
    case 'glass':
      return {
        palette: [[168, 85, 247], [45, 212, 191], [244, 63, 94]],
        lineColor: [168, 85, 247],
        starCount: 500,
        glowCount: 38,
        nebulaCount: 7,
        constellationDist: 100,
        shootInterval: 90,
        starAlphaScale: 0.9,
      }
    case 'paper':
      return {
        palette: [[236, 64, 122], [124, 77, 255], [38, 198, 218]],
        lineColor: [200, 150, 255],
        starCount: 420,
        glowCount: 32,
        nebulaCount: 6,
        constellationDist: 90,
        shootInterval: 110,
        starAlphaScale: 0.75,
      }
    case 'nova':
      return {
        palette: [[124, 58, 237], [59, 130, 246], [167, 139, 250]],
        lineColor: [124, 58, 237],
        starCount: 520,
        glowCount: 44,
        nebulaCount: 8,
        constellationDist: 108,
        shootInterval: 82,
        starAlphaScale: 0.88,
      }
    default: // modern
      return {
        palette: [[99, 102, 241], [34, 211, 238], [139, 92, 246]],
        lineColor: [99, 102, 241],
        starCount: 500,
        glowCount: 32,
        nebulaCount: 6,
        constellationDist: 100,
        shootInterval: 110,
        starAlphaScale: 0.6,
      }
  }
}

function mkStars(n) {
  return Array.from({ length: n }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 1.6 + 0.2,
    phase: Math.random() * Math.PI * 2,
    spd: Math.random() * 0.45 + 0.1,
    base: Math.random() * 0.55 + 0.35,
    colorIdx: Math.floor(Math.random() * 3),
    dx: (Math.random() - 0.5) * 0.1,
    dy: (Math.random() - 0.5) * 0.1,
  }))
}

function mkGlow(n) {
  return Array.from({ length: n }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 3 + 1.2,
    phase: Math.random() * Math.PI * 2,
    spd: Math.random() * 0.12 + 0.03,
    vx: (Math.random() - 0.5) * 0.2,
    vy: (Math.random() - 0.5) * 0.2,
    base: Math.random() * 0.22 + 0.05,
    colorIdx: Math.floor(Math.random() * 3),
  }))
}

function mkNebulae(n) {
  return Array.from({ length: n }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 200 + 90,
    phase: Math.random() * Math.PI * 2,
    spd: Math.random() * 0.006 + 0.002,
    colorIdx: Math.floor(Math.random() * 3),
    base: Math.random() * 0.05 + 0.015,
  }))
}

function mkShooting() {
  return {
    x: Math.random() * w * 0.8 + w * 0.05,
    y: Math.random() * h * 0.45,
    angle: Math.PI * 0.22 + (Math.random() - 0.5) * 0.5,
    speed: Math.random() * 7 + 5,
    life: 0,
    maxLife: Math.random() * 45 + 30,
    len: Math.random() * 130 + 60,
  }
}

function resize() {
  if (!canvasEl.value) return
  w = window.innerWidth
  h = window.innerHeight
  canvasEl.value.width = w
  canvasEl.value.height = h
  cfg = themeConfig()
  stars = mkStars(cfg.starCount)
  glowDots = mkGlow(cfg.glowCount)
  nebulae = mkNebulae(cfg.nebulaCount)
  shootingStars = []
  nextShootFrame = cfg.shootInterval
}

function col(cfg, idx) {
  return cfg.palette[idx % cfg.palette.length]
}

function draw() {
  if (!canvasEl.value) return
  const ctx = canvasEl.value.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  // nebulae
  for (const nb of nebulae) {
    const a = nb.base * (0.5 + 0.5 * Math.sin(nb.phase + t * nb.spd))
    const [r, g, b] = col(cfg, nb.colorIdx)
    const grad = ctx.createRadialGradient(nb.x, nb.y, 0, nb.x, nb.y, nb.r)
    grad.addColorStop(0, `rgba(${r},${g},${b},${a})`)
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`)
    ctx.beginPath()
    ctx.arc(nb.x, nb.y, nb.r, 0, Math.PI * 2)
    ctx.fillStyle = grad
    ctx.fill()
  }

  // constellation lines
  const [lr, lg, lb] = cfg.lineColor
  const distSq = cfg.constellationDist * cfg.constellationDist
  for (let i = 0; i < stars.length; i++) {
    for (let j = i + 1; j < stars.length; j++) {
      const dx = stars[i].x - stars[j].x
      const dy = stars[i].y - stars[j].y
      if (dx * dx + dy * dy < distSq) {
        const dist = Math.sqrt(dx * dx + dy * dy)
        const a = (1 - dist / cfg.constellationDist) * 0.09
        ctx.beginPath()
        ctx.moveTo(stars[i].x, stars[i].y)
        ctx.lineTo(stars[j].x, stars[j].y)
        ctx.strokeStyle = `rgba(${lr},${lg},${lb},${a})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  }

  // stars
  for (const s of stars) {
    const a = s.base * cfg.starAlphaScale * (0.3 + 0.7 * (0.5 + 0.5 * Math.sin(s.phase + t * s.spd)))
    const [r, g, b] = col(cfg, s.colorIdx)
    // glow halo
    if (s.r > 0.6) {
      const hGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 3)
      hGrad.addColorStop(0, `rgba(${r},${g},${b},${a * 0.4})`)
      hGrad.addColorStop(1, `rgba(${r},${g},${b},0)`)
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r * 3, 0, Math.PI * 2)
      ctx.fillStyle = hGrad
      ctx.fill()
    }
    ctx.beginPath()
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${r},${g},${b},${Math.min(a * 2.2, 0.95)})`
    ctx.fill()

    // drift
    s.x += s.dx + Math.sin(s.phase * 0.6 + t * 0.04) * 0.08
    s.y += s.dy + Math.cos(s.phase * 0.5 + t * 0.035) * 0.07
    if (s.x < -2) s.x = w + 2
    if (s.x > w + 2) s.x = -2
    if (s.y < -2) s.y = h + 2
    if (s.y > h + 2) s.y = -2
  }

  // glow dots
  for (const p of glowDots) {
    const a = p.base * (0.3 + 0.7 * (0.5 + 0.5 * Math.sin(p.phase + t * p.spd)))
    const [r, g, b] = col(cfg, p.colorIdx)
    const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4)
    grad.addColorStop(0, `rgba(${r},${g},${b},${a})`)
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`)
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2)
    ctx.fillStyle = grad
    ctx.fill()

    p.x += p.vx
    p.y += p.vy
    if (p.x < -30) p.x = w + 30
    if (p.x > w + 30) p.x = -30
    if (p.y < -30) p.y = h + 30
    if (p.y > h + 30) p.y = -30
  }

  // shooting stars
  nextShootFrame--
  if (nextShootFrame <= 0) {
    shootingStars.push(mkShooting())
    nextShootFrame = cfg.shootInterval + Math.random() * 60
  }
  const [sr, sg, sb] = cfg.palette[0]
  for (let i = shootingStars.length - 1; i >= 0; i--) {
    const ss = shootingStars[i]
    ss.life++
    const progress = ss.life / ss.maxLife
    const alpha = Math.sin(progress * Math.PI) * 0.85
    ss.x += Math.cos(ss.angle) * ss.speed
    ss.y += Math.sin(ss.angle) * ss.speed

    const tailX = ss.x - Math.cos(ss.angle) * ss.len * Math.min(progress * 3, 1)
    const tailY = ss.y - Math.sin(ss.angle) * ss.len * Math.min(progress * 3, 1)

    const sGrad = ctx.createLinearGradient(tailX, tailY, ss.x, ss.y)
    sGrad.addColorStop(0, `rgba(${sr},${sg},${sb},0)`)
    sGrad.addColorStop(0.6, `rgba(${sr},${sg},${sb},${alpha * 0.5})`)
    sGrad.addColorStop(1, `rgba(255,255,255,${alpha})`)
    ctx.beginPath()
    ctx.moveTo(tailX, tailY)
    ctx.lineTo(ss.x, ss.y)
    ctx.strokeStyle = sGrad
    ctx.lineWidth = 1.8
    ctx.stroke()

    if (ss.life >= ss.maxLife || ss.x > w + 150 || ss.y > h + 150) {
      shootingStars.splice(i, 1)
    }
  }

  t += 0.016
  rafId = requestAnimationFrame(draw)
}

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  rafId = requestAnimationFrame(draw)
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  if (rafId) cancelAnimationFrame(rafId)
})

watch(() => props.theme, () => {
  cfg = themeConfig()
})
</script>

<style scoped>
.star-canvas {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  opacity: 0.8;
}
</style>
