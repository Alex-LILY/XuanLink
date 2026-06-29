<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue"
import { getDataOrPopupError } from "@/assets/utils"
import { t } from "@/i18n"

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(["update:modelValue"])

const allGroups = ref([])
const showPanel = ref(false)
const newGroupName = ref("")
const containerRef = ref(null)

async function fetchAllTags() {
  const tags = await getDataOrPopupError("/session/tags")
  if (tags) {
    allGroups.value = tags
  }
}

function isSelected(tag) {
  return props.modelValue.includes(tag)
}

function toggleTag(tag) {
  const current = [...props.modelValue]
  const idx = current.indexOf(tag)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(tag)
  }
  emit("update:modelValue", current)
}

function removeTag(tag) {
  emit("update:modelValue", props.modelValue.filter(g => g !== tag))
}

function addNewGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  if (!allGroups.value.includes(name)) {
    allGroups.value = [...allGroups.value, name].sort()
  }
  if (!props.modelValue.includes(name)) {
    emit("update:modelValue", [...props.modelValue, name])
  }
  newGroupName.value = ""
}

async function togglePanel() {
  showPanel.value = !showPanel.value
  if (showPanel.value) {
    await fetchAllTags()
  }
}

function handleClickOutside(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    showPanel.value = false
  }
}

onMounted(async () => {
  document.addEventListener("click", handleClickOutside)
  await fetchAllTags()
})

onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside)
})
</script>

<template>
  <div class="tag-selector" ref="containerRef">
    <div class="tag-selector__row">
      <span
        v-for="tag in modelValue"
        :key="tag"
        class="tag-chip"
      >
        {{ tag }}
        <button class="tag-chip__remove" type="button" @click.stop="removeTag(tag)">×</button>
      </span>
      <div
        class="tag-trigger-wrap"
        :class="{ 'tag-trigger-wrap--empty': allGroups.length === 0 }"
      >
        <button class="tag-btn" type="button" @click.stop="togglePanel">
          <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" style="flex-shrink:0">
            <path d="M1 3.5A.5.5 0 0 1 1.5 3h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 3.5zm2 3A.5.5 0 0 1 3.5 6h9a.5.5 0 0 1 0 1h-9A.5.5 0 0 1 3 6.5zm2 3A.5.5 0 0 1 5.5 9h5a.5.5 0 0 1 0 1h-5A.5.5 0 0 1 5 9.5z"/>
          </svg>
          {{ t.webshellEditor.groupLabel }}
        </button>
        <span class="tag-add-hint">{{ t.webshellEditor.groupAdd }}</span>
      </div>
    </div>

    <div v-if="showPanel" class="tag-panel" @click.stop>
      <div v-if="allGroups.length === 0" class="tag-panel__empty">{{ t.webshellEditor.groupNone }}</div>
      <label
        v-for="group in allGroups"
        :key="group"
        class="tag-panel__item"
      >
        <input
          type="checkbox"
          :checked="isSelected(group)"
          @change="toggleTag(group)"
        />
        <span>{{ group }}</span>
      </label>
      <div class="tag-panel__footer">
        <input
          v-model="newGroupName"
          class="tag-panel__input"
          type="text"
          :placeholder="t.webshellEditor.groupPh"
          @keyup.enter="addNewGroup"
          @click.stop
        />
        <button class="tag-panel__addbtn" type="button" @click.stop="addNewGroup">
          {{ t.webshellEditor.groupAdd }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-selector {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
}

.tag-selector__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: var(--control-height, 32px);
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px 2px 10px;
  background: var(--button-bg, rgba(255, 255, 255, 0.1));
  color: var(--font-color-primary, #e0e0e0);
  border-radius: 12px;
  font-size: calc(var(--font-size-base, 13px) - 1px);
  line-height: 1.5;
  border: 1px solid var(--card-border, rgba(255, 255, 255, 0.15));
}

.tag-chip__remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  margin: 0;
  font-size: 15px;
  line-height: 1;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.tag-chip__remove:hover {
  opacity: 1;
}

.tag-trigger-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tag-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: var(--button-bg, rgba(255, 255, 255, 0.06));
  color: var(--font-color-secondary, #aaa);
  border: 1px solid var(--input-border, rgba(255, 255, 255, 0.15));
  border-radius: var(--input-radius, 6px);
  cursor: pointer;
  font-size: var(--font-size-base, 13px);
  transition: background 0.15s, color 0.15s;
}
.tag-btn:hover {
  background: var(--button-bg, rgba(255, 255, 255, 0.12));
  color: var(--font-color-primary, #e0e0e0);
}

/* "添加分组" hint — visible only on hover when no groups exist */
.tag-add-hint {
  font-size: calc(var(--font-size-base, 13px) - 1px);
  color: var(--font-color-secondary, #888);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.tag-trigger-wrap--empty:hover .tag-add-hint {
  opacity: 1;
}

.tag-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 200;
  min-width: 200px;
  max-width: 320px;
  background: var(--card-bg, #1e1e2e);
  border: 1px solid var(--card-border, rgba(255, 255, 255, 0.12));
  border-radius: var(--card-radius, 8px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
  padding: 6px 0;
}

.tag-panel__empty {
  padding: 8px 14px;
  color: var(--font-color-secondary, #888);
  font-size: var(--font-size-base, 13px);
}

.tag-panel__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: var(--font-size-base, 13px);
  color: var(--font-color-primary, #e0e0e0);
  transition: background 0.1s;
}
.tag-panel__item:hover {
  background: var(--input-bg, rgba(255, 255, 255, 0.06));
}
.tag-panel__item input[type="checkbox"] {
  cursor: pointer;
  accent-color: var(--button-bg, #6c5ce7);
}

.tag-panel__footer {
  display: flex;
  gap: 6px;
  padding: 8px 10px 6px;
  border-top: 1px solid var(--card-border, rgba(255, 255, 255, 0.08));
  margin-top: 4px;
}

.tag-panel__input {
  flex: 1;
  min-width: 0;
  padding: 4px 8px;
  background: var(--input-bg, rgba(255, 255, 255, 0.06));
  border: 1px solid var(--input-border, rgba(255, 255, 255, 0.15));
  border-radius: var(--input-radius, 4px);
  color: var(--input-color, #e0e0e0);
  font-size: var(--font-size-base, 13px);
  outline: none;
  transition: border-color 0.15s;
}
.tag-panel__input:focus {
  border-color: var(--button-bg, rgba(255, 255, 255, 0.4));
}
.tag-panel__input::placeholder {
  color: var(--font-color-secondary, #888);
}

.tag-panel__addbtn {
  padding: 4px 10px;
  background: var(--button-bg, rgba(255, 255, 255, 0.1));
  color: var(--button-color, #e0e0e0);
  border: 1px solid var(--input-border, rgba(255, 255, 255, 0.15));
  border-radius: var(--input-radius, 4px);
  cursor: pointer;
  font-size: var(--font-size-base, 13px);
  white-space: nowrap;
  transition: background 0.15s;
}
.tag-panel__addbtn:hover {
  background: var(--button-bg, rgba(255, 255, 255, 0.18));
}
</style>
