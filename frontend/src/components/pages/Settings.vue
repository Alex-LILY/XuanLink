<script setup>
import { ref, computed, onMounted } from "vue";
import { getDataOrPopupError, postDataOrPopupError, addPopup } from "@/assets/utils"
import GroupedForm from "@/components/GroupedForm.vue"
import ChangePasswordModal from "@/components/ChangePasswordModal.vue"
import { store, currentSettings } from "@/assets/store";
import { useRouter } from "vue-router"
import { getCurrentApiUrl } from "@/assets/utils"
import { t } from "@/i18n"

const router = useRouter()
const props = defineProps({ session: String })

if (props.session) store.session = props.session

const proxyAlternatives = ref([])

const optionsGroups = computed(() => {
  const T = t.value.settings
  return [
    {
      name: T.uiGroup,
      options: [
        {
          id: "theme", name: T.theme, type: "select", default_value: store.theme,
          alternatives: [
            { name: T.themes.pro, value: "pro" },
            { name: T.themes.terminal, value: "terminal" },
            { name: T.themes.glass, value: "glass" },
            { name: T.themes.cyber, value: "cyber" },
            { name: T.themes.paper, value: "paper" },
            { name: T.themes.modern, value: "modern" },
            { name: T.themes.nova, value: "nova" },
          ]
        },
        { id: "fontSize", name: T.fontSize, type: "text", placeholder: T.fontSizePh, default_value: "13" }
      ]
    },
    {
      name: T.connGroup,
      options: [
        { id: "proxy", name: T.proxy, type: "select", default_value: null, alternatives: proxyAlternatives.value.length ? proxyAlternatives.value : [{ name: T.noProxy, value: "" }] }
      ]
    },
    {
      name: T.otherGroup,
      options: [
        {
          id: "filesizeUnit", name: T.fileUnit, type: "select", default_value: 1024,
          alternatives: [
            { name: T.fileUnit1024, value: 1024 },
            { name: T.fileUnit1000, value: 1000 }
          ]
        }
      ]
    }
  ]
})

onMounted(async () => {
  try {
    const settings = await getDataOrPopupError("/settings")
    for (const key of Object.keys(settings)) {
      currentSettings[key] = settings[key]
    }
  } catch (e) {}

  if (currentSettings.proxy === undefined || currentSettings.proxy === null) {
    currentSettings.proxy = ""
  }

  try {
    const proxyList = await getDataOrPopupError("/http_proxies")
    const alternatives = [{ name: t.value.settings.noProxy, value: "" }]
    for (const proxy of proxyList) {
      alternatives.push({ name: proxy.url, value: proxy.url })
    }
    proxyAlternatives.value = alternatives
  } catch (e) {}
})

async function saveSettings() {
  await postDataOrPopupError("/settings", { ...currentSettings })
  addPopup("green", t.value.settings.saveOkTitle, t.value.settings.saveOkMsg)
}

const testProxySite = ref("apple")
const testingProxy = ref(false)

async function onTestProxy() {
  testingProxy.value = true
  try {
    const data = await getDataOrPopupError("/utils/test_proxy", {
      params: { proxy: currentSettings.proxy, site: testProxySite.value }
    })
    if (data) {
      addPopup("green", t.value.settings.proxyOkTitle, t.value.settings.proxyOkMsg.replace('{site}', testProxySite.value))
    } else {
      addPopup("yellow", t.value.settings.proxyFailTitle, t.value.settings.proxyFailMsg.replace('{site}', testProxySite.value))
    }
  } finally {
    testingProxy.value = false
  }
}

function onUpdateSettings(optionId, value) {
  currentSettings[optionId] = value
}

const buttons = computed(() => [
  { id: "discard", label: t.value.settings.discard },
  { id: "save", label: t.value.settings.save },
])

function onButtonClick(button) {
  if (button.id === "discard") router.go(-1)
  else if (button.id === "save") saveSettings()
}

// ── Security section ──────────────────────────────────────────────────────────

const showChangePassword = ref(false)

// OTP
const otpInfo = ref(null)
const otpSectionOpen = ref(false)
const otpVerifyCode = ref("")
const otpLoading = ref(false)
const otpError = ref("")

