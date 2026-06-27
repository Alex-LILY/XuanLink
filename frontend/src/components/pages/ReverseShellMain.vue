<script setup>
import { store } from '@/assets/store';
import { addPopup, postDataOrPopupError } from '@/assets/utils';
import { ref } from 'vue';
import { t } from '@/i18n'


const props = defineProps({
  session: String,
})

if (props.session) {
  store.session = props.session
} else {
  alert(t.value.reverseShell.noSession)
}

const host = ref("");
const port = ref("");

async function doConnect() {
  if (!/\d+/.test(port.value)) {
    addPopup("red", t.value.reverseShell.errPortTitle, t.value.reverseShell.errPortMsg)
    return
  }
  addPopup("blue", t.value.reverseShell.timeoutWarnTitle, t.value.reverseShell.timeoutWarnMsg)


  const result = postDataOrPopupError(`/session/${store.session}/open_reverse_shell`, {
    host: host.value,
    port: port.value,
  })
  console.log("请求发送完毕")
}

</script>

<template>
  <div class="main">
    <div class="panel shadow-box">
      <div class="panel-line">
        <h2>{{ t.reverseShell.title }}</h2>
      </div>
      <div class="panel-line">
        <p>{{ t.reverseShell.host }}</p>
        <input type="text" placeholder="x.x.x.x" v-model="host">
      </div>
      <div class="panel-line">
        <p>{{ t.reverseShell.port }}</p>
        <input type="text" placeholder="8080" v-model="port">
      </div>
      <div class="panel-line">
        <input type="button" class="button" :value="t.reverseShell.connect" @click="doConnect">
      </div>
    </div>
  </div>
</template>

<style scoped>
.main {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
}

.panel {
  width: min(420px, 90vw);
  border-radius: var(--card-radius);
  background-color: var(--card-bg);
  border: var(--card-border);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  box-shadow: var(--card-shadow);
  padding: 28px 32px;
  color: var(--font-color-primary);
}

.panel-line {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
}

.panel-line h2,
.panel-line p {
  margin: 0;
}

.panel-line input[type="text"] {
  margin-left: 12px;
  padding: 0 12px;
  flex-grow: 1;
  height: var(--control-height);
  background-color: var(--input-bg);
  border-radius: var(--input-radius);
  outline: none;
  border: var(--input-border);
  color: var(--font-color-primary);
  font-size: var(--font-size-base);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.panel-line input[type="text"]:focus {
  border-color: var(--input-focus-border-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color) 15%, transparent);
}
</style>