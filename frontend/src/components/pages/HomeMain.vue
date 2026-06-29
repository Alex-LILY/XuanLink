<script setup>
import { ref, computed, watch } from "vue";
import IconCode from "@/components/icons/iconCode.vue"
import Pagination from "@/components/Pagination.vue"
import IconDelete from "@/components/icons/iconDelete.vue"
import IconEdit from "@/components/icons/iconEdit.vue"
import IconFileBrowser from "@/components/icons/iconFileBrowser.vue"
import IconHash from "@/components/icons/iconHash.vue"
import IconInfo from "@/components/icons/iconInfo.vue"
import IconPlus from "@/components/icons/iconPlus.vue"
import IconCross from "@/components/icons/iconCross.vue"
import IconProxy from "@/components/icons/iconProxy.vue"
import IconTerminal from "@/components/icons/iconTerminal.vue"
import IconLoad from "@/components/icons/iconLoad.vue";

import ClickMenu from "@/components/ClickMenu.vue"
import { addPopup, ClickMenuManager, getDataOrPopupError, postDataOrPopupError, parseDataOrPopupError } from "@/assets/utils";
import { useRouter } from "vue-router"
import WebshellEditorMain from "@/components/pages/WebshellEditorMain.vue"
import TerminalMain from "@/components/pages/TerminalMain.vue"
import FileBrowserMain from "@/components/pages/FileBrowserMain.vue"
import WebshellGenerator from "@/components/WebshellGenerator.vue"
import { TerminalApi } from 'vue-web-terminal'
import axios from "axios"
import sanitizeHtml from "sanitize-html";

import { getCurrentApiUrl } from "@/assets/utils";
import { store } from "@/assets/store";
import { t, sessionTypeName } from "@/i18n"

const sessions = ref([])
const currentPage = ref(1)
const pageSize = 25
const searchQuery = ref("")
const selectedSessionIds = ref(new Set())

const isAllPageSelected = computed(() => {
  if (pagedSessions.value.length === 0) return false
  return pagedSessions.value.every(session => selectedSessionIds.value.has(session.id))
})

function toggleSessionSelection(sessionId) {
  const newSet = new Set(selectedSessionIds.value)
  if (newSet.has(sessionId)) {
    newSet.delete(sessionId)
  } else {
    newSet.add(sessionId)
  }
  selectedSessionIds.value = newSet
}

function toggleSelectAllPage() {
  const newSet = new Set(selectedSessionIds.value)
  const allSelected = isAllPageSelected.value
  for (const session of pagedSessions.value) {
    if (allSelected) {
      newSet.delete(session.id)
    } else {
      newSet.add(session.id)
    }
  }
  selectedSessionIds.value = newSet
}

const sortColumn = ref("")
const sortOrder = ref("asc")

const tableColumns = computed(() => [
  { key: "id", label: "ID" },
  { key: "name", label: t.value.home.col.name },
  { key: "note", label: t.value.home.col.note },
  { key: "tags", label: t.value.home.col.tags },
  { key: "readable_type", label: t.value.home.col.type },
  { key: "url", label: "URL" },
  { key: "os", label: t.value.home.col.os },
  { key: "internal_ip", label: t.value.home.col.ip },
  { key: "username", label: t.value.home.col.user },
  { key: "last_connected_at", label: t.value.home.col.lastConn },
  { key: "status", label: t.value.home.col.status },
])

function toggleSort(column) {
  if (sortColumn.value === column) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc"
  } else {
    sortColumn.value = column
    sortOrder.value = "asc"
  }
}

function sortIndicator(column) {
  if (sortColumn.value !== column) return ""
  return sortOrder.value === "asc" ? "↑" : "↓"
}

function getSortValue(session, key) {
  if (key === "tags") {
    return (session.tags || []).join(",")
  }
  return session[key] || ""
}

const filteredSessions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let list = sessions.value
  if (q) {
    list = list.filter(session => {
      const fields = [
        session.name,
        session.note,
        session.url,
        session.internal_ip,
        session.username,
        session.readable_type,
        session.os,
        ...(session.tags || [])
      ]
      return fields.some(value =>
        String(value || "").toLowerCase().includes(q)
      )
    })
  }
  if (sortColumn.value) {
    const key = sortColumn.value
    const order = sortOrder.value === "asc" ? 1 : -1
    list = [...list].sort((a, b) => {
      let av = String(getSortValue(a, key)).toLowerCase()
      let bv = String(getSortValue(b, key)).toLowerCase()
      if (av < bv) return -1 * order
      if (av > bv) return 1 * order
      return 0
    })
  }
  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredSessions.value.length / pageSize)))