async function openOtpSection() {
  otpSectionOpen.value = true
  otpError.value = ""
  otpVerifyCode.value = ""
  otpLoading.value = true
  try {
    const data = await getDataOrPopupError("/api/auth/otp_setup")
    otpInfo.value = data
  } catch (e) {
    otpError.value = t.value.settings.otpLoadErr
  } finally {
    otpLoading.value = false
  }
}

async function enableOtp() {
  if (!otpVerifyCode.value) {
    otpError.value = t.value.settings.otpErrVerify
    return
  }
  otpLoading.value = true
  otpError.value = ""
  try {
    await postDataOrPopupError("/api/auth/otp_enable", {
      secret: otpInfo.value.secret,
      otp_code: otpVerifyCode.value,
    })
    otpInfo.value.otp_enabled = true
    otpVerifyCode.value = ""
    addPopup("green", t.value.settings.otpSuccessTitle, t.value.settings.otpSuccessMsg)
  } catch (e) {
    otpError.value = e.response?.data?.detail || t.value.settings.otpVerifyFail
  } finally {
    otpLoading.value = false
  }
}

async function disableOtp() {
  otpLoading.value = true
  otpError.value = ""
  try {
    await postDataOrPopupError("/api/auth/otp_disable", {})
    otpInfo.value.otp_enabled = false
    addPopup("green", t.value.settings.otpDisabledTitle, t.value.settings.otpDisabledMsg)
  } catch (e) {
    otpError.value = t.value.settings.otpOpFail
  } finally {
    otpLoading.value = false
  }
}
</script>

