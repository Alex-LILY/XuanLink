<script setup>
import Header from "@/components/Header.vue"
import { store, popupsRef, currentSettings, authState } from "@/assets/store"
import Popups from "@/components/Popups.vue"
import StarField from "@/components/StarField.vue"
import ChangePasswordModal from "@/components/ChangePasswordModal.vue"
import { getDataOrPopupError } from "@/assets/utils";
import { watch, onMounted, computed, nextTick } from "vue";

const starThemes = ["modern", "glass", "cyber", "terminal", "paper", "nova"]
const showStars = computed(() => starThemes.includes(store.theme))

function applyFontSize(value) {
  let targetVal = Number(value)
  if (!targetVal || targetVal < 8 || targetVal > 100) {
    targetVal = 13
  }
  document.querySelector("html").style.fontSize = `${targetVal}px`
}

onMounted(async () => {
  nextTick(() => store.theme_background_transition = true)

  const validThemes = ["pro", "terminal", "glass", "cyber", "paper", "modern", "nova"]
  const themeMigration = {
    tool: "pro",
    night: "glass",
    ink: "terminal",
    ember: "cyber",
    aurora: "glass",
    parchment: "paper",
    modern: "modern",
  }
  let settings = await getDataOrPopupError("/settings")
  for (let key of Object.keys(settings)) {
    currentSettings[key] = settings[key]
  }
  if (themeMigration[currentSettings.theme]) {
    currentSettings.theme = themeMigration[currentSettings.theme]
  }
  if (!validThemes.includes(currentSettings.theme)) {
    currentSettings.theme = "pro"
  }
  if (!currentSettings.proxy) {
    currentSettings.proxy = ""
  }
  applyFontSize(currentSettings.fontSize)

  // Check if password change is required
  try {
    const status = await getDataOrPopupError("/api/auth/status")
    if (status && status.needs_password_change) {
      authState.needsPasswordChange = true
    }
  } catch (_) {}
})

watch(() => currentSettings.fontSize, (newValue) => {
  applyFontSize(newValue)
})

// Sync theme to <body> so Popups (outside #root) inherit theme CSS variables
watch(() => store.theme, (t) => {
  document.body.dataset.theme = t
}, { immediate: true })

onMounted(() => {
  applyFontSize(currentSettings.fontSize)
})
</script>

<template>
  <div id="root" :data-theme="store.theme">

    <!-- modern 动态背景 -->
    <div v-if="store.theme === 'modern'" class="modern-bg" aria-hidden="true">
      <div class="modern-bg-gradient"></div>
      <div class="modern-bg-noise"></div>
      <div class="modern-bg-orb orb-1"></div>
      <div class="modern-bg-orb orb-2"></div>
      <div class="modern-bg-orb orb-3"></div>
      <div class="modern-bg-orb orb-4"></div>
    </div>

    <!-- glass 极光背景 -->
    <div v-if="store.theme === 'glass'" class="glass-bg" aria-hidden="true">
      <div class="glass-aurora"></div>
      <div class="glass-orb glass-orb-1"></div>
      <div class="glass-orb glass-orb-2"></div>
      <div class="glass-orb glass-orb-3"></div>
      <div class="glass-noise"></div>
    </div>

    <!-- cyber 赛博网格背景 -->
    <div v-if="store.theme === 'cyber'" class="cyber-bg" aria-hidden="true">
      <div class="cyber-grid"></div>
      <div class="cyber-glow cyber-glow-1"></div>
      <div class="cyber-glow cyber-glow-2"></div>
      <div class="cyber-scan"></div>
    </div>

    <!-- terminal 磷光背景 -->
    <div v-if="store.theme === 'terminal'" class="terminal-bg" aria-hidden="true">
      <div class="terminal-dots"></div>
      <div class="terminal-scanlines"></div>
      <div class="terminal-vignette"></div>
      <div class="terminal-glow"></div>
    </div>

    <!-- paper 粉彩玻璃背景 -->
    <div v-if="store.theme === 'paper'" class="paper-bg" aria-hidden="true">
      <div class="paper-aurora"></div>
      <div class="paper-orb paper-orb-1"></div>
      <div class="paper-orb paper-orb-2"></div>
      <div class="paper-orb paper-orb-3"></div>
      <div class="paper-noise"></div>
    </div>

    <!-- nova 极光幻境背景 -->
    <div v-if="store.theme === 'nova'" class="nova-bg" aria-hidden="true">
      <div class="nova-aurora"></div>
      <div class="nova-orb nova-orb-1"></div>
      <div class="nova-orb nova-orb-2"></div>
      <div class="nova-orb nova-orb-3"></div>
      <div class="nova-orb nova-orb-4"></div>
      <div class="nova-mesh"></div>
    </div>

    <StarField v-if="showStars" :theme="store.theme" />
    <!-- modified button from https://www.svgrepo.com/collection/dazzle-line-icons/ -->
    <Header />
    <main>
      <router-view></router-view>
    </main>
    <ChangePasswordModal v-model="authState.needsPasswordChange" :isFirstLogin="false" />
  </div>
  <Popups ref="popupsRef" />
