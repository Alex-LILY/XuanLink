<script setup>
import { ref, watch } from "vue"
import axios from "axios"
import { getCurrentApiUrl, addPopup } from "@/assets/utils"
import { authState } from "@/assets/store"
import { t } from "@/i18n"

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  isFirstLogin: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue", "success"])

const oldPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")
const errorMsg = ref("")
const saving = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    oldPassword.value = ""
    newPassword.value = ""
    confirmPassword.value = ""
    errorMsg.value = ""
    saving.value = false
  }
})

function close() {
  emit("update:modelValue", false)
}

async function handleSave() {
  errorMsg.value = ""

  if (!oldPassword.value) {
    errorMsg.value = t.value.changePw.errNoCurrent
    return
  }
  if (!newPassword.value) {
    errorMsg.value = t.value.changePw.errNoNew
    return
  }
  if (newPassword.value.length < 6) {
    errorMsg.value = t.value.changePw.errTooShort
    return
  }
  if (newPassword.value === oldPassword.value) {
    errorMsg.value = t.value.changePw.errSame
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMsg.value = t.value.changePw.errNoMatch
    return
  }

  saving.value = true
  try {
    await axios.post(
      `${getCurrentApiUrl()}/api/auth/change_password`,
      { old_password: oldPassword.value, new_password: newPassword.value }
    )
    authState.needsPasswordChange = false
    emit("update:modelValue", false)
    emit("success")
    addPopup("green", t.value.changePw.okTitle, t.value.changePw.okMsg)
  } catch (e) {
    if (e.response) {
      const detail = e.response.data?.detail
      errorMsg.value = detail || `${t.value.changePw.errReqFail} (${e.response.status})`
    } else {
      errorMsg.value = t.value.changePw.errNoConn
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-backdrop" @click.self="close">
      <div class="modal-card" role="dialog" aria-modal="true">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-title-row">
            <div class="modal-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
            <h2 class="modal-title">{{ isFirstLogin ? t.changePw.firstTitle : t.changePw.title }}</h2>
          </div>
          <button class="close-btn" @click="close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <!-- Default-password warning -->
        <div class="first-login-warning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ t.changePw.firstHint }}
        </div>

        <!-- Form body -->
        <div class="modal-body">
          <div class="form-field">
            <label class="form-label">{{ t.changePw.oldPw }}</label>
            <input
              type="password"
              v-model="oldPassword"
              class="form-input"
              :placeholder="t.changePw.oldPwPh"
              autocomplete="current-password"
            />
          </div>
          <div class="form-field">
            <label class="form-label">{{ t.changePw.newPw }}</label>
            <input
              type="password"
              v-model="newPassword"
              class="form-input"
              :placeholder="t.changePw.newPwPh"
              autocomplete="new-password"
            />
          </div>
          <div class="form-field">
            <label class="form-label">{{ t.changePw.confirmPw }}</label>
            <input
              type="password"
              v-model="confirmPassword"
              class="form-input"
              :placeholder="t.changePw.confirmPwPh"
              autocomplete="new-password"
              @keydown.enter="handleSave"
            />
          </div>

          <div v-if="errorMsg" class="error-msg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ errorMsg }}
          </div>
        </div>

        <!-- Footer -->
        <div class="modal-footer">
          <button class="btn-secondary" @click="close" :disabled="saving">{{ t.changePw.later }}</button>
          <button class="btn-primary" @click="handleSave" :disabled="saving">
            <span v-if="saving" class="spinner"></span>
            {{ saving ? t.changePw.saving : t.changePw.save }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
  animation: backdrop-in 0.2s ease;
}

@keyframes backdrop-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-card {
  width: 100%;
  max-width: 420px;
  background: var(--card-bg, rgba(20, 20, 35, 0.95));
  border: var(--card-border, 1px solid rgba(255,255,255,0.12));
  border-radius: var(--card-radius, 14px);
  backdrop-filter: var(--card-backdrop, blur(20px));
  -webkit-backdrop-filter: var(--card-backdrop, blur(20px));
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  animation: modal-in 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  overflow: hidden;
}

@keyframes modal-in {
  from { opacity: 0; transform: scale(0.9) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* Header */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: var(--card-border, 1px solid rgba(255,255,255,0.08));
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: color-mix(in srgb, var(--button-bg, #6366f1) 18%, transparent);
  color: var(--button-bg, #6366f1);
}

.modal-icon svg {
  width: 17px;
  height: 17px;
}

.modal-title {
  margin: 0;
  font-size: 1rem;
  font-weight: var(--font-weight-bold, 600);
  color: var(--font-color-primary, #fff);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  color: var(--font-color-secondary, rgba(255,255,255,0.5));
  cursor: pointer;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.close-btn:hover {
  color: var(--font-color-primary, #fff);
  background: color-mix(in srgb, currentColor 10%, transparent);
}

.close-btn svg {
  width: 16px;
  height: 16px;
}

/* First login warning */
.first-login-warning {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 16px 24px 0;
  padding: 12px 16px;
  border-radius: 8px;
  background: color-mix(in srgb, #f59e0b 12%, transparent);
  border: 1px solid color-mix(in srgb, #f59e0b 30%, transparent);
  color: #d97706;
  font-size: 0.875rem;
  line-height: 1.4;
}

.first-login-warning svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Body */
.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-label {
  font-size: 0.78rem;
  font-weight: var(--font-weight-medium, 500);
  color: var(--font-color-secondary, rgba(255,255,255,0.55));
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.form-input {
  width: 100%;
  height: var(--control-height, 38px);
  padding: 0 14px;
  background: var(--input-bg, rgba(255,255,255,0.06));
  border: var(--input-border, 1px solid rgba(255,255,255,0.12));
  border-radius: var(--input-radius, 7px);
  color: var(--input-color, #fff);
  font-size: var(--font-size-base, 0.875rem);
  font-family: var(--font-ui, inherit);
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--input-focus-border-color, #6366f1);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color, #6366f1) 15%, transparent);
}

.form-input::placeholder {
  color: var(--font-color-secondary, rgba(255,255,255,0.3));
}

.error-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 7px;
  background: color-mix(in srgb, #ef4444 12%, transparent);
  border: 1px solid color-mix(in srgb, #ef4444 30%, transparent);
  color: #fca5a5;
  font-size: 0.85rem;
}

.error-msg svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #f87171;
}

/* Footer */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px 20px;
  border-top: var(--card-border, 1px solid rgba(255,255,255,0.08));
}

.btn-secondary {
  height: var(--button-height, 36px);
  padding: 0 16px;
  border-radius: var(--button-radius, 7px);
  background: transparent;
  color: var(--font-color-secondary, rgba(255,255,255,0.6));
  border: var(--card-border, 1px solid rgba(255,255,255,0.12));
  font-size: var(--font-size-base, 0.875rem);
  font-weight: var(--font-weight-medium, 500);
  font-family: var(--font-ui, inherit);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.btn-secondary:hover:not(:disabled) {
  background: color-mix(in srgb, currentColor 8%, transparent);
  color: var(--font-color-primary, #fff);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  height: var(--button-height, 36px);
  padding: var(--button-padding, 0 18px);
  border-radius: var(--button-radius, 7px);
  background: var(--button-bg);
  color: var(--button-color, #fff);
  border: var(--button-border, none);
  font-size: var(--font-size-base, 0.875rem);
  font-weight: var(--font-weight-medium, 500);
  font-family: var(--font-ui, inherit);
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  transition: background 0.15s, transform 0.12s;
  box-shadow: var(--shadow-button, 0 2px 6px rgba(0,0,0,0.2));
}

.btn-primary:hover:not(:disabled) {
  background: var(--button-hover-bg);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
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