const pagedSessions = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredSessions.value.slice(start, start + pageSize)
})
watch(filteredSessions, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value
  }
})
function extractIp(ip) {
  if (!ip) return '-'
  const match = ip.match(/\b(\d{1,3}\.){3}\d{1,3}\b/)
  return match ? match[0] : ip.trim()
}

const router = useRouter();
let clickedSession = null

function getSessionMenuItems() {
  return [
    { name: "terminal", text: t.value.home.menu.terminal, icon: IconTerminal, color: "white", link: undefined, func: (session) => openTerminalModal(session) },
    { name: "browse_files", text: t.value.home.menu.files, icon: IconFileBrowser, color: "white", link: undefined, func: (session) => openFileBrowserModal(session) },
    { name: "open_proxy", text: t.value.home.menu.proxy, icon: IconProxy, color: "white", link: "/proxies/SESSION" },
    { name: "get_info", text: t.value.home.menu.info, icon: IconInfo, color: "white", link: undefined, func: (session) => openBasicInfoModal(session) },
    { name: "edit_session", text: t.value.home.menu.edit, icon: IconEdit, color: "white", link: undefined, func: (session) => openEditModal(session) },
    { name: "delete_session", text: t.value.home.menu.delete, icon: IconDelete, color: "red", link: undefined, func: (session) => onMarkDeleteSession(session) },
  ]
}

const ClickMenuSession = ClickMenuManager(
  getSessionMenuItems(),
  (item) => {
    if (item.name === "batch_delete") {
      item.func()
      return
    }
    if (item.link) {
      const uri = item.link.replace("SESSION", clickedSession.id)
      router.push(uri)
    } else if (item.func) {
      item.func(clickedSession)
    }
  }
)

watch(t, (newT) => {
  ClickMenuSession.items.value = getSessionMenuItems()
})

watch(selectedSessionIds, () => {
  ClickMenuSession.items.value = getSessionMenuItems()
}, { deep: true })

function onRowRightClick(event, session) {
  clickedSession = session;
  store.session = session.id;
  ClickMenuSession.items.value = getSessionMenuItems()
  ClickMenuSession.onshow(event)
}

async function fetchWebshell() {
  const newSessions = await getDataOrPopupError("/session")
  sessions.value = newSessions
}

setTimeout(fetchWebshell, 0)

function isCacheFresh(lastConnectedAt) {
  if (!lastConnectedAt) return false
  const last = new Date(lastConnectedAt).getTime()
  if (isNaN(last)) return false
  return Date.now() - last < 2 * 60 * 60 * 1000
}

async function probeSession(session, force = false) {
  if (!force && isCacheFresh(session.last_connected_at)) {
    addPopup("green", t.value.home.probe.cacheValidTitle, `${session.name} ${t.value.home.probe.cacheValidMsg}`)
    return
  }
  try {
    await postDataOrPopupError(`/session/${session.id}/probe`, {})
    addPopup("green", t.value.home.probe.doneTitle, t.value.home.probe.doneMsg)
  } catch (e) {
    addPopup("red", t.value.home.probe.errTitle, String(e))
  } finally {
    setTimeout(fetchWebshell, 0)
  }
}

async function probeAllSessions() {
  try {
    await postDataOrPopupError("/session/probe_all", {})
    addPopup("green", t.value.home.probe.allDoneTitle, t.value.home.probe.allDoneMsg)
    setTimeout(fetchWebshell, 0)
  } catch (e) {
    addPopup("red", t.value.home.probe.errTitle, String(e))
  }
}

function statusText(status) {
  return t.value.home.status[status] || status
}

async function openBasicInfoModal(session) {
  basicInfoTitle.value = `${t.value.home.modal.basicInfoTitle} - ${session.name}`
  basicInfoData.value = []
  basicInfoLoading.value = true
  showBasicInfoModal.value = true
  try {
    basicInfoData.value = await getDataOrPopupError(`/session/${session.id}/basicinfo`)
  } catch (e) {
    showBasicInfoModal.value = false
  } finally {
    basicInfoLoading.value = false
  }
}

function looksLikeHtml(value) {
  return typeof value === 'string' && /<[^>]+>/.test(value)
}

function safeHtml(value) {
  return sanitizeHtml(value, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(['font']),
    allowedAttributes: {
      font: ['size', 'color'],
    },
  })
}

function openTerminalModal(session, pwd = "") {
  terminalSession.value = session.id
  terminalPwd.value = pwd
  showTerminalModal.value = true
}

function clearTerminal() {
  TerminalApi.clearLog("my-terminal")
}

function openFileBrowserModal(session) {
  fileBrowserSession.value = session.id
  showFileBrowserModal.value = true
}

function onFileBrowserOpenTerminal(pwd) {
  showFileBrowserModal.value = false
  openTerminalModal({ id: fileBrowserSession.value }, pwd)
}

