<script setup>
import { store } from '@/assets/store';
import { getDataOrPopupError } from '@/assets/utils';
import { ref } from 'vue';
import Terminal, { TerminalApi } from 'vue-web-terminal';

const props = defineProps({
  session: String,
  pwd: String,
  modalMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(["close"])

if (props.session) {
  store.session = props.session
}

const pwd = ref("")

if(props.pwd) {
  pwd.value = props.pwd
}

function looksLikeWindows(path) {
  return /^[A-Za-z]:[\\/]/.test(path)
}

async function psudoExec(command) {
  if (pwd.value == "") {
    // Windows shell 没有 pwd，用 cd 取当前目录
    pwd.value = (await getDataOrPopupError(`/session/${props.session}/execute_cmd`, {
      params: {
        cmd: "pwd"
      }
    })).trim()
  }
  const isWin = looksLikeWindows(pwd.value)
  let cmd
  if (isWin) {
    // Windows cmd 不支持单引号和分号，使用 cd /d 和 &&
    const safePwd = pwd.value.replace(/"/g, '""')
    cmd = `cd /d "${safePwd}" && (${command}) 2>&1`
  } else {
    // TODO: correctly escape pwd.value
    cmd = `cd '${pwd.value}'; (${command}) 2>&1`
  }
  const result_text = await getDataOrPopupError(`/session/${props.session}/execute_cmd`, {
    params: {
      cmd: cmd
    }
  })
  return result_text
}

async function onExecCmd(key, command, success, failed) {

  // TODO: fix this regexp, it stop user cd to special directory
  if (key == "cd" && /^cd +[^;&\|]+$/.test(command)) {
    let result
    try {
      const dir = command.substring(2).trim()
      if (looksLikeWindows(pwd.value)) {
        result = await psudoExec(`cd /d "${dir.replace(/"/g, '""')}" && cd`)
      } else {
        result = await psudoExec(command + "; pwd")
      }
    } catch (error) {
      failed()
      return
    }
    // when `cd` success it produces no output
    if (!result.trim().includes("can't cd to") && !result.trim().includes("系統找不到")) {
      pwd.value = result.trim()
      success()
    } else {
      success({
        type: "ansi",
        content: result
      })
    }
  } else if (key == "clear") {
    TerminalApi.clearLog("my-terminal")
    success()
  } else {
    let result
    try {
      result = await psudoExec(command)
    } catch (error) {
      failed()
      return
    }
    success({
      type: 'ansi',
      content: result
    })
  }
}
</script>

<template>
  <div class="terminal-main">
    <terminal name="my-terminal" :context="pwd" :show-header="false" :log-size-limit="500"
      :enable-default-command="false" @exec-cmd="onExecCmd" />
  </div>
</template>

<style scoped>
.terminal-main {
  height: 100%;
  width: 100%;
  z-index: 0;
}
</style>
