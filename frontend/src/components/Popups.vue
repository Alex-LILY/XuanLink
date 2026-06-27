<script setup>
import { ref } from "vue"
import IconCross from "@/components/icons/iconCross.vue"
import IconCheck from "@/components/icons/iconCheck.vue"
import IconWarning from "@/components/icons/iconWarning.vue"
import IconPlus from "@/components/icons/iconPlus.vue"
import { doAssert } from "@/assets/utils"

const POPUP_SHOW_TIME = 5000;

const popups = ref([

])

function getPopup(id) {
  const selectedPopups = popups.value.filter(popup => popup.id == id)
  if (selectedPopups.length == 0) {
    return undefined
  }
  doAssert(selectedPopups.length == 1, "Multiple popups with same id")
  return selectedPopups[0]
}

function delPopup(id) {
  setTimeout(() => {
    let popup = getPopup(id)
    if (popup) {
      popup.state = "hide"
    }
  }, 0)
  setTimeout(() => {
    const idx = popups.value.findIndex(popup => popup.id == id)
    if (idx > -1) {
      popups.value.splice(idx, 1)
    }
  }, 1000)
}

function addPopup(color, title, message) {
  const id = Date.now() + Math.floor(Math.random() * 100000)
  const popup = {
    id,
    color,
    title,
    message,
    state: "show"
  }
  popups.value.push(popup)
  setTimeout(() => delPopup(id), POPUP_SHOW_TIME)
}

defineExpose({ addPopup })

</script>

<template>
  <div class="popups" v-if="popups.length != 0">
    <div class="popup shadow-box" v-for="popup in popups" :key="popup.id" :color="popup.color" :state="popup.state">
      <button class="popup-close" @click.stop="delPopup(popup.id)" aria-label="Close">
        <IconCross />
      </button>
      <div class="popup-title-line">
        <div class="popup-icon">
          <IconCross v-if="popup.color == 'red'" />
          <IconWarning v-else-if="popup.color == 'yellow'" />
          <IconCheck v-else-if="popup.color == 'green'" />
          <IconPlus v-else-if="popup.color == 'blue'" />
        </div>
        <h3 class="popup-title">
          {{ popup.title }}
        </h3>
      </div>

      <p class="popup-message">
        {{ popup.message }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.popups {
  position: fixed;
  bottom: 20px;
  right: 16px;
  width: 320px;
  max-width: calc(100vw - 32px);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.popup {
  position: relative;
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--popup-radius);
  box-shadow: var(--shadow-float);
  backdrop-filter: var(--card-backdrop);
  padding: 16px 18px;
  min-height: 5rem;
  opacity: 1;
  transform: translateX(0);
  transition: opacity 0.35s ease, transform 0.35s ease;
  animation: slide-in 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  cursor: pointer;
}

.popup:active {
  transform: scale(0.99);
}

.popup[color="red"] {
  background-color: var(--red);
}

.popup[color="yellow"] {
  background-color: var(--yellow);
}

.popup[color="green"] {
  background-color: var(--green);
}

.popup[color="blue"] {
  background-color: var(--blue);
}

.popup[color="red"] .popup-title,
.popup[color="red"] .popup-message,
.popup[color="yellow"] .popup-title,
.popup[color="yellow"] .popup-message,
.popup[color="green"] .popup-title,
.popup[color="green"] .popup-message,
.popup[color="blue"] .popup-title,
.popup[color="blue"] .popup-message {
  color: var(--font-color-black);
}

.popup[state=hide] {
  opacity: 0;
  transform: translateX(120%);
  pointer-events: none;
}

.popup-close {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease, background-color 0.2s ease;
}

.popup-close:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.12);
}

.popup-close svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
}

.popup-title-line {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding-right: 24px;
}

.popup-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.popup-icon svg {
  width: 22px;
  height: 22px;
  stroke: currentColor;
}

.popup-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: var(--font-color-primary);
  line-height: 1.3;
}

.popup-message {
  margin: 8px 0 0 32px;
  color: var(--font-color-secondary);
  font-size: 0.9rem;
  line-height: 1.4;
  word-break: break-word;
}

@keyframes slide-in {
  0% {
    opacity: 0;
    transform: translateX(120%);
  }

  100% {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