<template>
  <div class="settings-page">
    <div class="page-header">
      <div class="page-header-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </div>
      <div class="page-header-text">
        <h1>{{ t.settings.pageTitle }}</h1>
        <p>{{ t.settings.pageDesc }}</p>
      </div>
    </div>

    <GroupedForm
      :groups="optionsGroups"
      :modelValue="currentSettings"
      @update:modelValue="onUpdateSettings"
      :buttons="buttons"
      @button-click="onButtonClick"
    />

    <div class="proxy-test-card">
      <div class="proxy-test-header">{{ t.settings.proxyTest }}</div>
      <div class="proxy-test-body">
        <p class="proxy-test-desc">{{ t.settings.proxyTestDesc }}</p>
        <div class="proxy-test-row">
          <select class="form-select" v-model="testProxySite">
            <option value="apple">{{ t.settings.proxyServers.apple }}</option>
            <option value="google">{{ t.settings.proxyServers.google }}</option>
            <option value="cloudflare">{{ t.settings.proxyServers.cloudflare }}</option>
            <option value="microsoft">{{ t.settings.proxyServers.microsoft }}</option>
            <option value="huawei">{{ t.settings.proxyServers.huawei }}</option>
            <option value="xiaomi">{{ t.settings.proxyServers.xiaomi }}</option>
          </select>
          <button class="test-btn" @click="onTestProxy" :disabled="testingProxy">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline v-if="!testingProxy" points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              <circle v-else cx="12" cy="12" r="3" opacity="0.5"/>
            </svg>
            {{ testingProxy ? t.settings.testingBtn : t.settings.testBtn }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── Security settings ── -->
    <div class="proxy-test-card security-card">
      <!-- Change Password subsection -->
      <div class="proxy-test-header">{{ t.settings.security }}</div>
      <div class="proxy-test-body security-body">

        <!-- Change password row -->
        <div class="security-row">
          <div class="security-row-info">
            <div class="security-row-title">{{ t.settings.changePwTitle }}</div>
            <div class="security-row-desc">{{ t.settings.changePwDesc }}</div>
          </div>
          <button class="test-btn" @click="showChangePassword = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            {{ t.settings.changePwBtn }}
          </button>
        </div>

        <div class="security-divider"></div>

        <!-- OTP subsection -->
        <div class="security-row">
          <div class="security-row-info">
            <div class="security-row-title">{{ t.settings.otpTitle }}</div>
            <div class="security-row-desc">{{ t.settings.otpDesc }}</div>
          </div>
          <button class="test-btn" @click="openOtpSection" :disabled="otpLoading">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
              <line x1="12" y1="18" x2="12.01" y2="18"/>
            </svg>
            {{ otpSectionOpen ? t.settings.otpRefresh : t.settings.otpManage }}
          </button>
        </div>

        <!-- OTP expanded panel -->
        <div v-if="otpSectionOpen" class="otp-panel">
          <div v-if="otpLoading" class="otp-loading">
            <span class="otp-spinner"></span> {{ t.settings.otpLoading }}
          </div>
          <template v-else-if="otpInfo">
            <!-- Current status badge -->
            <div class="otp-status-row">
              <span class="otp-badge" :class="otpInfo.otp_enabled ? 'badge-on' : 'badge-off'">
                {{ otpInfo.otp_enabled ? t.settings.otpEnabled : t.settings.otpDisabled }}
              </span>
            </div>

            <!-- Disable flow -->
            <template v-if="otpInfo.otp_enabled">
              <p class="otp-desc">{{ t.settings.otpEnabledDesc }}</p>
              <button class="test-btn btn-danger" @click="disableOtp" :disabled="otpLoading">{{ t.settings.otpDisableBtn }}</button>
            </template>

            <!-- Enable flow -->
            <template v-else>
              <p class="otp-desc">{{ t.settings.otpSetupDesc }}</p>

              <!-- QR code via external service -->
              <div class="otp-qr-wrap">
                <img
                  :src="`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(otpInfo.uri)}`"
                  alt="OTP QR Code"
                  class="otp-qr"
                />
              </div>

              <div class="otp-secret-block">
                <span class="otp-secret-label">{{ t.settings.otpSecretLabel }}</span>
                <code class="otp-secret-value">{{ otpInfo.secret }}</code>
              </div>

              <div class="otp-verify-row">
                <input
                  type="text"
                  v-model="otpVerifyCode"
                  class="form-input otp-code-input"
                  :placeholder="t.settings.otpVerifyPh"
                  maxlength="6"
                  inputmode="numeric"
                />
                <button class="test-btn" @click="enableOtp" :disabled="otpLoading || !otpVerifyCode">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  {{ t.settings.otpEnableBtn }}
                </button>
              </div>
            </template>

            <div v-if="otpError" class="otp-error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ otpError }}
            </div>
          </template>
        </div>
      </div>
    </div>

    <ChangePasswordModal v-model="showChangePassword" :isFirstLogin="false" />
  </div>
</template>

<style scoped>
.settings-page {
  padding-bottom: 32px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 900px;
  margin: 0 auto 28px;
  padding: 0 24px;
}

.page-header-icon {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  background-color: var(--card-bg);
  border: var(--card-border);
  color: var(--font-color-primary);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
}

.page-header-icon svg {
  width: 22px;
  height: 22px;
}

.page-header-text h1 {
  margin: 0 0 3px;
  font-size: 1.3rem;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
  line-height: 1.2;
}

.page-header-text p {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--font-color-secondary);
}

/* Proxy test card */
.proxy-test-card {
  max-width: 900px;
  margin: 4px auto 0;
  padding: 0 24px;
}

.proxy-test-card > div:first-child {
  border-radius: var(--card-radius);
}

.proxy-test-header {
  color: var(--font-color-secondary);
  font-size: 0.78rem;
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  padding: 11px 20px 9px;
  background-color: var(--table-header-bg);
  border: var(--card-border);
  border-bottom: none;
  border-radius: var(--card-radius) var(--card-radius) 0 0;
}

.proxy-test-body {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-top: none;
  border-radius: 0 0 var(--card-radius) var(--card-radius);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  padding: 16px 20px 18px;
}

.proxy-test-desc {
  margin: 0 0 12px;
  font-size: var(--font-size-base);
  color: var(--font-color-secondary);
}

.proxy-test-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.form-select {
  height: var(--control-height);
  border-radius: var(--input-radius);
  background-color: var(--input-bg);
  border: var(--input-border);
  color: var(--input-color);
  font-size: var(--font-size-base);
  font-family: var(--font-ui);
  padding: 0 12px;
  outline: none;
  min-width: 160px;
  flex: 1;
  max-width: 280px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-select:focus {
  border-color: var(--input-focus-border-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color) 15%, transparent);
}

