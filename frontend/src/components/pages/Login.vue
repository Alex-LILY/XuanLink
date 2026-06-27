<script setup>
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import { getCurrentApiUrl } from "@/assets/utils"
import { authState } from "@/assets/store"
import { t, lang, setLang } from "@/i18n"

const router = useRouter()

const password = ref("")
const otpCode = ref("")
const showPassword = ref(false)
const otpEnabled = ref(false)
const loading = ref(false)
const errorMsg = ref("")

onMounted(async () => {
  const token = localStorage.getItem("ghost_auth_token")
  if (token) {
    router.push("/")
    return
  }
  try {
    const resp = await axios.get(`${getCurrentApiUrl()}/api/auth/status`)
    if (resp.data && resp.data.data) {
      otpEnabled.value = resp.data.data.otp_enabled
    }
  } catch (e) {}
})

async function handleLogin() {
  if (!password.value) {
    errorMsg.value = t.value.login.errNoPw
    return
  }
  if (otpEnabled.value && !otpCode.value) {
    errorMsg.value = t.value.login.errNoOtp
    return
  }

  loading.value = true
  errorMsg.value = ""

  try {
    const payload = { password: password.value }
    if (otpEnabled.value) payload.otp_code = otpCode.value

    const resp = await axios.post(`${getCurrentApiUrl()}/api/auth/login`, payload)
    const data = resp.data.data
    localStorage.setItem("ghost_auth_token", data.token)
    if (data.needs_password_change) {
      authState.needsPasswordChange = true
    }
    router.push("/")
  } catch (e) {
    if (e.response) {
      const detail = e.response.data?.detail
      if (detail) {
        errorMsg.value = detail
      } else {
        errorMsg.value = `${t.value.login.errStatus} (${e.response.status})`
      }
    } else {
      errorMsg.value = t.value.login.errNoConn
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-overlay">
    <div class="login-card">
      <!-- Logo area -->
      <div class="login-logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div class="logo-text">
          <h1>{{ lang === 'zh' ? '玄联' : 'XuLink' }}</h1>
          <p>{{ t.login.subtitle }}</p>
        </div>
        <div class="lang-switcher">
          <button class="lang-btn" :class="{ active: lang === 'zh' }" @click="setLang('zh')">ZH</button>
          <button class="lang-btn" :class="{ active: lang === 'en' }" @click="setLang('en')">EN</button>
        </div>
      </div>

      <!-- Form -->
      <form class="login-form" @submit.prevent="handleLogin">
        <!-- Password field -->
        <div class="form-field">
          <label class="form-label">{{ t.login.password }}</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <input
              :type="showPassword ? 'text' : 'password'"
              v-model="password"
              class="form-input"
              :placeholder="t.login.passwordPh"
              autocomplete="current-password"
              @keydown.enter="handleLogin"
            />
            <button type="button" class="toggle-btn" @click="showPassword = !showPassword" tabindex="-1">
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- OTP field (only when enabled) -->
        <div class="form-field" v-if="otpEnabled">
          <label class="form-label">{{ t.login.otp }}</label>
          <div class="input-wrapper">
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
              <line x1="12" y1="18" x2="12.01" y2="18"/>
            </svg>
            <input
              type="text"
              v-model="otpCode"
              class="form-input otp-input"
              :placeholder="t.login.otpPh"
              maxlength="6"
              inputmode="numeric"
              autocomplete="one-time-code"
              @keydown.enter="handleLogin"
            />
          </div>
        </div>

        <!-- Error message -->
        <div v-if="errorMsg" class="error-msg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {{ errorMsg }}
        </div>

        <!-- Submit button -->
        <button type="submit" class="login-btn" :disabled="loading">
          <svg v-if="!loading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
            <polyline points="10 17 15 12 10 7"/>
            <line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
          <span class="spinner" v-else></span>
          {{ loading ? t.login.loading : t.login.btn }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--card-bg, rgba(255,255,255,0.08));
  border: var(--card-border, 1px solid rgba(255,255,255,0.15));
  border-radius: var(--card-radius, 16px);
  backdrop-filter: var(--card-backdrop, blur(20px));
  -webkit-backdrop-filter: var(--card-backdrop, blur(20px));
  padding: 40px 36px 36px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.35), 0 4px 16px rgba(0, 0, 0, 0.2);
  animation: card-appear 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes card-appear {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Logo */
.login-logo {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 32px;
}

.logo-icon {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: color-mix(in srgb, var(--button-bg, #6366f1) 20%, transparent);
  border: 1px solid color-mix(in srgb, var(--button-bg, #6366f1) 40%, transparent);
  color: var(--button-bg, #6366f1);
}

.logo-icon svg {
  width: 26px;
  height: 26px;
}

.logo-text {
  flex: 1;
}

.logo-text h1 {
  margin: 0 0 2px;
  font-size: 1.4rem;
  font-weight: var(--font-weight-bold, 700);
  color: var(--font-color-primary, #fff);
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.logo-text p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--font-color-secondary, rgba(255,255,255,0.5));
  letter-spacing: 0.05em;
}

/* Lang switcher */
.lang-switcher {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}

.lang-btn {
  height: 24px;
  padding: 0 7px;
  border-radius: 5px;
  border: 1px solid rgba(255,255,255,0.12);
  background: transparent;
  color: var(--font-color-secondary, rgba(255,255,255,0.45));
  font-size: 0.65rem;
  font-weight: 600;
  font-family: var(--font-ui, inherit);
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.lang-btn:hover {
  color: var(--font-color-primary, #fff);
  border-color: rgba(255,255,255,0.25);
}

.lang-btn.active {
  border-color: var(--button-bg, #6366f1);
  color: var(--button-bg, #6366f1);
  background: color-mix(in srgb, var(--button-bg, #6366f1) 12%, transparent);
}

/* Form */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 0.8rem;
  font-weight: var(--font-weight-medium, 500);
  color: var(--font-color-secondary, rgba(255,255,255,0.6));
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 12px;
  width: 16px;
  height: 16px;
  color: var(--font-color-secondary, rgba(255,255,255,0.4));
  pointer-events: none;
  flex-shrink: 0;
}

.form-input {
  width: 100%;
  height: var(--control-height, 40px);
  padding: 0 40px 0 38px;
  background: var(--input-bg, rgba(255,255,255,0.06));
  border: var(--input-border, 1px solid rgba(255,255,255,0.12));
  border-radius: var(--input-radius, 8px);
  color: var(--input-color, #fff);
  font-size: var(--font-size-base, 0.875rem);
  font-family: var(--font-ui, inherit);
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--input-focus-border-color, #6366f1);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color, #6366f1) 18%, transparent);
}

.form-input::placeholder {
  color: var(--font-color-secondary, rgba(255,255,255,0.3));
}

.otp-input {
  letter-spacing: 0.3em;
  font-size: 1.1rem;
  text-align: center;
  padding-left: 38px;
}

.toggle-btn {
  position: absolute;
  right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--font-color-secondary, rgba(255,255,255,0.4));
  cursor: pointer;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.toggle-btn:hover {
  color: var(--font-color-primary, #fff);
  background: color-mix(in srgb, currentColor 10%, transparent);
}

.toggle-btn svg {
  width: 16px;
  height: 16px;
}

/* Error */
.error-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--input-radius, 8px);
  background: color-mix(in srgb, #ef4444 12%, transparent);
  border: 1px solid color-mix(in srgb, #ef4444 30%, transparent);
  color: #fca5a5;
  font-size: 0.85rem;
  line-height: 1.4;
}

.error-msg svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: #f87171;
}

/* Login button */
.login-btn {
  height: var(--button-height, 40px);
  padding: var(--button-padding, 0 20px);
  border-radius: var(--button-radius, 8px);
  background: var(--button-bg);
  color: var(--button-color, #fff);
  border: var(--button-border, none);
  font-size: var(--font-size-base, 0.875rem);
  font-weight: var(--font-weight-medium, 500);
  font-family: var(--font-ui, inherit);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  margin-top: 6px;
  transition: background 0.18s, transform 0.15s, box-shadow 0.18s;
  box-shadow: var(--shadow-button, 0 2px 8px rgba(0,0,0,0.2));
}

.login-btn:hover:not(:disabled) {
  background: var(--button-hover-bg);
  transform: translateY(-1px);
  box-shadow: var(--shadow-button, 0 4px 16px rgba(0,0,0,0.3));
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-btn svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Spinner */
.spinner {
  width: 15px;
  height: 15px;
  border: 2px solid color-mix(in srgb, currentColor 30%, transparent);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
