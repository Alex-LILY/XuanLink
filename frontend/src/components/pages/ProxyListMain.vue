<script setup>
import { ref, onMounted, computed, watch } from "vue"
import axios from "axios"
import Pagination from "@/components/Pagination.vue"
import { t } from "@/i18n"
import IconBatchAdd from "@/components/icons/iconBatchAdd.vue"
import IconSingleAdd from "@/components/icons/iconSingleAdd.vue"
import IconTestSpeed from "@/components/icons/iconTestSpeed.vue"
import IconLoad from "@/components/icons/iconLoad.vue"
import IconCross from "@/components/icons/iconCross.vue"
import IconCheck from "@/components/icons/iconCheck.vue"
import {
  addPopup,
  getCurrentApiUrl,
  getDataOrPopupError,
  postDataOrPopupError,
  parseDataOrPopupError,
} from "@/assets/utils"

const proxies = ref([])
const httpProxyPage = ref(1)
const httpProxyPageSize = 25
const httpProxyTotalPages = computed(() => Math.max(1, Math.ceil(proxies.value.length / httpProxyPageSize)))
const pagedProxies = computed(() => {
  const start = (httpProxyPage.value - 1) * httpProxyPageSize
  return proxies.value.slice(start, start + httpProxyPageSize)
})
watch(proxies, () => {
  if (httpProxyPage.value > httpProxyTotalPages.value) {
    httpProxyPage.value = httpProxyTotalPages.value
  }
})
const batchInput = ref("")
const batchProtocol = ref("http")
const showBatchModal = ref(false)
const showAddModal = ref(false)
const proxyProtocol = ref("http")
const proxyHost = ref("")
const proxyPort = ref("")
const proxyUsername = ref("")
const proxyPassword = ref("")
const proxyNote = ref("")
const testingConnection = ref(false)
const testingAll = ref(false)
const testingIds = ref(new Set())

async function loadProxies() {
  proxies.value = await getDataOrPopupError("/http_proxies")
}

const newProxyUrl = computed(() => {
  if (!proxyHost.value.trim() || !proxyPort.value.trim()) return ""
  const scheme = proxyProtocol.value
  const host = proxyHost.value.trim()
  const port = proxyPort.value.trim()
  const user = proxyUsername.value.trim()
  const passwd = proxyPassword.value.trim()
  let auth = ""
  if (user) {
    auth = passwd ? `${encodeURIComponent(user)}:${encodeURIComponent(passwd)}@` : `${encodeURIComponent(user)}@`
  }
  return `${scheme}://${auth}${host}:${port}`
})

function resetAddModal() {
  proxyProtocol.value = "http"
  proxyHost.value = ""
  proxyPort.value = ""
  proxyUsername.value = ""
  proxyPassword.value = ""
  proxyNote.value = ""
  showAddModal.value = false
  testingConnection.value = false
}

function resetBatchModal() {
  batchInput.value = ""
  batchProtocol.value = "http"
  showBatchModal.value = false
}

async function onBatchAdd() {
  const lines = batchInput.value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
  if (lines.length === 0) {
    addPopup("yellow", t.value.proxyList.tipTitle, t.value.proxyList.errNoProxy)
    return
  }
  const result = await postDataOrPopupError("/http_proxies/batch", {
    urls: lines,
    scheme: batchProtocol.value,
  })
  addPopup("green", t.value.proxyList.batchOkTitle, t.value.proxyList.batchOkMsg.replace('{n}', result.length))
  resetBatchModal()
  await loadProxies()
}

async function onTestConnection() {
  const url = newProxyUrl.value
  if (!url) {
    addPopup("yellow", t.value.proxyList.tipTitle, t.value.proxyList.errNoFull)
    return
  }
  testingConnection.value = true
  try {
    const result = await postDataOrPopupError("/http_proxies/test", { url })
    if (result.status === "ok") {
      addPopup("green", t.value.proxyList.testOkTitle, `${result.latency_ms} ms`)
    } else {
      addPopup("red", t.value.proxyList.testFailTitle, t.value.proxyList.testFailMsg)
    }
  } finally {
    testingConnection.value = false
  }
}

async function onSingleAdd() {
  const url = newProxyUrl.value
  if (!url) {
    addPopup("yellow", t.value.proxyList.tipTitle, t.value.proxyList.errNoFull)
    return
  }
  await postDataOrPopupError("/http_proxies", {
    url,
    note: proxyNote.value.trim(),
  })
  addPopup("green", t.value.proxyList.addOkTitle, t.value.proxyList.addOkMsg)
  resetAddModal()
  await loadProxies()
}

async function onDelete(proxy) {
  const url = `${getCurrentApiUrl()}/http_proxies/${proxy.proxy_id}`
  try {
    const resp = await axios.delete(url)
    parseDataOrPopupError(resp)
    await loadProxies()
  } catch (e) {
    // parseDataOrPopupError already shows popup
  }
}

async function onTestOne(proxy) {
  testingIds.value.add(proxy.proxy_id)
  try {
    await postDataOrPopupError(`/http_proxies/${proxy.proxy_id}/test_speed`)
    await loadProxies()
  } finally {
    testingIds.value.delete(proxy.proxy_id)
  }
}