const showBasicInfoModal = ref(false)
const basicInfoTitle = ref("")
const basicInfoData = ref([])
const basicInfoLoading = ref(false)

const showTerminalModal = ref(false)
const terminalSession = ref(null)
const terminalPwd = ref("")

const showFileBrowserModal = ref(false)
const fileBrowserSession = ref(null)

const showGeneratorModal = ref(false)

let sessionToDelete = undefined
const sessionToDeleteName = ref("")
const showDeleteModal = ref(false)

function onMarkDeleteSession(session) {
  sessionToDelete = session.id
  sessionToDeleteName.value = session.name || session.url || session.id
  showDeleteModal.value = true
}

async function confirmDelete() {
  if (!sessionToDelete) {
    addPopup("red", t.value.home.delErrNotFound, t.value.home.delErrNotFoundMsg)
    return
  }
  try {
    let response = await axios.delete(`${getCurrentApiUrl()}/session/${sessionToDelete}`)
    let result = parseDataOrPopupError(response)
    if (result) {
      addPopup("green", t.value.home.delOkTitle, t.value.home.delOkMsg + sessionToDeleteName.value)
    } else {
      addPopup("red", t.value.home.delErrTitle, t.value.home.delErrMsg + sessionToDeleteName.value)
    }
  } finally {
    showDeleteModal.value = false
    sessionToDelete = undefined
    sessionToDeleteName.value = ""
    setTimeout(fetchWebshell, 0)
  }
}

function cancelDelete() {
  showDeleteModal.value = false
  sessionToDelete = undefined
  sessionToDeleteName.value = ""
}

const batchDeleteSessionIds = ref([])
const showBatchDeleteModal = ref(false)

function onBatchDelete() {
  const ids = Array.from(selectedSessionIds.value)
  if (ids.length === 0) return
  batchDeleteSessionIds.value = ids
  showBatchDeleteModal.value = true
}

async function confirmBatchDelete() {
  if (batchDeleteSessionIds.value.length === 0) {
    addPopup("red", t.value.home.delErrNotFound, t.value.home.delErrNotFoundMsg)
    return
  }
  try {
    const result = await postDataOrPopupError("/batch_delete_sessions", {
      session_ids: batchDeleteSessionIds.value,
    })
    if (result.deleted > 0) {
      addPopup("green", t.value.home.batchDelOkTitle,
        t.value.home.batchDelOkMsg.replace('{count}', result.deleted))
      selectedSessionIds.value = new Set()
    }
    if (result.failed && result.failed.length > 0) {
      addPopup("red", t.value.home.batchDelErrTitle,
        `${result.failed.length} ${t.value.home.batchDelErrMsg}`)
    }
  } finally {
    showBatchDeleteModal.value = false
    batchDeleteSessionIds.value = []
    setTimeout(fetchWebshell, 0)
  }
}

function cancelBatchDelete() {
  showBatchDeleteModal.value = false
  batchDeleteSessionIds.value = []
}

function selectSession(session) {
  store.session = session.id
}

const showAddModal = ref(false)
const editingSessionId = ref("")

function onAddSaved() {
  showAddModal.value = false
  setTimeout(fetchWebshell, 0)
}

function openAddModal() {
  editingSessionId.value = ""
  store.session = ""
  showAddModal.value = true
}

function openEditModal(session) {
  editingSessionId.value = session.id
  store.session = session.id
  showAddModal.value = true
}

const showBatchImportModal = ref(false)
const batchImportContent = ref("")
const batchImportLoading = ref(false)
const batchImportResult = ref(null)

function openBatchImportModal() {
  batchImportContent.value = ""
  batchImportResult.value = null
  showBatchImportModal.value = true
}

function closeBatchImportModal() {
  showBatchImportModal.value = false
  batchImportContent.value = ""
  batchImportResult.value = null
}

async function confirmBatchImport() {
  const content = batchImportContent.value.trim()
  if (!content) {
    addPopup("red", t.value.home.modal.batchImportResultTitle, t.value.home.modal.batchImportNoData)
    return
  }
  batchImportLoading.value = true
  batchImportResult.value = null
  try {
    const result = await postDataOrPopupError("/batch_import_webshells", {
      content: content,
      session_type: "ONELINE_PHP",
      delimiter: "|",
    })
    batchImportResult.value = result
    if (result.created > 0) {
      setTimeout(fetchWebshell, 0)
    }
  } catch (e) {
    // postDataOrPopupError 已经弹出错误
  } finally {
    batchImportLoading.value = false
  }
}

</script>

