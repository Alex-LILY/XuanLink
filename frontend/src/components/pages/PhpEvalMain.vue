<script setup>
import { ref, shallowRef, watch } from "vue";
import { Codemirror } from 'vue-codemirror'
import { php } from '@codemirror/lang-php'
import { oneDark } from '@codemirror/theme-one-dark'
import { noctisLilac } from "thememirror";
import { EditorView } from "@codemirror/view"

import { addPopup, getCurrentApiUrl, postDataOrPopupError } from "@/assets/utils";
import { t } from "@/i18n"
import { store } from "@/assets/store";
import { parseDataOrPopupError } from "@/assets/utils";
import axios from "axios";

const props = defineProps({
  session: String,
})

if (props.session) {
  store.session = props.session
}

// ##############
// --- Editor ---
// ##############

const phpPlain = ref(true)
const codeMirrorView = shallowRef()
const codeMirrorContent = ref("")
const codeMirrorTheme = EditorView.theme({
  "&": {
    "background-color": "var(--background-color-2)",
    "font-size": "1rem",
  },
}, { dark: true })

const lightThemes = ["pro", "paper"]
const codeMirrorExtensions = shallowRef([])

function updateCodeMirrorExtension() {
  codeMirrorExtensions.value = [
    codeMirrorTheme,
    (lightThemes.includes(store.theme) ? noctisLilac : oneDark),
    codeMirrorTheme,
    php({ plain: phpPlain.value })
  ]
}

function codeMirrorReady(payload) {
  codeMirrorView.value = payload.view
  updateCodeMirrorExtension()
}

watch(phpPlain, () => {
  updateCodeMirrorExtension()
})

watch(codeMirrorContent, (newValue, _) => {
  const isPlain = s => s.indexOf("<?") == -1 && s.indexOf("<html>") == -1
  if (isPlain(newValue) != phpPlain.value) {
    phpPlain.value = isPlain(newValue)
  }
})


// ###############
// --- Execute ---
// ###############

const codeOutput = ref("")

async function onCtrlEnter() {
  let content = codeMirrorContent.value
  // evil hack to implement ctrl+enter event
  // that ignore user input newline
  if (content[content.length - 1] == "\n") {
    codeMirrorContent.value = content.slice(0, content.length - 1)
  }
  await onExecute()
}

async function onExecute() {
  if (phpPlain.value) {
    await onPhpEval()
  } else {
    await onPhpInclude()
  }
}

async function onPhpEval() {
  if (!phpPlain.value) {
    addPopup("yellow", t.value.phpEval.warnHasTagTitle, t.value.phpEval.warnHasTagMsg)
  }
  const code = codeMirrorContent.value;
  const url = `${getCurrentApiUrl()}/session/${props.session}/php_eval`
  let resp
  try {
    resp = await axios.post(url, {
      code: code
    })
  } catch (e) {
    addPopup("red", t.value.phpEval.errNoConnTitle, t.value.phpEval.errNoConnMsg.replace('{session}', props.session))
    throw e
  }
  if (resp.data.code == -500 || resp.data.code == -400) {
    setTimeout(() => {
      addPopup("blue", t.value.phpEval.checkCodeTitle, t.value.phpEval.checkCodeMsg)
    }, 300)
  }
  const data = parseDataOrPopupError(resp)
  codeOutput.value = data
}

async function onPhpInclude() {
  if (phpPlain.value) {
    addPopup("yellow", t.value.phpEval.warnNoTagTitle, t.value.phpEval.warnNoTagMsg)
  }
  const url = `/session/${props.session}/php_eval`
  const rawCode = codeMirrorContent.value;
  const code = `
$temp_file = tempnam(sys_get_temp_dir(), "");
$content = base64_decode(${JSON.stringify(btoa(rawCode))});
file_put_contents($temp_file, $content);
include $temp_file;
@unlink($temp_file);
  `.trim()
  const data = await postDataOrPopupError(url, {
    code: code
  })
  codeOutput.value = data
}

</script>

<template>
  <div class="panels">
    <div class="left-panel">
      <div class="php-code shadow-box">
        <codemirror v-model="codeMirrorContent" placeholder="var_dump('exploit!');" :autofocus="true"
          :indent-with-tab="true" :tab-size="4" :extensions="codeMirrorExtensions" @ready="codeMirrorReady"
          @keydown.ctrl.enter="onCtrlEnter" />
      </div>
      <div class="actions shadow-box">
        <button class="button" :title="t.phpEval.btnAutoTitle" @click="onExecute">{{ t.phpEval.btnAuto }}</button>
        <button class="button" @click="onPhpEval">{{ t.phpEval.btnEval }}</button>
        <button class="button" @click="onPhpInclude">{{ t.phpEval.btnInclude }}</button>
      </div>
    </div>
    <div class="right-panel">
      <div class="php-output">
        <textarea name="php-output" id="php-output" class="shadow-box" readonly :value="codeOutput"></textarea>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panels {
  display: flex;
  width: 100%;
  height: 100%;
  justify-content: space-between;
  flex-grow: 1;
}

.left-panel {
  width: 48%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.actions {
  display: flex;
  justify-content: left;
  flex-wrap: wrap;
  width: 100%;
  min-height: 60px;
  margin-top: 16px;
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  box-shadow: var(--card-shadow);
  align-items: center;
  padding-left: 20px;
  padding-right: 20px;
  gap: 8px;
}



.actions button {
  min-height: 2.5rem;
  height: max-content;
}

.actions button:hover {
  background-color: var(--background-color-hover);
}

.php-code {
  flex-grow: 1;
  border-radius: var(--card-radius);
  padding-top: 1rem;
  padding-bottom: 1rem;
  background-color: var(--card-bg);
  border: var(--card-border);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  overflow: auto;
}

.right-panel {
  width: 50%;
  height: 100%;
}

.php-output {
  height: 100%;
}

.php-output textarea {
  width: 100%;
  height: 100%;
  background-color: var(--card-bg);
  color: var(--font-color-primary);
  border: var(--card-border);
  border-radius: var(--card-radius);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  font-size: var(--font-size-base);
  font-family: var(--font-mono);
  padding: 20px;
  outline: none;
  resize: none;
}

svg {
  width: 35px;
  stroke: var(--font-color-primary);
}
</style>