</template>

<style>
#root {
  display: flex;
  align-items: stretch;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  position: relative;
}

main {
  height: auto;
  width: 100%;
  flex-grow: 1;
  margin-top: 0;
  padding: 24px;
  background-color: var(--app-bg-color);
  overflow-y: auto;
  position: relative;
  z-index: 1;
}

/* ========== modern 主题动态背景 ========== */
.modern-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: #0b0f19;
}

.modern-bg-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 18%, rgba(99, 102, 241, 0.22) 0%, transparent 40%),
    radial-gradient(circle at 82% 8%, rgba(34, 211, 238, 0.15) 0%, transparent 35%),
    radial-gradient(circle at 62% 88%, rgba(139, 92, 246, 0.18) 0%, transparent 45%),
    radial-gradient(circle at 8% 75%, rgba(6, 182, 212, 0.1) 0%, transparent 30%);
  animation: bg-pulse 14s ease-in-out infinite alternate;
}

.modern-bg-noise {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none;
  opacity: 0.7;
}

.modern-bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.38;
  animation: orb-float 18s ease-in-out infinite alternate;
}

.orb-1 {
  width: 560px;
  height: 560px;
  background: rgba(99, 102, 241, 0.38);
  top: -140px;
  left: -140px;
  animation-duration: 22s;
}

.orb-2 {
  width: 460px;
  height: 460px;
  background: rgba(34, 211, 238, 0.28);
  bottom: -100px;
  right: -100px;
  animation-duration: 26s;
}

.orb-3 {
  width: 340px;
  height: 340px;
  background: rgba(139, 92, 246, 0.32);
  top: 38%;
  left: 52%;
  animation-duration: 20s;
}

.orb-4 {
  width: 260px;
  height: 260px;
  background: rgba(6, 182, 212, 0.22);
  top: 22%;
  right: 12%;
  animation-duration: 30s;
  animation-direction: alternate-reverse;
}

/* ========== glass 主题极光背景 ========== */
.glass-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: #0d0a24;
}

.glass-aurora {
  position: absolute;
  inset: -50%;
  background:
    radial-gradient(ellipse at 30% 40%, rgba(168, 85, 247, 0.4) 0%, transparent 50%),
    radial-gradient(ellipse at 72% 62%, rgba(45, 212, 191, 0.32) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 10%, rgba(244, 63, 94, 0.22) 0%, transparent 45%),
    radial-gradient(ellipse at 15% 80%, rgba(99, 102, 241, 0.28) 0%, transparent 45%);
  animation: aurora-rotate 28s linear infinite;
  filter: blur(30px);
}

.glass-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(110px);
  animation: orb-float 20s ease-in-out infinite alternate;
}