<template>
  <div class="page-container">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <button class="tool-btn secondary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
          {{ t.home.toolGlobalProbe }}
        </button>
        <button class="tool-btn secondary" @click="probeAllSessions">
          <IconLoad />
          {{ t.home.toolRefreshAll }}
        </button>
        <div class="toolbar-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input v-model="searchQuery" type="text" :placeholder="t.home.search" />
        </div>
      </div>
      <div class="toolbar-right">
        <button v-if="selectedSessionIds.size > 0" class="tool-btn danger" @click="onBatchDelete">
          <IconDelete />
          {{ t.home.toolDeleteSelected }}（{{ selectedSessionIds.size }}）
        </button>
        <button class="tool-btn secondary" @click="showGeneratorModal = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          {{ t.home.toolGenerate }}
        </button>
        <button class="tool-btn secondary" @click="openBatchImportModal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          {{ t.home.toolBatchImport }}
        </button>
        <button class="tool-btn primary" @click="openAddModal">
          <IconPlus />
          {{ t.home.modal.addTitle }}
        </button>
      </div>
    </div>

    <div class="table-card shadow-box" v-if="sessions.length != 0">
      <div class="table-scroll-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-checkbox"><input type="checkbox" :checked="isAllPageSelected" @change="toggleSelectAllPage" /></th>
            <th v-for="col in tableColumns" :key="col.key" class="sortable-header" @click="toggleSort(col.key)">
              {{ col.label }}<span v-if="sortColumn === col.key" class="sort-indicator">{{ sortIndicator(col.key) }}</span>
            </th>
            <th>{{ t.home.colOps }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in pagedSessions" :key="session.id" @click="selectSession(session)"
            @contextmenu.prevent="(event) => onRowRightClick(event, session)"
            :class="{ selected: store.session === session.id }">
            <td class="col-checkbox" @click.stop><input type="checkbox" :checked="selectedSessionIds.has(session.id)" @change="toggleSessionSelection(session.id)" /></td>
            <td class="mono">{{ session.id.slice(0, 8) }}</td>
            <td class="session-name">{{ session.name }}</td>
            <td class="session-note">{{ session.note || '-' }}</td>
            <td>
              <div v-if="session.tags && session.tags.length" class="tag-list">
                <span v-for="tag in session.tags" :key="tag" class="tag-badge">{{ tag }}</span>
              </div>
              <span v-else>-</span>
            </td>
            <td>
              <span class="type-badge" :data-type="session.type">{{ sessionTypeName(session.type, session.readable_type) }}</span>
            </td>
            <td class="mono url-cell">{{ session.url }}</td>
            <td>{{ session.os }}</td>
            <td class="mono">{{ extractIp(session.internal_ip) }}</td>
            <td>{{ session.username }}</td>
            <td class="mono">{{ session.last_connected_at }}</td>
            <td>
              <span class="status-badge" :data-status="session.status">
                <span class="status-dot"></span>
                {{ statusText(session.status) }}
              </span>
            </td>
            <td>
              <div class="row-actions">
                <button class="icon-btn" :title="t.home.menu.refreshCache" @click.stop="probeSession(session, true)">
                  <IconLoad />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <Pagination :total="sessions.length" :page-size="pageSize" v-model="currentPage" />
    </div>

    <div class="empty-state" v-else>
      <div class="empty-state-icon">
        <IconTerminal></IconTerminal>
      </div>
      <p class="empty-state-title">{{ t.home.empty.title }}</p>
      <p class="empty-state-subtitle">{{ t.home.empty.subtitle }}</p>
      <button class="tool-btn primary empty-state-action" @click="openAddModal">
        <IconPlus />
        {{ t.home.empty.addBtn }}
      </button>
    </div>
  </div>

  <transition>
    <div v-if="ClickMenuSession.show.value">
      <ClickMenu :mouse_y="ClickMenuSession.y" :mouse_x="ClickMenuSession.x" :menuItems="ClickMenuSession.items.value"
        @remove="ClickMenuSession.onremove" @clickItem="ClickMenuSession.onclick" />
    </div>
  </transition>

  <Teleport to="body">
    <transition>
      <div v-if="showDeleteModal" class="modal-overlay" @click.self="cancelDelete">
        <div class="modal-container delete-modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.home.modal.deleteTitle }}</h2>
            <button class="modal-close" @click="cancelDelete" :title="t.home.modal.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body delete-modal-body">
            <p class="delete-modal-text">
              {{ t.home.modal.deleteConfirm }} <strong>{{ sessionToDeleteName }}</strong>{{ t.home.modal.deleteConfirm2 }}
            </p>
            <div class="delete-modal-actions">
              <button class="tool-btn secondary" @click="cancelDelete">{{ t.home.modal.cancel }}</button>
              <button class="tool-btn danger" @click="confirmDelete">{{ t.home.modal.confirmDelete }}</button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <Teleport to="body">
    <transition>
      <div v-if="showBatchDeleteModal" class="modal-overlay" @click.self="cancelBatchDelete">
        <div class="modal-container delete-modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.home.modal.batchDeleteTitle }}</h2>
            <button class="modal-close" @click="cancelBatchDelete" :title="t.home.modal.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body delete-modal-body">
            <p class="delete-modal-text">
              {{ t.home.modal.batchDeleteConfirm }} <strong>{{ batchDeleteSessionIds.length }}</strong>{{ t.home.modal.batchDeleteConfirm2 }}
            </p>
            <div class="delete-modal-actions">
              <button class="tool-btn secondary" @click="cancelBatchDelete">{{ t.home.modal.cancel }}</button>
              <button class="tool-btn danger" @click="confirmBatchDelete">{{ t.home.modal.confirmDelete }}</button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <WebshellGenerator :show="showGeneratorModal" @close="showGeneratorModal = false" />

  <Teleport to="body">
    <transition>
      <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ editingSessionId ? t.home.modal.editTitle : t.home.modal.addTitle }}</h2>
            <button class="modal-close" @click="showAddModal = false" :title="t.home.modal.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body">
            <WebshellEditorMain :session="editingSessionId" modal-mode @saved="onAddSaved"
              @closed="showAddModal = false" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <Teleport to="body">
    <transition>
      <div v-if="showBatchImportModal" class="modal-overlay" @click="closeBatchImportModal">
        <div class="modal-container batch-import-modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.home.modal.batchImportTitle }}</h2>
            <button class="modal-close" @click="closeBatchImportModal" :title="t.home.modal.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body batch-import-modal-body">
            <p class="batch-import-hint">{{ t.home.modal.batchImportHint }}</p>
            <textarea class="batch-import-textarea" v-model="batchImportContent" rows="12"
              :placeholder="t.home.modal.batchImportPlaceholder" :disabled="batchImportLoading"></textarea>
            <div v-if="batchImportResult" class="batch-import-result">
              <p class="batch-import-result-title">{{ t.home.modal.batchImportResultTitle }}</p>
              <p class="batch-import-result-success">
                {{ t.home.modal.batchImportSuccess.replace('{count}', batchImportResult.created) }}
              </p>
              <p v-if="batchImportResult.skipped" class="batch-import-result-skipped">
                {{ t.home.modal.batchImportSkipped.replace('{count}', batchImportResult.skipped) }}
              </p>
              <p v-if="batchImportResult.failed.length" class="batch-import-result-failed">
                {{ t.home.modal.batchImportFailed.replace('{count}', batchImportResult.failed.length) }}
              </p>
              <ul v-if="batchImportResult.failed.length" class="batch-import-failed-list">
                <li v-for="(item, idx) in batchImportResult.failed" :key="idx">
                  {{ t.home.col.id }} {{ item.line }}: {{ item.reason }}
                </li>
              </ul>
            </div>
            <div class="batch-import-actions">
              <button class="tool-btn secondary" @click="closeBatchImportModal" :disabled="batchImportLoading">
                {{ t.home.modal.batchImportCancel }}
              </button>
              <button class="tool-btn primary" @click="confirmBatchImport" :disabled="batchImportLoading">
                <span v-if="batchImportLoading" class="loading-spinner"></span>
                {{ t.home.modal.batchImportStart }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <Teleport to="body">
    <transition>
      <div v-if="showBasicInfoModal" class="modal-overlay basic-info-modal-overlay" @click="showBasicInfoModal = false">
        <div class="modal-container basic-info-modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ basicInfoTitle }}</h2>
            <button class="modal-close" @click="showBasicInfoModal = false" :title="t.home.modal.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body basic-info-modal-body">
            <div v-if="basicInfoLoading" class="basic-info-loading">{{ t.home.modal.basicInfoLoading }}</div>
            <div v-else-if="basicInfoData.length === 0" class="basic-info-empty">{{ t.home.modal.basicInfoEmpty }}</div>
            <table v-else class="basic-info-table">
              <tbody>
                <tr v-for="item in basicInfoData" :key="item.key">
                  <td class="basic-info-key">{{ item.key }}</td>
                  <td class="basic-info-value" :class="{ 'pre-wrap': !looksLikeHtml(item.value) }">
                    <span v-if="looksLikeHtml(item.value)" v-html="safeHtml(item.value)"></span>
                    <span v-else>{{ item.value }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <Teleport to="body">
    <transition>
      <div v-if="showTerminalModal" class="modal-overlay terminal-modal-overlay" @click="showTerminalModal = false">
        <div class="modal-container terminal-modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.home.terminalTitle }}</h2>
            <div class="terminal-header-actions">
              <button class="tool-btn secondary terminal-clear-btn" @click="clearTerminal" :title="t.home.clearTerminal">
                {{ t.home.clearTerminal }}
              </button>
              <button class="modal-close" @click="showTerminalModal = false" :title="t.home.modal.close">
                <IconCross />
              </button>
            </div>
          </div>
          <div class="modal-body terminal-modal-body">
            <TerminalMain v-if="terminalSession" :session="terminalSession" :pwd="terminalPwd" modal-mode
              @close="showTerminalModal = false" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <Teleport to="body">
    <transition>
      <div v-if="showFileBrowserModal" class="modal-overlay file-browser-modal-overlay"
        @click="showFileBrowserModal = false">
        <div class="modal-container file-browser-modal-container" @click.stop>
          <div class="modal-header">
            <h2>{{ t.home.fileBrowserTitle }}</h2>
            <button class="modal-close" @click="showFileBrowserModal = false" :title="t.home.modal.close">
              <IconCross />
            </button>
          </div>
          <div class="modal-body file-browser-modal-body">
            <FileBrowserMain v-if="fileBrowserSession" :session="fileBrowserSession" modal-mode
              @close="showFileBrowserModal = false" @open-terminal="onFileBrowserOpenTerminal" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.page-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 0 4px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.toolbar-search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: var(--control-height);
  padding: 0 14px;
  border-radius: var(--button-radius);
  border: var(--input-border);
  background-color: var(--input-bg);
  color: var(--font-color-secondary);
  min-width: 240px;
  max-width: 360px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.toolbar-search:focus-within {
  border-color: var(--input-focus-border-color);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--input-focus-border-color) 20%, transparent);
}

