<script setup>
import { getDataOrPopupError } from '@/assets/utils';
import { ref, computed } from 'vue';
import { t } from '@/i18n';

const version = ref("Unknown Version")

setTimeout(async () => {
  let serverVersion = await getDataOrPopupError("/utils/version")
  version.value = `v${serverVersion}`
}, 0)

const features = computed(() => [
  { icon: "🛡️", text: t.value.about.feat1 },
  { icon: "🔐", text: t.value.about.feat2 },
  { icon: "📁", text: t.value.about.feat3 },
  { icon: "🎨", text: t.value.about.feat4 },
])
</script>

<template>
  <div class="info-main">
    <div class="info-panel shadow-box">
      <div class="panel-glow" aria-hidden="true"></div>

      <div class="panel-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
      </div>

      <h1 class="panel-title">XuLink</h1>
      <p class="panel-subtitle">{{ t.about.subtitle }}</p>
      <div class="panel-version">
        <span class="version-badge">{{ version }}</span>
      </div>

      <div class="feature-list">
        <div v-for="f in features" :key="f.text" class="feature-item">
          <span class="feature-icon">{{ f.icon }}</span>
          <span class="feature-text">{{ f.text }}</span>
        </div>
      </div>

      <div class="panel-links">
        <a href="https://t.me/SpeAR_888" target="_blank" class="link-btn">
          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.869 4.326-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.829.941z"/>
          </svg>
          {{ t.about.channelBtn }}
        </a>
        <a href="https://t.me/SpeAR_888" target="_blank" class="link-btn secondary">
          {{ t.about.communityBtn }}
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.info-main {
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-panel {
  position: relative;
  overflow: hidden;
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  box-shadow: var(--shadow-float);
  width: min(400px, 90vw);
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  text-align: center;
}

.panel-glow {
  position: absolute;
  top: -60px;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, transparent 70%);
  pointer-events: none;
  border-radius: 50%;
}

.panel-logo {
  width: 64px;
  height: 64px;
  background: var(--button-bg);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: var(--shadow-button, 0 8px 24px rgba(99, 102, 241, 0.35));
}

.panel-logo svg {
  width: 32px;
  height: 32px;
  stroke: #ffffff;
}

.panel-title {
  font-size: 1.8rem;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
  margin: 0 0 6px 0;
  font-family: "MapleMono SemiBold", var(--font-ui);
  letter-spacing: 0.03em;
}

.panel-subtitle {
  font-size: 0.9rem;
  color: var(--font-color-secondary);
  margin: 0 0 16px 0;
}

.panel-version {
  margin-bottom: 28px;
}

.version-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: var(--radius-pill);
  background: var(--background-color-3);
  border: var(--card-border);
  color: var(--font-color-secondary);
  font-size: 0.8rem;
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
}

.feature-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 28px;
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--background-color-1);
  border: var(--card-border);
  font-size: 0.85rem;
  color: var(--font-color-primary);
}

.feature-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.feature-text {
  line-height: 1.3;
}

.panel-links {
  width: 100%;
  display: flex;
  gap: 10px;
}

.link-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: var(--button-height);
  padding: var(--button-padding);
  border-radius: var(--button-radius);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
  background: var(--button-bg);
  color: var(--button-color, #ffffff);
  border: none;
  box-shadow: var(--shadow-button);
}

.link-btn:hover {
  background: var(--button-hover-bg);
  transform: translateY(-1px);
}

.link-btn.secondary {
  background: var(--button-secondary-bg);
  color: var(--button-secondary-color);
  border: var(--button-secondary-border, none);
  box-shadow: none;
}

.link-btn.secondary:hover {
  background: var(--button-secondary-hover-bg);
  box-shadow: none;
}
</style>

<style>
body[data-theme="modern"] .panel-title {
  background: linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

body[data-theme="modern"] .panel-logo {
  background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.45);
}

body[data-theme="modern"] .version-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

body[data-theme="modern"] .feature-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

body[data-theme="modern"] .feature-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

body[data-theme="modern"] .link-btn {
  background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
  color: #ffffff;
  border: none;
}

body[data-theme="modern"] .link-btn:hover {
  background: linear-gradient(135deg, #818cf8 0%, #67e8f9 100%);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
}

body[data-theme="modern"] .link-btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--font-color-secondary);
}

body[data-theme="modern"] .link-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: none;
}
</style>