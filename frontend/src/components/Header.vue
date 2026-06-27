<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from "vue"
import IconTerminal from "@/components/icons/iconTerminal.vue"
import IconProxy from "@/components/icons/iconProxy.vue"
import IconInfo from "@/components/icons/iconInfo.vue"
import IconSetting from "@/components/icons/iconSetting.vue"
import IconCode from "@/components/icons/iconCode.vue"
import IconHash from "@/components/icons/iconHash.vue"
import { useRouter, useRoute } from "vue-router"
import { store } from "@/assets/store.js"
import { addPopup, ClickMenuManager, getDataOrPopupError } from "@/assets/utils"
import ClickMenu from "./ClickMenu.vue"
import logoUrl from "@/assets/logo.ico"
import { t, lang, setLang } from "@/i18n"

const router = useRouter()
const route = useRoute()

const tabSpecs = computed(() => [
  {
    type: "home",
    component: IconTerminal,
    label: t.value.header.nav.webshell,
    uri: "/",
    tooltip: t.value.header.tooltip.home,
  },
  {
    type: "proxy",
    component: IconProxy,
    label: t.value.header.nav.proxy,
    uri: "/proxies",
    tooltip: t.value.header.tooltip.proxy,
  },
  {
    type: "proxy-list",
    component: IconProxy,
    label: t.value.header.nav.proxyList,
    uri: "/proxy-list",
    tooltip: t.value.header.tooltip.proxyList,
  },
  {
    type: "settings",
    component: IconSetting,
    label: t.value.header.nav.settings,
    uri: "/settings/",
    tooltip: t.value.header.tooltip.settings,
  },
  {
    type: "about",
    component: IconInfo,
    label: t.value.header.nav.about,
    uri: "/about",
    tooltip: t.value.header.tooltip.about,
  },
])

function fillSession(specs, session) {
  return specs.map(tab => {
    let clone = { ...tab }
    if (tab.uri.indexOf("SESSION") === -1) return clone
    clone.uri = session ? tab.uri.replace("SESSION", session) : "/popup/no_session"
    return clone
  })
}

const tabs = computed(() => fillSession(tabSpecs.value, store.session || ""))

const activeTabType = computed(() => {
  const path = route.path
  if (path === "/") return "home"
  if (path.startsWith("/proxy-list")) return "proxy-list"
  if (path.startsWith("/proxies")) return "proxy"
  if (path.startsWith("/settings")) return "settings"
  if (path.startsWith("/about")) return "about"
  return ""
})

// ######################
// --- Status counters ---
// ######################
const sessions = ref([])
const proxies = ref([])

async function loadStats() {
  try {
    sessions.value = await getDataOrPopupError("/session")
  } catch (e) {
    sessions.value = []
  }
  try {
    const proxyData = await getDataOrPopupError("/http_proxies")
    proxies.value = proxyData || []
  } catch (e) {
    proxies.value = []
  }
}

const shellStats = computed(() => {
  const online = sessions.value.filter(s => s.status === "online").length
  const offline = sessions.value.filter(s => s.status === "offline").length
  return { online, offline }
})

const osStats = computed(() => {
  const linux = sessions.value.filter(s =>
    String(s.os || "").toLowerCase().includes("linux")
  ).length
  const windows = sessions.value.filter(s =>
    String(s.os || "").toLowerCase().includes("windows")
  ).length
  return { linux, windows }
})

const proxyStats = computed(() => {
  const ok = proxies.value.filter(p => p.status === "ok").length
  const fail = proxies.value.filter(p => p.status !== "ok").length
  return { ok, fail }
})

let statsInterval = null
onMounted(() => {
  loadStats()
  statsInterval = setInterval(loadStats, 5000)
  document.addEventListener('click', closeUserMenu, true)
})
onUnmounted(() => {
  if (statsInterval) clearInterval(statsInterval)
  document.removeEventListener('click', closeUserMenu, true)
})

// click menus
let rightClickedTab = undefined

const clickMenuRightClick = ClickMenuManager(
  [
    { name: "open", text: t.value.header.menu.open, icon: IconHash, color: "white" },
    { name: "open_in_new_page", text: t.value.header.menu.openNewTab, icon: IconCode, color: "white" },
  ],
  (item) => {
    if (rightClickedTab.uri === "/popup/no_session") {
      addPopup("red", t.value.header.menu.noSession, t.value.header.menu.noSessionHint)
    } else if (item.name === "open") {
      router.push(rightClickedTab.uri)
    } else {
      let link = router.resolve({ path: rightClickedTab.uri })
      window.open(link.href, '_blank')
    }
  }
)

watch(t, (newT) => {
  clickMenuRightClick.items.value = [
    { name: "open", text: newT.header.menu.open, icon: IconHash, color: "white" },
    { name: "open_in_new_page", text: newT.header.menu.openNewTab, icon: IconCode, color: "white" },
  ]
})

