<script setup>
import { store } from '@/assets/store';
import { getCurrentApiUrl } from '@/assets/utils';
import { t } from '@/i18n';

const props = defineProps({ session: String })
if (props.session) store.session = props.session
</script>

<template>
  <div class="info-main">
    <div class="info-card">
      <div class="card-header">
        <div class="card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div class="card-title-group">
          <h2>{{ t.emulatedAntsword.title }}</h2>
          <p>{{ t.emulatedAntsword.desc }}</p>
        </div>
      </div>

      <div class="info-table">
        <div class="info-row">
          <span class="info-key">{{ t.emulatedAntsword.keyAddr }}</span>
          <code class="info-value">{{ getCurrentApiUrl() }}/session/{{ props.session }}/emulated_antsword</code>
        </div>
        <div class="info-row">
          <span class="info-key">{{ t.emulatedAntsword.keyPw }}</span>
          <code class="info-value">as</code>
        </div>
      </div>

      <div class="card-note">
        <p>{{ t.emulatedAntsword.note }}</p>
        <p class="note-warning">{{ t.emulatedAntsword.warning }}</p>
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
  padding: 24px;
}

.info-card {
  width: min(600px, 100%);
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 24px 24px 20px;
  border-bottom: 1px solid var(--border-color-grey);
}

.card-icon {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background-color: var(--background-color-3);
  color: var(--font-color-primary);
}

.card-icon svg {
  width: 22px;
  height: 22px;
}

.card-title-group h2 {
  margin: 0 0 4px;
  font-size: 1.15rem;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
}

.card-title-group p {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--font-color-secondary);
  line-height: 1.4;
}

.info-table {
  padding: 0 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color-grey);
}

.info-row:last-child {
  border-bottom: none;
}

.info-key {
  width: 48px;
  flex-shrink: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--font-color-secondary);
  text-align: right;
}

.info-value {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--font-color-primary);
  word-break: break-all;
  background: transparent;
  padding: 0;
}

.card-note {
  padding: 16px 24px 20px;
  border-top: 1px solid var(--border-color-grey);
  background-color: var(--table-header-bg);
}

.card-note p {
  margin: 0 0 6px;
  font-size: var(--font-size-base);
  color: var(--font-color-secondary);
  line-height: 1.5;
}

.card-note p:last-child {
  margin: 0;
}

.note-warning {
  color: var(--yellow) !important;
  font-size: 0.82rem !important;
}
</style>
