<script setup>
import { ref, shallowRef, reactive, watch, computed } from "vue";
import { getDataOrPopupError, postDataOrPopupError, addPopup, doAssert } from "@/assets/utils"
import GroupedForm from "@/components/GroupedForm.vue"
import { store } from "@/assets/store";
import { useRouter } from "vue-router"
import { t } from "@/i18n"

const router = useRouter()
const props = defineProps({
  connector: String,
})

if (props.connector) {
  store.connector = props.connector
}

const basicOptionGroup = reactive({
  name: t.value.connectorEditor.basicGroup,
  options: [
    { id: "name", name: t.value.connectorEditor.name, type: "text", placeholder: t.value.connectorEditor.connectorNamePh, default_value: undefined },
    { id: "note", name: t.value.connectorEditor.note, type: "text", placeholder: t.value.connectorEditor.notePh, default_value: t.value.connectorEditor.noNote },
    { id: "connector_type", name: t.value.connectorEditor.type, type: "select", default_value: undefined, alternatives: [] },
    { id: "autostart", name: t.value.connectorEditor.autostart, type: "checkbox", default_value: false },
  ]
})

watch(t, (newT) => {
  basicOptionGroup.name = newT.connectorEditor.basicGroup
  basicOptionGroup.options[0].name = newT.connectorEditor.name
  basicOptionGroup.options[0].placeholder = newT.connectorEditor.connectorNamePh
  basicOptionGroup.options[1].name = newT.connectorEditor.note
  basicOptionGroup.options[1].placeholder = newT.connectorEditor.notePh
  basicOptionGroup.options[2].name = newT.connectorEditor.type
  basicOptionGroup.options[3].name = newT.connectorEditor.autostart
  optionsGroups.value = [...optionsGroups.value]
})

const optionValues = reactive({
  name: "",
  connector_type: "",
  note: t.value.connectorEditor.noNote,
  autostart: false
})
const optionsGroups = shallowRef([])

async function updateOption(connectorType) {
  let options = await getDataOrPopupError(`/connectortype/${connectorType}/conn_options`)
  optionsGroups.value = [basicOptionGroup, ...options]
  for (let group of optionsGroups.value) {
    for (let option of group.options) {
      if (option.default_value !== undefined && option.default_value !== null) {
        optionValues[option.id] = option.default_value
      }
    }
  }
}

async function fetchSupportedConnectorTypes() {
  const data = await getDataOrPopupError("/connectortype")
  let optionIdx = basicOptionGroup.options.findIndex(option => option.id == 'connector_type')
  basicOptionGroup.options[optionIdx].alternatives = data.map(connectorType => {
    return {
      name: connectorType.name,
      value: connectorType.type
    }
  })
}

async function fetchCurrentConnector() {
  const connector = await getDataOrPopupError(`/connector/${props.connector}`)
  await updateOption(connector.connector_type)
  for (const group of optionsGroups.value) {
    for (const option of group.options) {
      doAssert(["text", "checkbox", "select"].includes(option.type), t.value.connectorEditor.internalErr)
      if (["name", "connector_type", "note", "autostart"].includes(option.id)) {
        optionValues[option.id] = connector[option.id]
      } else if (connector.connection[option.id] !== undefined && connector.connection[option.id] !== null) {
        optionValues[option.id] = connector.connection[option.id]
      }
    }
  }
}

function getCurrentConnector() {
  let connector = { connection: {} }
  if (!optionValues["connector_type"]) {
    return undefined;
  }
  for (const group of optionsGroups.value) {
    for (const option of group.options) {
      doAssert(["text", "checkbox", "select"].includes(option.type), t.value.connectorEditor.internalErr)
      if (optionValues[option.id] === undefined || optionValues[option.id] == null) {
        if (option.type !== "checkbox") {
          addPopup("red", `${t.value.connectorEditor.optionEmptyTitle}: ${option.name}`, `${option.name} ${t.value.connectorEditor.optionEmptyMsg}`)
          return undefined
        }
      }
      if (["name", "connector_type", "note", "autostart"].includes(option.id)) {
        connector[option.id] = optionValues[option.id]
      } else {
        connector.connection[option.id] = optionValues[option.id]
      }
    }
  }
  if (store.connector) {
    connector.connector_id = store.connector;
  } else {
    // 生成新的 UUID
    connector.connector_id = crypto.randomUUID();
  }
  return connector
}

async function saveConnector() {
  let connector = getCurrentConnector()
  if (!connector) return;
  let result = await postDataOrPopupError("/connector", connector)
  if (!result) {
    addPopup("red", t.value.connectorEditor.saveFailTitle, t.value.connectorEditor.saveFailMsg)
  } else {
    addPopup("green", t.value.connectorEditor.saveOkTitle, result.action === 'add' ? t.value.connectorEditor.saveOkMsgAdd : t.value.connectorEditor.saveOkMsgUpdate)
    setTimeout(() => {
      router.push("/connector")
    }, 1000);
  }
}

function onUpdateOption(optionId, value) {
  optionValues[optionId] = value
  // If connector_type changes, reload options
  if (optionId === "connector_type") {
    updateOption(value)
  }
}

const buttons = computed(() => [
  { id: "cancel", label: t.value.connectorEditor.cancel },
  { id: "save", label: t.value.connectorEditor.save },
])

function onButtonClick(button) {
  if (button.id === "cancel") {
    router.push("/connector")
  } else if (button.id === "save") {
    saveConnector()
  }
}

setTimeout(async () => {
  await fetchSupportedConnectorTypes();
  if (props.connector) {
    await fetchCurrentConnector()
  } else {
    // 设置默认连接器类型
    if (basicOptionGroup.options.find(opt => opt.id === 'connector_type').alternatives.length > 0) {
      const defaultType = basicOptionGroup.options.find(opt => opt.id === 'connector_type').alternatives[0].value
      optionValues.connector_type = defaultType
      await updateOption(defaultType)
    }
  }
}, 0)
</script>

<template>
  <GroupedForm :groups="optionsGroups" :modelValue="optionValues" @update:modelValue="onUpdateOption" :buttons="buttons"
    @button-click="onButtonClick" />
</template>
