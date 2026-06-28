<script setup>
import { ref, shallowRef, reactive, watch, computed } from "vue";
import { getDataOrPopupError, postDataOrPopupError, addPopup, doAssert } from "@/assets/utils"
import GroupedForm from "@/components/GroupedForm.vue"
import { store } from "@/assets/store";
import { useRouter } from "vue-router"
import { t, sessionTypeName, optionGroupName, optionName, optionPlaceholder } from "@/i18n"

const proxyAlternatives = ref([])

async function fetchProxyAlternatives() {
  try {
    const proxies = await getDataOrPopupError("/http_proxies") || []
    proxyAlternatives.value = proxies.map(p => ({
      name: p.note ? `${p.url} (${p.note})` : p.url,
      value: p.url,
    }))
  } catch (e) {
    proxyAlternatives.value = []
  }
}

function applyProxyAlternatives() {
  const currentProxy = optionValues.proxy || ""
  const base = proxyAlternatives.value
  const values = new Set(base.map(a => a.value))
  let alternatives = base
  if (currentProxy && !values.has(currentProxy)) {
    alternatives = [
      { name: `${currentProxy}${t.value.webshellEditor.proxyExpired}`, value: currentProxy },
      ...base,
    ]
  }
  for (const group of optionsGroups.value) {
    for (const option of group.options) {
      if (option.id === "proxy") {
        option.alternatives = alternatives
      }
    }
  }
  if (optionValues.proxy === undefined || optionValues.proxy === null) {
    optionValues.proxy = ""
  }
}