.toolbar-search svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke: currentColor;
}

.toolbar-search input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--font-color-primary);
  font-size: var(--font-size-base);
  min-width: 0;
}

.toolbar-search input::placeholder {
  color: var(--font-color-secondary);
  opacity: 0.7;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: var(--control-height);
  padding: 0 16px;
  border-radius: var(--button-radius);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  border: var(--button-border);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
}

.tool-btn svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
}

.tool-btn.primary {
  background: var(--button-bg);
  color: var(--button-color);
  border: none;
  box-shadow: var(--shadow-button);
}

.tool-btn.primary:hover {
  background: var(--button-hover-bg);
}

.tool-btn.secondary {
  background: var(--button-secondary-bg);
  color: var(--button-secondary-color);
  border: var(--button-secondary-border, none);
}

.tool-btn.secondary:hover {
  background: var(--button-secondary-hover-bg);
}

.tool-btn.danger {
  background-color: #dc2626;
  color: #ffffff;
  border-color: #dc2626;
}

.tool-btn.danger:hover {
  background-color: #b91c1c;
  border-color: #b91c1c;
}

.table-card {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  backdrop-filter: var(--card-backdrop);
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-base);
}

.data-table th,
.data-table td {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--table-border-color);
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.data-table th {
  background-color: var(--table-header-bg);
  color: var(--table-header-color);
  font-weight: var(--font-weight-medium);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.sortable-header {
  cursor: pointer;
  user-select: none;
  transition: color var(--transition-fast);
}

.sortable-header:hover {
  color: var(--accent-color);
}

.sort-indicator {
  margin-left: 6px;
  font-size: 0.75rem;
  color: var(--accent-color);
}

.data-table tbody tr {
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.data-table tbody tr:hover {
  background-color: var(--table-row-hover-bg);
}

.data-table tbody tr.selected {
  background-color: var(--background-color-hover);
}

.col-checkbox {
  width: 40px;
  text-align: center;
}

.col-checkbox input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary-color);
}

