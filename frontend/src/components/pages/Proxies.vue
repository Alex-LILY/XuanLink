<script setup>

import { addPopup, getCurrentApiUrl, getDataOrPopupError, parseDataOrPopupError, postDataOrPopupError } from "@/assets/utils";
import { reactive, ref, watch, computed } from "vue";
import { t, sessionTypeName } from "@/i18n"
import iconCross from "@/components/icons/iconCross.vue";
import { store } from "@/assets/store";
import axios from "axios";
import Pagination from "@/components/Pagination.vue";

const props = defineProps({
  session: String,
})

if (props.session) {
  store.session = props.session
}


const sessions = ref([])

const PHP_SESSION_TYPES = new Set([
  "ONELINE_PHP",
  "PHP_RAW",
  "BEHINDER_PHP_AES",
  "BEHINDER_PHP_XOR",
  "GHOST_PHP",
  "GODZILLA_PHP_XOR_BASE64",
  "GODZILLA_PHP_XOR_RAW",
])

const phpSessions = computed(() =>
  sessions.value.filter((s) => PHP_SESSION_TYPES.has(s.type))
)

const readableProxyType = computed(() => ({
  vessel_http_proxy: t.value.proxies.typeHttp,
  vessel_socks5_proxy: t.value.proxies.typeSocks5,
}))

const openedProxies = ref([])
const proxyPage = ref(1)
const proxyPageSize = 25
const proxyTotalPages = computed(() => Math.max(1, Math.ceil(openedProxies.value.length / proxyPageSize)))
const pagedOpenedProxies = computed(() => {
  const start = (proxyPage.value - 1) * proxyPageSize
  return openedProxies.value.slice(start, start + proxyPageSize)
})
watch(openedProxies, () => {
  if (proxyPage.value > proxyTotalPages.value) {
    proxyPage.value = proxyTotalPages.value
  }
})

// TODO: support not just remote IP but remote address

const addProxyInput = reactive({
  type: "",
  session_id: "",
  listen_host: "",
  listen_port: "",
})

// null: no input, false: input invalid, true: input valid
const addProxyInputValid = reactive({
  session_id: null,
  listen_host: null,
  listen_port: null,
})

async function createProxy() {
  if (addProxyInput.type == "") {
    addPopup("red", t.value.proxies.errNoTypeTitle, t.value.proxies.errNoTypeMsg)
    return
  }
  if (addProxyInput.session_id == "") {
    addPopup("red", t.value.proxies.errNoSessionTitle, t.value.proxies.errNoSessionMsg)
    return
  }
  const invalid = ["listen_host", "listen_port"].filter(field => !addProxyInputValid[field])
  if (invalid.length != 0) {
    addPopup("red", t.value.proxies.errNoFieldsTitle, t.value.proxies.errNoFieldsMsg.replace('{field}', invalid[0]))
    return
  }

  const data = {
    "type": addProxyInput.type,
    "session_id": addProxyInput.session_id,
    "listen_host": addProxyInput.listen_host,
    "listen_port": parseInt(addProxyInput.listen_port),
    "host": null,
    "port": null,
    "send_method": null,
  }
  await postDataOrPopupError("/forward_proxy/create_psudo_proxy", data)
  addPopup("green", t.value.proxies.addOkTitle, t.value.proxies.addOkMsg
    .replace('{host}', addProxyInput.listen_host)
    .replace('{port}', addProxyInput.listen_port)
    .replace('{type}', readableProxyType.value[addProxyInput.type]))
  Object.keys(addProxyInput).forEach(key => {
    addProxyInput[key] = ""
  });
  openedProxies.value = await getDataOrPopupError("/forward_proxy/list")

}
async function closeProxy(listen_port) {
  const response = await axios.delete(`${getCurrentApiUrl()}/forward_proxy/${listen_port}/`)
  try {
    const result = parseDataOrPopupError(response)
    if (!result) {
      addPopup("yellow", t.value.proxies.closeFailTitle, t.value.proxies.closeFailMsg)
    }
  } finally {
    openedProxies.value = await getDataOrPopupError("/forward_proxy/list")
  }
}

watch(addProxyInput, (newValue, oldValue) => {
  addProxyInputValid.session_id = newValue.session_id == "" ? null : true
  addProxyInputValid.listen_host = newValue.listen_host == "" ? null : /^\d+\.\d+\.\d+\.\d+$/.test(newValue.listen_host)
  addProxyInputValid.listen_port = newValue.listen_port == "" ? null : /^\d{1,5}$/.test(newValue.listen_port)
})

