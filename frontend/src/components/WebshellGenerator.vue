<script setup>
import { ref, onMounted, computed } from "vue";
import { getDataOrPopupError, postDataOrPopupError, addPopup } from "@/assets/utils";
import { t } from "@/i18n"

const props = defineProps({
  show: Boolean,
})

const emit = defineEmits(["close"])

const password = ref("")
const key = ref("")
const selectedType = ref("")
const generatedCode = ref("")
const types = ref([])
const loading = ref(false)

const needKey = computed(() => {
  const t = types.value.find(item => item.id === selectedType.value)
  return t && t.need_key
})

onMounted(async () => {
  types.value = await getDataOrPopupError("/generate_webshell/types")
  if (types.value.length) {
    selectedType.value = types.value[0].id
  }
})

async function generate() {
  if (!password.value) {
    addPopup("red", t.value.webshellGenerator.errNoPwTitle, t.value.webshellGenerator.errNoPwMsg)
    return
  }
  if (needKey.value && !key.value) {
    addPopup("red", t.value.webshellGenerator.errNoKeyTitle, t.value.webshellGenerator.errNoKeyMsg)
    return
  }
  if (!selectedType.value) {
    addPopup("red", t.value.webshellGenerator.errNoTypeTitle, t.value.webshellGenerator.errNoTypeMsg)
    return
  }
  loading.value = true
  try {
    const payload = {
      webshell_type: selectedType.value,
      password: password.value,
    }
    if (needKey.value) {
      payload.key = key.value
    }
    const code = await postDataOrPopupError("/generate_webshell", payload)
    generatedCode.value = code
  } finally {
    loading.value = false
  }
}

function copyCode() {
  if (!generatedCode.value) return
  navigator.clipboard.writeText(generatedCode.value).then(() => {
    addPopup("green", t.value.webshellGenerator.copyOkTitle, t.value.webshellGenerator.copyOkMsg)
  }).catch(() => {
    addPopup("red", t.value.webshellGenerator.copyFailTitle, t.value.webshellGenerator.copyFailMsg)
  })
}

function close() {
  password.value = ""
  key.value = ""
  generatedCode.value = ""
  emit("close")
}
</script>

<template>
  <Teleport to="body">
    <transition>
      <div v-if="show" class="generator-overlay" @click.self="close">
        <div class="generator-box">
          <div class="generator-header">
            <h3>{{ t.webshellGenerator.title }}</h3>
            <button class="generator-close" @click="close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="generator-body">
            <div class="generator-field">
              <label>{{ t.webshellGenerator.password }}</label>
              <input v-model="password" type="text" :placeholder="t.webshellGenerator.passwordPh" />
            </div>

            <div class="generator-field" v-if="needKey">
              <label>Key</label>
              <input v-model="key" type="text" :placeholder="t.webshellGenerator.keyPh" />
            </div>

            <div class="generator-field">
              <label>{{ t.webshellGenerator.type }}</label>
              <select v-model="selectedType">
                <option v-for="item in types" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </div>

            <button class="generator-btn primary" @click="generate" :disabled="loading">
              {{ loading ? t.webshellGenerator.generating : t.webshellGenerator.generate }}
            </button>

            <div class="generator-output" v-if="generatedCode">
              <div class="generator-output-header">
                <label>{{ t.webshellGenerator.result }}</label>
                <button class="generator-copy" @click="copyCode">{{ t.webshellGenerator.copy }}</button>
              </div>
              <textarea readonly v-model="generatedCode"></textarea>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.generator-overlay {
  position: fixed;
  inset: 0;
  background-color: var(--modal-overlay-bg);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: var(--card-backdrop);
}

.generator-box {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--modal-radius);
  box-shadow: var(--shadow-float);
  width: 100%;
  max-width: 720px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.generator-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color-grey);
  flex-shrink: 0;
}

.generator-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
}

.generator-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--font-color-secondary);
  border-radius: var(--icon-btn-radius);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.generator-close:hover {
  background-color: var(--background-color-hover);
  color: var(--font-color-primary);
}

.generator-close svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
}

.generator-body {
  padding: 20px;
  overflow-y: auto;
}

.generator-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.generator-field label {
  font-size: 0.85rem;
  font-weight: var(--font-weight-medium);
  color: var(--font-color-secondary);
}

.generator-field input,
.generator-field select {
  height: var(--control-height);
  padding: 0 14px;
  border-radius: var(--input-radius);
  border: var(--input-border);
  background-color: var(--input-bg);
  color: var(--input-color);
  font-size: var(--font-size-base);
  outline: none;
}

.generator-field input:focus,
.generator-field select:focus {
  border-color: var(--input-focus-border-color);
}

.generator-field select option {
  background-color: var(--card-bg);
  color: var(--font-color-primary);
}

.generator-btn {
  height: var(--control-height);
  padding: 0 20px;
  border-radius: var(--button-radius);
  border: var(--button-border);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.generator-btn.primary {
  background-color: var(--button-bg);
  color: var(--button-color);
  border-color: var(--button-bg);
}

.generator-btn.primary:hover:not(:disabled) {
  background-color: var(--button-hover-bg);
  border-color: var(--button-hover-bg);
}

.generator-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.generator-output {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.generator-output-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.generator-output-header label {
  font-size: 0.85rem;
  font-weight: var(--font-weight-medium);
  color: var(--font-color-secondary);
}

.generator-copy {
  padding: 4px 12px;
  border-radius: var(--radius-md);
  border: var(--button-border);
  background-color: var(--button-secondary-bg);
  color: var(--button-secondary-color);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.generator-copy:hover {
  background-color: var(--button-secondary-hover-bg);
}

.generator-output textarea {
  width: 100%;
  min-height: 220px;
  padding: 14px;
  border-radius: var(--radius-md);
  border: var(--input-border);
  background-color: var(--background-color-1);
  color: var(--font-color-primary);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  resize: vertical;
  outline: none;
}
</style>