function clickTab(event, tab) {
  if (tab.uri === "/popup/no_session") {
    addPopup("red", t.value.header.menu.noSession, t.value.header.menu.noSessionHint)
  } else {
    router.push(tab.uri)
  }
}

function rightClickTab(event, tab) {
  rightClickedTab = tab
  clickMenuRightClick.onshow(event)
}

// ── User menu ───────────────────────────────────────────────
const showUserMenu = ref(false)
const userMenuRef = ref(null)

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

function closeUserMenu(e) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target)) {
    showUserMenu.value = false
  }
}

async function logout() {
  showUserMenu.value = false
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
  } catch (_) {}
  localStorage.removeItem('ghost_auth_token')
  window.location.href = '/login.html'
}

</script>

<template>
  <header :data-bg-transition="store.theme_background_transition">
    <div class="header-left">
      <div class="header-logo">
        <img :src="logoUrl" alt="XuLink" />
      </div>
      <div class="header-brand">
        <span class="brand-name">XuLink</span>
        <span v-if="store.sessionName" class="session-name">· {{ store.sessionName }}</span>
      </div>
    </div>

    <nav class="header-nav">
      <div v-for="tab in tabs" :key="tab.type" class="nav-tab"
        :class="{ active: activeTabType === tab.type }"
        @click="(event) => clickTab(event, tab)"
        @click.right.prevent="event => rightClickTab(event, tab)"
        :title="tab.tooltip">
        <component :is="tab.component" />
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </nav>

    <div class="header-right">
      <div class="status-indicators">
        <span class="status-item"><span class="status-dot"></span>{{ t.header.status.shell }} {{ shellStats.online }}/{{ shellStats.offline }}</span>
        <span class="status-item">{{ t.header.status.terminal }} {{ osStats.linux }}/{{ osStats.windows }}</span>
        <span class="status-item">{{ t.header.status.proxy }} {{ proxyStats.ok }}/{{ proxyStats.fail }}</span>
      </div>

      <div class="lang-switcher">
        <button class="lang-btn" :class="{ active: lang === 'zh' }" @click="setLang('zh')">ZH</button>
        <button class="lang-btn" :class="{ active: lang === 'en' }" @click="setLang('en')">EN</button>
      </div>

      <div class="user-avatar-wrap" ref="userMenuRef">
        <div class="user-avatar" :class="{ active: showUserMenu }" @click="toggleUserMenu" :title="t.header.user.name">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
        </div>
        <transition name="user-menu">
          <div v-if="showUserMenu" class="user-dropdown">
            <div class="user-dropdown-header">
              <span class="user-dropdown-name">{{ t.header.user.name }}</span>
              <span class="user-dropdown-role">{{ t.header.user.role }}</span>
            </div>
            <div class="user-dropdown-divider"></div>
            <button class="user-dropdown-item logout" @click="logout">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              {{ t.header.user.logout }}
            </button>
          </div>
        </transition>
      </div>
    </div>
  </header>

  <transition>
    <div v-if="clickMenuRightClick.show.value" class="header-click-menu">
      <ClickMenu :mouse_y="clickMenuRightClick.y" :mouse_x="clickMenuRightClick.x"
        :menuItems="clickMenuRightClick.items.value" @remove="clickMenuRightClick.onremove"
        @clickItem="clickMenuRightClick.onclick" />
    </div>
  </transition>
</template>

<style scoped>
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: var(--header-height);
  padding: 0 24px;
  background-color: var(--header-bg);
  border-bottom: var(--header-border);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: background-color 0.5s ease, border-color 0.5s ease;
}

header[data-bg-transition="true"] {
  transition: background-color 0.8s ease, border-color 0.8s ease;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.header-logo {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--font-color-primary);
}

.header-logo img {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1rem;
  font-weight: var(--font-weight-bold);
  color: var(--font-color-primary);
}

.brand-name {
  font-family: "MapleMono SemiBold", var(--font-ui);
}

.session-name {
  font-size: 0.9rem;
  font-weight: var(--font-weight-normal);
  color: var(--font-color-secondary);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: center;
  margin: 0 24px;
  overflow-x: hidden;
  min-width: 0;
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 16px;
  border-radius: var(--header-nav-radius);
  cursor: pointer;
  color: var(--font-color-secondary);
  font-size: 0.95rem;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.nav-tab:hover {
  background-color: var(--background-color-hover);
  color: var(--font-color-primary);
}

.nav-tab.active {
  background-color: var(--primary-color);
  color: var(--font-color-black);
}

.nav-tab svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
  flex-shrink: 0;
}

.tab-label {
  line-height: 1;
  font-size: 0.8rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 0.85rem;
  color: var(--font-color-secondary);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--green);
}

/* Lang switcher */
.lang-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
}