.session-name {
  font-weight: var(--font-weight-medium);
  color: var(--font-color-primary);
}

.session-note {
  color: var(--font-color-secondary);
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono {
  font-family: var(--font-mono);
  color: var(--font-color-secondary);
  font-size: 0.85rem;
}

.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.8rem;
  font-weight: var(--font-weight-medium);
  background-color: var(--background-color-3);
  color: var(--font-color-secondary);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-width: 160px;
}

.tag-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: var(--font-weight-medium);
  background-color: var(--background-color-3);
  color: var(--font-color-secondary);
  border: 1px solid var(--border-color-grey);
  white-space: nowrap;
}

.url-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.8rem;
  font-weight: var(--font-weight-medium);
  background-color: var(--background-color-3);
  color: var(--font-color-secondary);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
}

.status-badge[data-status="online"] {
  background-color: var(--green);
  color: #000000;
}

.status-badge[data-status="offline"] {
  background-color: var(--red);
  color: #ffffff;
}

.status-badge[data-status="unknown"] {
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
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--icon-btn-radius);
  border: var(--icon-btn-border);
  background-color: var(--icon-btn-bg);
  color: var(--icon-btn-color);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.icon-btn:hover {
  background-color: var(--icon-btn-hover-bg);
  color: var(--font-color-primary);
}

