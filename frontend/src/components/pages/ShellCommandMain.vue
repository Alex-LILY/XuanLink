<script setup>
import { getDataOrPopupError } from "@/assets/utils";
import IconRun from "@/components/icons/iconRun.vue"
import { ref } from "vue";
import { store } from "@/assets/store";


const props = defineProps({
  session: String,
})
const commandInput = ref("")
const commandInputReadonly = ref(false)
const commandOutput = ref("$")

if (props.session) {
  store.session = props.session
}

function addCommand(command) {
  commandOutput.value = `${commandOutput.value} ${command}\n`
  // change scroll position after text rendered.
  setTimeout(() => {
    let textarea = document.getElementById("command-output");
    textarea.scrollTop = textarea.scrollHeight;
  }, 0)
}

function addOutput(output) {
  commandOutput.value = `${commandOutput.value}${output}\n$`
  // change scroll position after text rendered.
  setTimeout(() => {
    let textarea = document.getElementById("command-output");
    textarea.scrollTop = textarea.scrollHeight;
  }, 0)
}

async function onExecuteCommand(event) {
  const cmd = commandInput.value;
  event.preventDefault()
  commandInput.value = ""
  commandInputReadonly.value = true
  try {
    addCommand(cmd)
    const result = await getDataOrPopupError(`/session/${props.session}/execute_cmd`, {
      params: {
        cmd: cmd
      }
    })
    addOutput(result)
  } catch (error) {
    throw error
  } finally {
    commandInputReadonly.value = false

  }

}

</script>

<template>
  <form action="" class="command-input" @submit="onExecuteCommand">
    <input id="command-input" type="text" placeholder="cat /etc/passwd" v-model="commandInput"
      :readonly="commandInputReadonly" class="shadow-box">
    <div class="icon-run shadow-box" @click="onExecuteCommand">
      <IconRun />
    </div>
  </form>
  <div class="command-output">
    <textarea name="command-output" id="command-output" class="shadow-box" readonly :value="commandOutput"></textarea>
  </div>
</template>

<style scoped>
.command-input {
  display: flex;
  height: 60px;
}

.command-input input {
  background-color: var(--card-bg);
  color: var(--font-color-primary);
  border: var(--card-border);
  border-radius: var(--card-radius);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  margin-right: 12px;
  outline: none;
  flex-grow: 1;
  font-size: var(--font-size-base);
  font-family: var(--font-mono);
  padding: 0 20px;
  height: 60px;
  width: 100px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.command-input input:focus {
  border-color: var(--input-focus-border-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--input-focus-border-color) 15%, transparent);
}

.icon-run {
  height: 60px;
  width: 60px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  backdrop-filter: var(--card-backdrop);
  -webkit-backdrop-filter: var(--card-backdrop);
  transition: background var(--transition-fast), border-color var(--transition-fast), transform var(--transition-fast);
  cursor: pointer;
}

.icon-run:hover {
  background: var(--button-bg);
  border-color: transparent;
  transform: scale(1.05);
}

.icon-run:hover svg {
  stroke: var(--button-color);
}

.icon-run:active {
  transform: scale(0.97);
}

.command-output {
  margin-top: 12px;
  height: 85%;
  flex-grow: 1;
}

.command-output textarea {
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
  line-height: 1.6;
  padding: 20px 24px;
  outline: none;
  resize: none;
}

svg {
  width: 35px;
  stroke: var(--font-color-primary);
}
</style>