const router = useRouter()
const props = defineProps({
  session: String,
  modalMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(["saved", "closed"])

if (props.session) {
  store.session = props.session
}

const basicOptionGroup = reactive({
  name: t.value.webshellEditor.basicGroup,
  options: [
    { id: "name", name: t.value.webshellEditor.name, type: "text", placeholder: "xxx", default_value: undefined },
    { id: "note", name: t.value.webshellEditor.note, type: "text", placeholder: "xxx...", default_value: t.value.webshellEditor.noNote },
    { id: "tags", name: t.value.webshellEditor.tags, type: "text", placeholder: t.value.webshellEditor.tagsPh, default_value: "" },
    { id: "session_type", name: t.value.webshellEditor.type, type: "select", default_value: undefined, alternatives: [] },
  ]
})

watch(t, (newT) => {
  basicOptionGroup.name = newT.webshellEditor.basicGroup
  basicOptionGroup.options[0].name = newT.webshellEditor.name
  basicOptionGroup.options[1].name = newT.webshellEditor.note
  basicOptionGroup.options[2].name = newT.webshellEditor.tags
  basicOptionGroup.options[2].placeholder = newT.webshellEditor.tagsPh
  basicOptionGroup.options[3].name = newT.webshellEditor.type
  if (optionValues.session_type) {
    updateOption(optionValues.session_type)
  } else {
    optionsGroups.value = [...optionsGroups.value]
  }
})

const optionValues = reactive({
  name: "",
  session_type: "ONELINE_PHP",
  tags: ""
})
const optionsGroups = shallowRef([])

function translateOptions(groups) {
  for (let group of groups) {
    group.name = optionGroupName(group.name)
    for (let option of group.options) {
      option.name = optionName(option.name)
      if (option.placeholder) {
        option.placeholder = optionPlaceholder(option.placeholder)
      }
      if (option.alternatives) {
        for (let alt of option.alternatives) {
          alt.name = optionName(alt.name)
        }
      }
    }
  }
  return groups
}

async function updateOption(sessionType) {
  let options = await getDataOrPopupError(`/sessiontype/${sessionType}/conn_options`)
  optionsGroups.value = translateOptions([basicOptionGroup, ...options])
  for (let group of optionsGroups.value) {
    for (let option of group.options) {
      if (option.default_value !== undefined && option.default_value !== null) {
        optionValues[option.id] = option.default_value
      }
    }
  }
  applyProxyAlternatives()
}

async function fetchSupportedSessionTypes() {
  const sessionTypes = await getDataOrPopupError("/sessiontype")
  let optionIdx = basicOptionGroup.options.findIndex(option => option.id == 'session_type')
  basicOptionGroup.options[optionIdx].alternatives = sessionTypes.map(sessionType => {
    return {
      name: sessionTypeName(sessionType.id, sessionType.name),
      value: sessionType.id
    }
  })
}

async function fetchCurrentSession() {
  const session = await getDataOrPopupError(`/session/${props.session}`)
  await updateOption(session.session_type)
  for (const group of optionsGroups.value) {
    for (const option of group.options) {
      doAssert(["text", "checkbox", "select"].includes(option.type), t.value.webshellEditor.internalErr)
      if (["name", "session_type", "note"].includes(option.id)) {
        optionValues[option.id] = session[option.id]
      } else if (option.id === "tags") {
        const tags = session.tags || []
        optionValues.tags = Array.isArray(tags) ? tags.join(", ") : String(tags)
      } else if (session.connection[option.id] !== undefined && session.connection[option.id] !== null) {
        optionValues[option.id] = session.connection[option.id]
      }
    }
  }
  applyProxyAlternatives()
}

function getCurrentSession() {
  let session = { connection: {} }
  if (!optionValues["session_type"]) {
    return undefined;
  }
  for (const group of optionsGroups.value) {
    for (const option of group.options) {
      doAssert(["text", "checkbox", "select"].includes(option.type), t.value.webshellEditor.internalErr)
      if (optionValues[option.id] === undefined || optionValues[option.id] == null) {
        addPopup("red", `${t.value.webshellEditor.optionEmptyTitle}: ${option.name}`, `${option.name} ${t.value.webshellEditor.optionEmptyMsg}`)
        return undefined
      }
      if (["name", "session_type", "note"].includes(option.id)) {
        session[option.id] = optionValues[option.id]
      } else if (option.id === "tags") {
        session.tags = optionValues.tags
          ? optionValues.tags.split(/[,，]/).map(t => t.trim()).filter(t => t)
          : []
      } else {
        session.connection[option.id] = optionValues[option.id]
      }
    }
  }
  if (store.session) {
    session.session_id = store.session;
  }
  return session
}

async function testSession() {
  let session = getCurrentSession()
  if (!session) return;
  let data = await postDataOrPopupError("/test_webshell", session)
  if (!data.success) {
    addPopup("red", t.value.webshellEditor.testFailTitle, data.msg)
  } else {
    addPopup("green", t.value.webshellEditor.testOkTitle, data.msg)
  }
}

async function saveSession() {
  let session = getCurrentSession()
  if (!session) return;
  let sessionId = await postDataOrPopupError("/update_webshell", session)
  if (!sessionId) {
    addPopup("red", t.value.webshellEditor.saveFailTitle, t.value.webshellEditor.saveFailMsg)
  } else {
    addPopup("green", t.value.webshellEditor.saveOkTitle, t.value.webshellEditor.saveOkMsg)
    let sessionInfo = await getDataOrPopupError(`/session/${sessionId}/`)
    store.sessionName = sessionInfo.name
    setTimeout(() => {
      if (props.modalMode) {
        emit("saved")
      } else {
        router.push("/")
      }
    }, 1000);
  }
}

function onUpdateOption(optionId, value) {
  optionValues[optionId] = value
  // If session_type changes, reload options
  if (optionId === "session_type") {
    updateOption(value)
  }
}

const buttons = computed(() => [
  { id: "discard", label: t.value.webshellEditor.discard },
  { id: "save", label: t.value.webshellEditor.save },
  { id: "test", label: t.value.webshellEditor.test },
])

function onButtonClick(button) {
  if (button.id === "discard") {
    if (props.modalMode) {
      emit("closed")
    } else {
      router.go(-1)
    }
  } else if (button.id === "save") {
    saveSession()
  } else if (button.id === "test") {
    testSession()
  }
}

setTimeout(async () => {
  await fetchProxyAlternatives();
  await fetchSupportedSessionTypes();
  if (props.session) {
    await fetchCurrentSession()
  } else {
    await updateOption("ONELINE_PHP")
  }
}, 0)
</script>

<template>
  <GroupedForm
    :groups="optionsGroups"
    :modelValue="optionValues"
    @update:modelValue="onUpdateOption"
    :buttons="buttons"
    @button-click="onButtonClick"
  />
</template>