.icon-btn svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
}

.empty-state {
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
}

.empty-state svg {
  width: 80px;
  height: 80px;
  stroke: var(--border-color-grey);
}

.empty-state p {
  font-size: 1rem;
  color: var(--font-color-secondary);
  margin-top: 16px;
}

.table-scroll-wrapper {
  overflow-x: auto;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--modal-overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 20px;
}

.modal-container {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--modal-radius);
  box-shadow: var(--shadow-float);
  backdrop-filter: var(--card-backdrop);
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color-grey);
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
}

.modal-close {
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

.modal-close:hover {
  background-color: var(--background-color-hover);
  color: var(--font-color-primary);
}

.modal-close svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
}

.modal-body {
  overflow-y: auto;
  padding: 20px;
  flex: 1;
  min-height: 0;
}

.delete-modal-container {
  max-width: 420px;
  width: 100%;
}

.delete-modal-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.delete-modal-text {
  margin: 0;
  color: var(--font-color-primary);
  line-height: 1.6;
}

.delete-modal-text strong {
  color: var(--accent-color);
  word-break: break-all;
}

.delete-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.batch-import-modal-container {
  max-width: 600px;
  width: 90%;
  max-height: 85vh;
  height: auto;
}

.batch-import-modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.batch-import-hint {
  margin: 0;
  color: var(--font-color-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
}

.batch-import-textarea {
  width: 100%;
  min-height: 180px;
  padding: 12px;
  border: 1px solid var(--border-color-grey);
  border-radius: var(--input-radius);
  background-color: var(--input-bg);
  color: var(--font-color-primary);
  font-family: var(--font-mono);
  font-size: 0.9rem;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.batch-import-textarea:focus {
  border-color: var(--accent-color);
}

.batch-import-textarea::placeholder {
  color: var(--font-color-tertiary);
}

.batch-import-result {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: var(--card-radius);
  background-color: var(--background-color-secondary);
}

.batch-import-result-title {
  margin: 0;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
}

.batch-import-result-success {
  margin: 0;
  color: var(--success-color, #2ecc71);
}

.batch-import-result-skipped {
  margin: 0;
  color: var(--font-color-secondary);
}

.batch-import-result-failed {
  margin: 0;
  color: var(--danger-color, #e74c3c);
}

.batch-import-failed-list {
  margin: 0;
  padding-left: 20px;
  color: var(--font-color-secondary);
  font-size: 0.85rem;
  max-height: 120px;
  overflow-y: auto;
}

.batch-import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 4px;
}

.basic-info-modal-container {
  max-width: 700px;
  width: 90%;
  max-height: 80vh;
  height: auto;
}

.basic-info-modal-body {
  padding: 0;
  background-color: var(--card-bg);
}

.basic-info-loading,
.basic-info-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--font-color-secondary);
  font-size: 1rem;
}

.basic-info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  color: var(--font-color-primary);
}

.basic-info-table tr:not(:last-child) {
  border-bottom: 1px solid var(--border-color-grey);
}

.basic-info-table td {
  padding: 12px 16px;
  vertical-align: top;
  word-break: break-word;
}

.basic-info-key {
  width: 140px;
  font-weight: var(--font-weight-semibold);
  color: var(--font-color-secondary);
  background-color: var(--background-color-2);
  white-space: nowrap;
}

.basic-info-value {
  font-family: var(--font-mono);
  background-color: var(--card-bg);
}

.pre-wrap {
  white-space: pre-wrap;
}

.terminal-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-clear-btn {
  font-size: 0.85rem;
  padding: 0 12px;
}

.terminal-modal-container,
.file-browser-modal-container {
  max-width: 95vw;
  width: 95vw;
  max-height: 90vh;
  height: 90vh;
}

.terminal-modal-body,
.file-browser-modal-body {
  padding: 0;
  overflow: hidden;
}

/* 列序号：1复选框 2ID 3名称 4备注 5标签 6类型 7URL 8系统 9内网IP 10用户名 11最后连接 12状态 13操作 */
@media (max-width: 1100px) {
  .data-table th:nth-child(11),
  .data-table td:nth-child(11) {
    display: none;
  }
}

@media (max-width: 900px) {
  .data-table th:nth-child(5),
  .data-table td:nth-child(5),
  .data-table th:nth-child(10),
  .data-table td:nth-child(10) {
    display: none;
  }
}

@media (max-width: 600px) {
  .page-toolbar {
    flex-wrap: wrap;
    gap: 12px;
  }

  .toolbar-left {
    width: 100%;
    order: 2;
  }

  .tool-btn.primary {
    width: 100%;
    order: 1;
    justify-content: center;
  }

  .data-table th,
  .data-table td {
    padding: 8px 10px;
  }

  .session-note {
    max-width: 120px;
  }

  .modal-container {
    max-height: 95vh;
    border-radius: var(--radius-lg);
  }

  .modal-body {
    padding: 12px;
  }
}
</style>