.glass-orb-1 {
  width: 700px;
  height: 700px;
  background: rgba(168, 85, 247, 0.28);
  top: -20%;
  left: -10%;
  animation-duration: 24s;
}

.glass-orb-2 {
  width: 580px;
  height: 580px;
  background: rgba(45, 212, 191, 0.22);
  bottom: -18%;
  right: -8%;
  animation-duration: 19s;
}

.glass-orb-3 {
  width: 440px;
  height: 440px;
  background: rgba(244, 63, 94, 0.18);
  top: 35%;
  left: 42%;
  animation-duration: 30s;
  animation-direction: alternate-reverse;
}

.glass-noise {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
  background-size: 32px 32px;
  opacity: 0.8;
}

/* ========== cyber 主题赛博背景 ========== */
.cyber-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: #020509;
}

.cyber-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.055) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse at center, black 40%, transparent 80%);
}

.cyber-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
}

.cyber-glow-1 {
  width: 540px;
  height: 540px;
  background: rgba(0, 240, 255, 0.14);
  top: -120px;
  right: -120px;
  animation: cyber-pulse 7s ease-in-out infinite alternate;
}

.cyber-glow-2 {
  width: 420px;
  height: 420px;
  background: rgba(255, 0, 212, 0.12);
  bottom: -100px;
  left: -100px;
  animation: cyber-pulse 9s ease-in-out infinite alternate-reverse;
}

.cyber-scan {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, rgba(0, 240, 255, 0.5) 50%, transparent 100%);
  animation: cyber-scanline 9s linear infinite;
  box-shadow: 0 0 16px rgba(0, 240, 255, 0.4), 0 0 40px rgba(0, 240, 255, 0.15);
}

/* ========== terminal 主题磷光背景 ========== */
.terminal-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: #010402;
}

.terminal-dots {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(34, 197, 94, 0.14) 1px, transparent 1px);
  background-size: 22px 22px;
}

.terminal-scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent 0px,
    transparent 3px,
    rgba(0, 0, 0, 0.22) 3px,
    rgba(0, 0, 0, 0.22) 4px
  );
}

.terminal-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, transparent 45%, rgba(0, 0, 0, 0.7) 100%);
}

.terminal-glow {
  position: absolute;
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse at 50% 60%, rgba(34, 197, 94, 0.07) 0%, transparent 65%);
  animation: terminal-flicker 6s ease-in-out infinite alternate;
}

/* ========== Shared keyframes ========== */

@keyframes bg-pulse {
  0% { opacity: 0.8; transform: scale(1); }
  100% { opacity: 1; transform: scale(1.06); }
}

@keyframes orb-float {
  0% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, -20px) scale(1.04); }
  100% { transform: translate(45px, -45px) scale(1.09); }
}

@keyframes aurora-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes cyber-pulse {
  from { opacity: 0.1; }
  to { opacity: 0.2; }
}

@keyframes cyber-scanline {
  from { top: -4px; }
  to { top: 100vh; }
}

@keyframes terminal-flicker {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

/* ========== 主题主区域背景透明 ========== */

body[data-theme="modern"] main {
  background-color: transparent;
  padding: 20px 28px;
}

body[data-theme="glass"] main {
  background-color: transparent;
  background-image: none;
}

body[data-theme="cyber"] main {
  background-color: transparent;
}

body[data-theme="terminal"] main {
  background-color: transparent;
}

body[data-theme="paper"] main {
  background-color: transparent;
}

/* ========== paper 粉彩玻璃背景 ========== */
.paper-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: linear-gradient(135deg, #fce4ec 0%, #ede7f6 40%, #e0f7fa 100%);
}

.paper-aurora {
  position: absolute;
  inset: -30%;
  background:
    radial-gradient(ellipse at 20% 30%, rgba(236, 64, 122, 0.3) 0%, transparent 50%),
    radial-gradient(ellipse at 78% 18%, rgba(124, 77, 255, 0.25) 0%, transparent 45%),
    radial-gradient(ellipse at 60% 80%, rgba(38, 198, 218, 0.22) 0%, transparent 45%),
    radial-gradient(ellipse at 8% 72%, rgba(255, 167, 38, 0.18) 0%, transparent 40%);
  animation: paper-aurora-drift 22s ease-in-out infinite alternate;
  filter: blur(22px);
}

.paper-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  animation: orb-float 20s ease-in-out infinite alternate;
}