.lang-btn {
  height: 26px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color-grey, rgba(255,255,255,0.12));
  background: transparent;
  color: var(--font-color-secondary);
  font-size: 0.7rem;
  font-weight: 600;
  font-family: var(--font-ui, inherit);
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.lang-btn:hover {
  color: var(--font-color-primary);
  border-color: var(--primary-color, rgba(255,255,255,0.3));
}

.lang-btn.active {
  border-color: var(--primary-color, #6366f1);
  color: var(--primary-color, #6366f1);
  background: color-mix(in srgb, var(--primary-color, #6366f1) 12%, transparent);
}

.user-avatar-wrap {
  position: relative;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--primary-color);
  color: var(--font-color-black);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  user-select: none;
}

.user-avatar:hover {
  transform: scale(1.08);
}

.user-avatar.active {
  opacity: 0.85;
}

.user-avatar svg {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

/* Dropdown */
.user-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  min-width: 168px;
  background: var(--card-bg, rgba(20,20,35,0.97));
  border: var(--card-border, 1px solid rgba(255,255,255,0.12));
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.45), 0 2px 8px rgba(0,0,0,0.3);
  overflow: hidden;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  z-index: 200;
}

.user-dropdown-header {
  padding: 12px 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-dropdown-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--font-color-primary, #fff);
}

.user-dropdown-role {
  font-size: 0.72rem;
  color: var(--font-color-secondary, rgba(255,255,255,0.45));
}

.user-dropdown-divider {
  height: 1px;
  background: var(--card-border, rgba(255,255,255,0.08));
  margin: 0;
}

.user-dropdown-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: var(--font-color-secondary, rgba(255,255,255,0.6));
  font-size: 0.85rem;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  text-align: left;
}

.user-dropdown-item:hover {
  background: rgba(255,255,255,0.06);
  color: var(--font-color-primary, #fff);
}

.user-dropdown-item.logout:hover {
  background: rgba(239,68,68,0.1);
  color: #f87171;
}

.user-dropdown-item svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

/* Dropdown animation */
.user-menu-enter-active { transition: opacity .15s ease, transform .15s ease; }
.user-menu-leave-active { transition: opacity .1s ease, transform .1s ease; }
.user-menu-enter-from, .user-menu-leave-to { opacity: 0; transform: translateY(-6px) scale(.97); }

.header-click-menu {
  z-index: 1000;
}

@media (max-width: 1100px) {
  .status-indicators {
    display: none;
  }
}

@media (max-width: 900px) {
  .tab-label {
    display: none;
  }
  .nav-tab {
    padding: 0 12px;
  }
  .session-name {
    display: none;
  }
}

@media (max-width: 600px) {
  header {
    padding: 0 12px;
  }
  .header-nav {
    margin: 0 8px;
  }
  .lang-switcher {
    display: none;
  }
}
</style>

<style>
/* modern 主题 Header 增强（非 scoped，便于命中 body data-theme） */
body[data-theme="modern"] header {
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  background: rgba(11, 15, 25, 0.72);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.25);
}

body[data-theme="modern"] .brand-name {
  background: linear-gradient(135deg, #818cf8 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

body[data-theme="modern"] .header-logo {
  filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.5));
}

body[data-theme="modern"] .header-logo img {
  width: 34px;
  height: 34px;
}

body[data-theme="modern"] .nav-tab {
  border-radius: 999px;
  padding: 0 18px;
  height: 38px;
  font-size: 0.9rem;
  position: relative;
  overflow: hidden;
}

body[data-theme="modern"] .nav-tab::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(34, 211, 238, 0.15));
  opacity: 0;
  transition: opacity 0.25s ease;
  z-index: -1;
}

body[data-theme="modern"] .nav-tab:hover::before {
  opacity: 1;
}

body[data-theme="modern"] .nav-tab.active {
  background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
  color: #fff;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
}

body[data-theme="modern"] .status-indicators {
  gap: 12px;
}

body[data-theme="modern"] .status-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--font-color-secondary);
  transition: background 0.2s ease, color 0.2s ease;
}

body[data-theme="modern"] .status-item:hover {
  background: rgba(255, 255, 255, 0.09);
  color: var(--font-color-primary);
}

body[data-theme="modern"] .status-dot {
  width: 7px;
  height: 7px;
  box-shadow: 0 0 8px currentColor;
}

body[data-theme="modern"] .user-avatar {
  background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

body[data-theme="modern"] .user-avatar:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
}

body[data-theme="modern"] .user-dropdown {
  background: rgba(9, 12, 26, 0.92);
  border: 1px solid rgba(99, 102, 241, 0.22);
  box-shadow: 0 16px 50px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255,255,255,0.04);
}

body[data-theme="modern"] .lang-btn.active {
  border-color: #6366f1;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.15);
}
</style>