async function onTestAll() {
  if (proxies.value.length === 0) {
    addPopup("yellow", t.value.proxyList.tipTitle, t.value.proxyList.noProxySpeed)
    return
  }
  testingAll.value = true
  try {
    await postDataOrPopupError("/http_proxies/test_all")
    await loadProxies()
  } finally {
    testingAll.value = false
  }
}

function formatLatency(latency) {
  if (latency === null || latency === undefined) return "-"
  return `${latency} ms`
}

function formatStatus(status) {
  if (status === "ok") return t.value.proxyList.statusOk
  if (status === "fail") return t.value.proxyList.statusFail
  return t.value.proxyList.statusUnknown
}

function statusClass(status) {
  if (status === "ok") return "status-ok"
  if (status === "fail") return "status-fail"
  return "status-unknown"
}

onMounted(() => {
  loadProxies()
})
</script>

<template>
  <div class="proxy-list-page">
    <div class="toolbar">
      <button class="button" @click="showBatchModal = true">
        <IconBatchAdd /> {{ t.proxyList.batchAdd }}
      </button>
      <button class="button" @click="showAddModal = true">
        <IconSingleAdd /> {{ t.proxyList.singleAdd }}
      </button>
      <button class="button" @click="onTestAll" :disabled="testingAll">
        <IconLoad v-if="testingAll" class="spin" /> <IconTestSpeed v-else /> {{ t.proxyList.speedTest }}
      </button>
    </div>

    <div class="proxy-table-wrapper shadow-box" v-if="proxies.length">
      <table class="proxy-table">
        <thead>
          <tr>
            <th>{{ t.proxyList.colAddr }}</th>
            <th>{{ t.proxyList.colProtocol }}</th>
            <th>{{ t.proxyList.colLatency }}</th>
            <th>{{ t.proxyList.colLastCheck }}</th>
            <th>{{ t.proxyList.colStatus }}</th>
            <th>{{ t.proxyList.colOps }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="proxy in pagedProxies" :key="proxy.proxy_id">
            <td class="proxy-url">
              <div>{{ proxy.url }}</div>
              <div v-if="proxy.note" class="proxy-note">{{ proxy.note }}</div>
            </td>
            <td>
              <span class="protocol-tag">{{ proxy.protocol ? proxy.protocol.toUpperCase() : '-' }}</span>
            </td>
            <td>{{ formatLatency(proxy.latency_ms) }}</td>
            <td>{{ proxy.last_checked_at ? proxy.last_checked_at.replace('T', ' ').split('.')[0] : '-' }}</td>
            <td>
              <span class="status-tag" :class="statusClass(proxy.status)">
                {{ formatStatus(proxy.status) }}
              </span>
            </td>
            <td>
              <div class="row-actions">
                <button class="icon-btn" :title="t.proxyList.testSpeed" @click="onTestOne(proxy)" :disabled="testingIds.has(proxy.proxy_id)">
                  <IconLoad v-if="testingIds.has(proxy.proxy_id)" class="spin" />
                  <IconCheck v-else />
                </button>
                <button class="icon-btn icon-btn-danger" :title="t.proxyList.delete" @click="onDelete(proxy)">
                  <IconCross />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <Pagination :total="proxies.length" :page-size="httpProxyPageSize" v-model="httpProxyPage" />
    </div>

    <div class="empty-state" v-else>
      <p>{{ t.proxyList.empty }}</p>
    </div>
  </div>

  <Teleport to="body">
    <transition>
      <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.proxyList.addModal }}</h2>
            <button class="modal-close" @click="resetAddModal" :title="t.proxyList.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label>{{ t.proxyList.labelProtocol }}</label>
              <select v-model="proxyProtocol">
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="socks5">SOCKS5</option>
              </select>
            </div>
            <div class="form-row">
              <label>{{ t.proxyList.labelIp }}</label>
              <input type="text" v-model="proxyHost" placeholder="82.47.203.217" />
            </div>
            <div class="form-row">
              <label>{{ t.proxyList.labelPort }}</label>
              <input type="text" v-model="proxyPort" placeholder="50100" />
            </div>
            <div class="form-row">
              <label>{{ t.proxyList.labelUser }}</label>
              <input type="text" v-model="proxyUsername" placeholder="" />
            </div>
            <div class="form-row">
              <label>{{ t.proxyList.labelPw }}</label>
              <input type="text" v-model="proxyPassword" placeholder="" />
            </div>
            <div class="form-row">
              <label>{{ t.proxyList.labelNote }}</label>
              <input type="text" v-model="proxyNote" placeholder="" />
            </div>
            <div class="form-actions">
              <button class="button button-secondary" @click="resetAddModal">{{ t.proxyList.cancel }}</button>
              <button class="button" @click="onTestConnection" :disabled="testingConnection">
                <IconLoad v-if="testingConnection" class="spin" />
                <IconCheck v-else />
                {{ t.proxyList.testConn }}
              </button>
              <button class="button" @click="onSingleAdd">{{ t.proxyList.save }}</button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <Teleport to="body">
    <transition>
      <div v-if="showBatchModal" class="modal-overlay" @click="showBatchModal = false">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.proxyList.batchModal }}</h2>
            <button class="modal-close" @click="resetBatchModal" :title="t.proxyList.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label>{{ t.proxyList.labelProtocol }}</label>
              <select v-model="batchProtocol">
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="socks5">SOCKS5</option>
              </select>
            </div>
            <textarea v-model="batchInput" class="batch-textarea" rows="8"
              placeholder="lingweblll:MuxrefQrzg@82.47.203.217:50100&#10;lingweblll:MuxrefQrzg@82.47.203.206:50100"></textarea>
            <div class="form-actions">
              <button class="button button-secondary" @click="resetBatchModal">{{ t.proxyList.cancel }}</button>
              <button class="button" @click="onBatchAdd">{{ t.proxyList.confirmAdd }}</button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.proxy-list-page {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.batch-textarea {
  width: 100%;
  resize: vertical;
  border: none;
  outline: none;
  border-radius: 12px;
  padding: 12px;
  font-size: 0.85rem;
  font-family: inherit;
  background-color: var(--background-color-1);
  color: var(--font-color-primary);
}

.toolbar {
  display: flex;
  gap: 12px;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: var(--button-height);
  padding: var(--button-padding);
  border-radius: var(--button-radius);
  border: var(--button-border);
  outline: none;
  background-color: var(--button-bg);
  color: var(--button-color);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background-color var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: var(--shadow-button);
}

.button:hover:not(:disabled) {
  background-color: var(--button-hover-bg);
}

.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button-secondary {
  background-color: var(--button-secondary-bg);
  color: var(--button-secondary-color);
  border: var(--button-secondary-border);
  box-shadow: none;
}

.button-secondary:hover:not(:disabled) {
  background-color: var(--button-secondary-hover-bg);
}

.button svg {
  width: 16px;
  height: 16px;
}

.proxy-table-wrapper {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  backdrop-filter: var(--card-backdrop);
  padding: 16px;
  overflow-x: auto;
}

.proxy-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  color: var(--font-color-primary);
}