.paper-orb-1 {
  width: 520px;
  height: 520px;
  background: rgba(236, 64, 122, 0.22);
  top: -12%;
  left: -6%;
  animation-duration: 19s;
}

.paper-orb-2 {
  width: 420px;
  height: 420px;
  background: rgba(124, 77, 255, 0.2);
  bottom: -10%;
  right: -6%;
  animation-duration: 23s;
}

.paper-orb-3 {
  width: 340px;
  height: 340px;
  background: rgba(38, 198, 218, 0.18);
  top: 38%;
  left: 48%;
  animation-duration: 17s;
  animation-direction: alternate-reverse;
}

.paper-noise {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.45) 1px, transparent 1px);
  background-size: 22px 22px;
  opacity: 0.55;
}

@keyframes paper-aurora-drift {
  0% { transform: scale(1) rotate(0deg); opacity: 0.85; }
  100% { transform: scale(1.08) rotate(8deg); opacity: 1; }
}

/* ========== nova 极光幻境背景 ========== */
.nova-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background: #030712;
}

.nova-aurora {
  position: absolute;
  inset: -30%;
  background:
    radial-gradient(ellipse at 18% 55%, rgba(109,40,217,0.5) 0%, transparent 50%),
    radial-gradient(ellipse at 82% 28%, rgba(59,130,246,0.38) 0%, transparent 48%),
    radial-gradient(ellipse at 52% 88%, rgba(124,58,237,0.32) 0%, transparent 45%),
    radial-gradient(ellipse at 8%  12%, rgba(6,182,212,0.22) 0%, transparent 40%),
    radial-gradient(ellipse at 72% 70%, rgba(167,139,250,0.28) 0%, transparent 42%);
  animation: nova-aurora-drift 22s ease-in-out infinite alternate;
  filter: blur(18px);
}

.nova-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  will-change: transform;
}

.nova-orb-1 {
  width: 700px; height: 700px;
  background: rgba(109,40,217,0.38);
  top: -18%; left: -10%;
  animation: nova-orb1 26s ease-in-out infinite alternate;
}

.nova-orb-2 {
  width: 560px; height: 560px;
  background: rgba(59,130,246,0.3);
  bottom: -14%; right: -8%;
  animation: nova-orb2 22s ease-in-out infinite alternate;
}

.nova-orb-3 {
  width: 420px; height: 420px;
  background: rgba(167,139,250,0.25);
  top: 38%; left: 54%;
  animation: nova-orb1 30s ease-in-out infinite alternate-reverse;
}

.nova-orb-4 {
  width: 280px; height: 280px;
  background: rgba(6,182,212,0.2);
  top: 12%; right: 18%;
  animation: nova-orb2 18s ease-in-out infinite alternate;
}

.nova-mesh {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(124,58,237,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124,58,237,0.05) 1px, transparent 1px);
  background-size: 64px 64px;
  mask-image: radial-gradient(ellipse 90% 80% at 50% 50%, black 25%, transparent 80%);
}

@keyframes nova-aurora-drift {
  0%   { transform: scale(1) rotate(0deg); opacity: 0.85; }
  50%  { transform: scale(1.06) rotate(4deg); opacity: 1; }
  100% { transform: scale(1.12) rotate(-3deg); opacity: 0.9; }
}

@keyframes nova-orb1 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(80px, 100px) scale(1.14); }
}

@keyframes nova-orb2 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(-90px, -80px) scale(1.2); }
}

body[data-theme="nova"] main {
  background-color: transparent;
  padding: 20px 28px;
}
</style>