<style>
/* modern 主题 Home 页增强 */
body[data-theme="modern"] .page-toolbar {
  margin-bottom: 20px;
}

body[data-theme="modern"] .tool-btn {
  font-weight: 600;
  letter-spacing: 0.02em;
}

body[data-theme="modern"] .tool-btn.primary {
  background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

body[data-theme="modern"] .tool-btn.primary:hover {
  background: linear-gradient(135deg, #818cf8 0%, #67e8f9 100%);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
  transform: translateY(-1px);
}

body[data-theme="modern"] .tool-btn.secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
}

body[data-theme="modern"] .tool-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.15);
}

body[data-theme="modern"] .toolbar-search {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

body[data-theme="modern"] .toolbar-search:focus-within {
  border-color: #22d3ee;
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.15);
}

body[data-theme="modern"] .table-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  backdrop-filter: blur(24px) saturate(160%);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

body[data-theme="modern"] .data-table th {
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.75rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

body[data-theme="modern"] .data-table td {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

body[data-theme="modern"] .data-table tbody tr {
  position: relative;
  transition: background-color 0.2s ease;
}

body[data-theme="modern"] .data-table tbody tr::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #6366f1 0%, #22d3ee 100%);
  opacity: 0;
  transition: opacity 0.2s ease;
}

body[data-theme="modern"] .data-table tbody tr:hover::before,
body[data-theme="modern"] .data-table tbody tr.selected::before {
  opacity: 1;
}

body[data-theme="modern"] .data-table tbody tr:hover {
  background: rgba(99, 102, 241, 0.08);
}

body[data-theme="modern"] .data-table tbody tr.selected {
  background: rgba(99, 102, 241, 0.12);
}

body[data-theme="modern"] .type-badge,
body[data-theme="modern"] .tag-badge {
  backdrop-filter: blur(4px);
}

body[data-theme="modern"] .type-badge[data-type*="PHP"] {
  background: rgba(137, 147, 190, 0.18);
  color: #a5b4fc;
  border: 1px solid rgba(137, 147, 190, 0.25);
}

body[data-theme="modern"] .type-badge[data-type*="JSP"] {
  background: rgba(183, 114, 25, 0.18);
  color: #fdba74;
  border: 1px solid rgba(183, 114, 25, 0.25);
}

body[data-theme="modern"] .type-badge[data-type*="ASP"] {
  background: rgba(34, 211, 238, 0.12);
  color: #67e8f9;
  border: 1px solid rgba(34, 211, 238, 0.22);
}

body[data-theme="modern"] .type-badge[data-type*="GHOST"] {
  background: rgba(168, 85, 247, 0.15);
  color: #d8b4fe;
  border: 1px solid rgba(168, 85, 247, 0.22);
}

body[data-theme="modern"] .status-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

body[data-theme="modern"] .status-badge[data-status="online"] {
  background: rgba(74, 222, 128, 0.15);
  color: #86efac;
  border: 1px solid rgba(74, 222, 128, 0.25);
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.15);
}

body[data-theme="modern"] .status-badge[data-status="offline"] {
  background: rgba(255, 123, 123, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(255, 123, 123, 0.25);
}

body[data-theme="modern"] .icon-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

body[data-theme="modern"] .icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.08);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

body[data-theme="modern"] .empty-state {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  backdrop-filter: blur(24px) saturate(160%);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  gap: 12px;
}

body[data-theme="modern"] .empty-state-icon {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

body[data-theme="modern"] .empty-state-icon svg {
  width: 48px;
  height: 48px;
  stroke: #94a3b8;
}

body[data-theme="modern"] .empty-state-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0;
}

body[data-theme="modern"] .empty-state-subtitle {
  font-size: 0.9rem;
  color: #94a3b8;
  margin: 0 0 8px;
}

body[data-theme="modern"] .empty-state-action {
  margin-top: 8px;
}

body[data-theme="modern"] .modal-container {
  background: rgba(11, 15, 25, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  backdrop-filter: blur(32px) saturate(180%);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

body[data-theme="modern"] .modal-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

body[data-theme="modern"] .modal-header h2 {
  background: linear-gradient(135deg, #818cf8 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

body[data-theme="modern"] .modal-close:hover {
  background: rgba(255, 255, 255, 0.08);
}

body[data-theme="modern"] .basic-info-key {
  background: rgba(255, 255, 255, 0.04);
}

body[data-theme="modern"] .basic-info-value {
  background: transparent;
}

.empty-state-action svg {
  width: 12px !important;
  height: 12px !important;
  stroke-width: 1.5;
}
</style>