.proxy-table th,
.proxy-table td {
  padding: 12px 10px;
  text-align: left;
  border-bottom: 1px solid var(--background-color-3);
}

.proxy-table th {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--font-color-secondary);
}

.proxy-url {
  max-width: 360px;
  word-break: break-all;
}

.proxy-note {
  font-size: 0.75rem;
  color: var(--font-color-secondary);
  margin-top: 4px;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 0.75rem;
}

.protocol-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  background-color: var(--background-color-3);
  color: var(--font-color-secondary);
  font-weight: 500;
}

.status-ok {
  background-color: rgba(74, 222, 128, 0.15);
  color: var(--green);
  border: 1px solid rgba(74, 222, 128, 0.3);
}

.status-fail {
  background-color: rgba(255, 123, 123, 0.15);
  color: var(--red);
  border: 1px solid rgba(255, 123, 123, 0.3);
}

.status-unknown {
  background-color: var(--background-color-3);
  color: var(--font-color-secondary);
}

.row-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: var(--icon-btn-size);
  height: var(--icon-btn-size);
  border-radius: var(--icon-btn-radius);
  border: var(--icon-btn-border);
  outline: none;
  background-color: var(--icon-btn-bg);
  color: var(--icon-btn-color);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.icon-btn:hover:not(:disabled) {
  background-color: var(--icon-btn-hover-bg);
  color: var(--font-color-primary);
}

.icon-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon-btn svg {
  width: 14px;
  height: 14px;
  stroke: currentColor;
}

.icon-btn-danger:hover {
  background-color: var(--red);
  color: #ffffff;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--font-color-secondary);
  font-size: 0.9rem;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: var(--modal-overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-container {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--modal-radius);
  box-shadow: var(--shadow-float);
  backdrop-filter: var(--card-backdrop);
  width: 90%;
  max-width: 500px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color-grey);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--font-color-primary);
}

.modal-close {
  width: var(--icon-btn-size);
  height: var(--icon-btn-size);
  border-radius: var(--icon-btn-radius);
  border: none;
  background-color: var(--icon-btn-bg);
  color: var(--icon-btn-color);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.modal-close:hover {
  background-color: var(--icon-btn-hover-bg);
  color: var(--font-color-primary);
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row label {
  font-size: var(--font-size-base);
  color: var(--font-color-secondary);
}

.form-row input,
.form-row select {
  height: var(--control-height);
  border-radius: var(--input-radius);
  border: var(--input-border);
  outline: none;
  padding: 0 12px;
  font-size: var(--font-size-base);
  background-color: var(--input-bg);
  color: var(--input-color);
}

.form-row input:focus,
.form-row select:focus {
  border-color: var(--input-focus-border-color);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

@media (max-width: 900px) {
  .proxy-table th,
  .proxy-table td {
    padding: 10px 8px;
  }
}

@media (max-width: 600px) {
  .proxy-table th:nth-child(4),
  .proxy-table td:nth-child(4) {
    display: none;
  }
}
</style>