.test-btn {
  height: var(--button-height);
  padding: var(--button-padding);
  border-radius: var(--button-radius);
  background: var(--button-bg);
  color: var(--button-color);
  border: var(--button-border, none);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-ui);
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: var(--shadow-button);
  flex-shrink: 0;
}

.test-btn:hover:not(:disabled) {
  background: var(--button-hover-bg);
  transform: translateY(-1px);
}

.test-btn:active:not(:disabled) {
  transform: translateY(0);
}

.test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.test-btn svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

@media (max-width: 700px) {
  .page-header,
  .proxy-test-card {
    padding: 0 16px;
  }

  .proxy-test-row {
    flex-direction: column;
    align-items: stretch;
  }

  .form-select {
    max-width: 100%;
  }

  .test-btn {
    justify-content: center;
  }
}

/* ── Security card ── */
.security-card {
  margin-top: 16px;
}

.security-body {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.security-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  flex-wrap: wrap;
}

.security-row-info {
  flex: 1;
  min-width: 0;
}

.security-row-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--font-color-primary);
  margin-bottom: 2px;
}

.security-row-desc {
  font-size: 0.8rem;
  color: var(--font-color-secondary);
}

.security-divider {
  height: 1px;
  background: var(--card-border-color, rgba(255,255,255,0.08));
  border: none;
  margin: 0;
}

/* OTP panel */
.otp-panel {
  border-top: var(--card-border, 1px solid rgba(255,255,255,0.08));
  padding-top: 16px;
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.otp-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--font-color-secondary);
  font-size: var(--font-size-base);
}

.otp-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid color-mix(in srgb, currentColor 30%, transparent);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.otp-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.otp-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: var(--font-weight-medium);
}

.badge-on {
  background: color-mix(in srgb, #22c55e 15%, transparent);
  border: 1px solid color-mix(in srgb, #22c55e 35%, transparent);
  color: #86efac;
}

.badge-off {
  background: color-mix(in srgb, #94a3b8 12%, transparent);
  border: 1px solid color-mix(in srgb, #94a3b8 25%, transparent);
  color: var(--font-color-secondary);
}

.otp-desc {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--font-color-secondary);
  line-height: 1.5;
}

.otp-qr-wrap {
  display: flex;
  justify-content: flex-start;
}

.otp-qr {
  width: 160px;
  height: 160px;
  border-radius: 10px;
  border: var(--card-border);
  background: white;
  padding: 4px;
}

.otp-secret-block {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.otp-secret-label {
  font-size: 0.78rem;
  color: var(--font-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.otp-secret-value {
  font-family: var(--font-mono, monospace);
  font-size: 0.85rem;
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--input-bg);
  border: var(--input-border);
  color: var(--font-color-primary);
  letter-spacing: 0.08em;
  word-break: break-all;
}

.otp-verify-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.otp-code-input {
  width: 200px;
  height: var(--control-height, 38px);
  padding: 0 12px;
  background: var(--input-bg);
  border: var(--input-border);
  border-radius: var(--input-radius);
  color: var(--input-color);
  font-size: var(--font-size-base);
  font-family: var(--font-ui);
  outline: none;
  letter-spacing: 0.2em;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.otp-code-input:focus {
  border-color: var(--input-focus-border-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color) 15%, transparent);
}

.otp-code-input::placeholder {
  letter-spacing: 0;
  color: var(--font-color-secondary);
}

.btn-danger {
  background: color-mix(in srgb, #ef4444 80%, transparent) !important;
  color: #fff !important;
}

.btn-danger:hover:not(:disabled) {
  background: #ef4444 !important;
}

.otp-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--input-radius, 7px);
  background: color-mix(in srgb, #ef4444 12%, transparent);
  border: 1px solid color-mix(in srgb, #ef4444 30%, transparent);
  color: #fca5a5;
  font-size: 0.85rem;
}

.otp-error svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #f87171;
}
</style>