setTimeout(async () => {
  const newSessions = await getDataOrPopupError("/session")
  sessions.value = newSessions.map(session => ({
    name: session.name,
    readable_type: session.readable_type,
    id: session.id,
    type: session.type,
  }))
}, 0)

setTimeout(async () => {
  openedProxies.value = await getDataOrPopupError("/forward_proxy/list")
}, 0)

setTimeout(() => {
  if (store.session) {
    addProxyInput.session_id = store.session
  }
}, 0)

</script>

<template>
  <div class="add-proxy shadow-box">
    <form action="" class="add-proxy-form" @submit.prevent="createProxy">
      <select name="proxy_type" id="" v-model="addProxyInput.type">
        <option value="">{{ t.proxies.typePh }}</option>
        <option v-for="proxyType in Object.keys(readableProxyType)" :value="proxyType">{{
          readableProxyType[proxyType] }}</option>
      </select>
      <select name="session" id="" v-model="addProxyInput.session_id">
        <option :value="''">{{ t.proxies.sessionPh }}</option>
        <option v-for="session in phpSessions" :value="session.id">{{ sessionTypeName(session.type, session.readable_type) }} - {{ session.name }}</option>
      </select>
      <input type="text" name="listen_host" id="" :placeholder="t.proxies.hostPh" v-model="addProxyInput.listen_host"
        :data-valid="addProxyInputValid.listen_host">
      <input type="text" name="listen_port" id="" :placeholder="t.proxies.portPh" v-model="addProxyInput.listen_port"
        :data-valid="addProxyInputValid.listen_port">
      <input type="button" :value="t.proxies.addBtn" @click="createProxy">
    </form>
  </div>
  <table class="opened-proxies shadow-box">
    <tr class="opened-proxies-row">
      <th class="open-proxies-head">Session</th>
      <th class="open-proxies-head">{{ t.proxies.colProxyType }}</th>
      <th class="open-proxies-head">{{ t.proxies.colListenIp }}</th>
      <th class="open-proxies-head">{{ t.proxies.colListenPort }}</th>
      <th class="open-proxies-head">{{ t.proxies.colOps }}</th>
    </tr>
    <tr class="opened-proxies-row" v-for="proxy in pagedOpenedProxies" :key="proxy.listen_port">
      <td class="open-proxies-data">{{ proxy.session_name }}</td>
      <td class="open-proxies-data">{{ readableProxyType[proxy.type] || proxy.type }}</td>
      <td class="open-proxies-data">{{ proxy.listen_host }}</td>
      <td class="open-proxies-data">{{ proxy.listen_port }}</td>
      <td class="open-proxies-data">
        <div class="close-proxy-button" @click="closeProxy(proxy.listen_port)">
          <iconCross></iconCross>
        </div>
      </td>
    </tr>
  </table>
  <Pagination :total="openedProxies.length" :page-size="proxyPageSize" v-model="proxyPage" />
</template>

<style scoped>
.add-proxy {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  backdrop-filter: var(--card-backdrop);
  width: 100%;
  height: 70px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-around;
}

.add-proxy-form {
  width: 80%;
  height: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-around;
}

.add-proxy input,
.add-proxy select {
  height: var(--control-height);
  min-width: 90px;
  border-radius: var(--input-radius);
  border: var(--input-border);
  outline: 2px solid transparent;
  background-color: var(--input-bg);
  color: var(--input-color);
  font-size: var(--font-size-base);
  padding-left: 10px;
  padding-right: 10px;
  transition: outline-color 0.3s ease, border-color 0.3s ease;
}

.add-proxy input:focus,
.add-proxy select:focus {
  outline: 2px solid var(--input-focus-border-color);
}

.add-proxy select option {
  background-color: var(--card-bg);
  color: var(--font-color-primary);
}

.add-proxy input:not(:focus)[data-valid="false"] {
  outline: 2px solid var(--red);
}

.add-proxy input:not(:focus)[data-valid="true"] {
  outline: 2px solid var(--green);
}

.add-proxy input[type="text"] {
  max-width: 120px;
}

.opened-proxies {
  margin-top: 20px;
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  backdrop-filter: var(--card-backdrop);
  width: 100%;
  height: max-content;
  color: var(--font-color-primary);
  font-size: var(--font-size-base);
  padding-left: 20px;
}

.opened-proxies-row {
  height: var(--table-row-height);
}

.open-proxies-head,
.open-proxies-data {
  padding-left: 10px;
  text-align: left;
}

.close-proxy-button {
  stroke: var(--font-color-primary);
  width: 24px;
  height: 24px;
  background-color: var(--red);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.close-proxy-button svg {
  width: 18px;
  height: 18px;
}
</style>
