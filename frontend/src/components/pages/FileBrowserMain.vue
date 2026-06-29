<script setup>
import IconRun from "@/components/icons/iconRun.vue"
import IconDirectory from "@/components/icons/iconDirectory.vue"
import IconFile from "@/components/icons/iconFile.vue"
import IconFileDownload from "@/components/icons/iconFileDownload.vue"
import IconFileNew from "@/components/icons/iconFileNew.vue"
import IconFileUpload from "@/components/icons/iconFileUpload.vue"
import IconFileUnknown from "@/components/icons/iconFileUnknown.vue"
import IconPenSquare from "@/components/icons/iconPenSquare.vue"
import IconLoad from "@/components/icons/iconLoad.vue"
import IconSymlinkFile from "@/components/icons/iconSymlinkFile.vue"
import IconSymlinkDirectory from "@/components/icons/iconSymlinkDirectory.vue"
import IconDelete from "@/components/icons/iconDelete.vue"
import IconChmod from "@/components/icons/iconChmod.vue"
import IconPlus from "@/components/icons/iconPlus.vue"
import IconCross from "@/components/icons/iconCross.vue"

import { ref, shallowRef, watch, computed } from "vue";
import ClickMenu from "@/components/ClickMenu.vue"
import HoverForm from "@/components/HoverForm.vue"
import HoverStatus from "@/components/HoverBox.vue"
import InputBox from "@/components/InputBox.vue"
import { Codemirror } from 'vue-codemirror'
import { getDataOrPopupError, postDataOrPopupError, addPopup, joinPath, ClickMenuManager, readableFileSize } from "@/assets/utils"
import { t } from "@/i18n"
import { store } from "@/assets/store"

// --- CodeMirror Stuff
import { EditorView } from "@codemirror/view"
import { oneDark } from '@codemirror/theme-one-dark'
import { noctisLilac } from 'thememirror';

import { css } from '@codemirror/lang-css'
import { cpp } from '@codemirror/lang-cpp'
import { html } from '@codemirror/lang-html'
import { java } from '@codemirror/lang-java'
import { javascript } from '@codemirror/lang-javascript'
import { markdown } from '@codemirror/lang-markdown'
import { php } from '@codemirror/lang-php'
import { python } from '@codemirror/lang-python'
import { xml } from '@codemirror/lang-xml'
import { yaml } from '@codemirror/lang-yaml'


import { shell } from "@codemirror/legacy-modes/mode/shell"
import { StreamLanguage } from "@codemirror/language"
import IconTerminal from "@/components/icons/iconTerminal.vue"
import IconLeft from "@/components/icons/iconLeft.vue"
import { useRouter } from "vue-router"

const props = defineProps({
  session: String,
  modalMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(["close", "open-terminal"])

if (props.session) {
  store.session = props.session
}

const router = useRouter()

// ###########
// --- PWD ---
// ###########

const userPwd = ref("")
let pwd = ref("")

setTimeout(async () => {
  pwd.value = await getDataOrPopupError(`/session/${props.session}/get_pwd`)
}, 0)

function onUserInputPwd(event) {
  event.preventDefault()
  pwd.value = userPwd.value
}

const breadcrumbs = computed(() => {
  let path = pwd.value || "/"
  if (path.includes("\\")) {
    let parts = path.split("\\").filter(p => p)
    if (parts.length === 0) {
      return [{ name: "\\", path: "\\" }]
    }
    let base = parts[0] + "\\"
    let crumbs = [{ name: parts[0], path: base }]
    let built = base
    for (let i = 1; i < parts.length; i++) {
      built = built + parts[i] + "\\"
      crumbs.push({ name: parts[i], path: built })
    }
    return crumbs
  }
  let parts = path.split("/").filter(p => p)
  if (parts.length === 0) {
    return [{ name: "/", path: "/" }]
  }
  let crumbs = []
  let built = ""
  for (let part of parts) {
    built = built + "/" + part
    crumbs.push({ name: part, path: built })
  }
  return crumbs
})

function jumpBreadcrumb(index) {
  pwd.value = breadcrumbs.value[index].path
}

// ####################
// --- Folder entry ---
// ####################

const entryIcons = {
  "dir": IconDirectory,
  "file": IconFile,
  "link-dir": IconSymlinkDirectory,
  "link-file": IconSymlinkFile,
  "unknown": IconFileUnknown
}

async function changeDir(entry) {
  let newPwd = await getDataOrPopupError("/utils/join_path", {
    params: {
      folder: pwd.value,
      entry: entry
    }
  })
  pwd.value = newPwd
}

async function listDir(newPwd) {
  let newEntries = await getDataOrPopupError(`/session/${props.session}/list_dir`, {
    params: {
      current_dir: newPwd
    }
  })
  entries.value = newEntries.map(entry => {
    return {
      name: entry.name,
      entryType: entry.entry_type,
      icon: entryIcons[entry.entry_type],
      permission: entry.permission,
      filesize: entry.filesize,
      mtime: entry.mtime || 0,
    }
  })
}


async function viewFile(newFilename) {
  let { text: fileContent, encoding: encoding } = await getDataOrPopupError(`/session/${props.session}/get_file_contents`, {
    params: {
      current_dir: pwd.value,
      filename: newFilename
    }
  })
  filename.value = newFilename
  userFilename.value = newFilename
  codeMirrorContent.value = fileContent
  fileEncoding.value = encoding
  showFileEditorModal.value = true
}


async function viewNewFile(newFilename) {
  filename.value = newFilename
  userFilename.value = newFilename
  codeMirrorContent.value = ""
  fileEncoding.value = "utf-8"
  showFileEditorModal.value = true
}

async function downloadFile(folder, filename) {

  let stopSignal = { signal: false }
  let downloadCoro = getDataOrPopupError(`/session/${props.session}/download_file`, {
    params: {
      folder: folder,
      filename: filename
    }
  })
  let checkDownloadsCoro = checkDownloadStatus(stopSignal)
  let content, _;
  try {
    [content, _] = await Promise.all([downloadCoro, checkDownloadsCoro])
  } catch (e) {
    stopSignal.signal = true;
    throw e
  }
  let url = `/utils/fetch_downloaded_file/${content.file_id}`;
  window.open(url, "_blank")

}

function openEntry(entry) {
  if (["dir", "link-dir"].includes(entry.entryType)) {
    changeDir(entry.name)
  } else if (["file", "link-file"].includes(entry.entryType)) {
    viewFile(entry.name)
  } else {
    addPopup("red", t.value.fileBrowser.unknownTypeTitle, t.value.fileBrowser.unknownTypeMsg.replace('{name}', entry.name))
  }
}

async function onDoubleClickEntry(event) {
  const element = event.currentTarget
  const entry = entries.value[element.dataset.entryIndex]
  openEntry(entry)
}

watch(pwd, async (newPwd, oldPwd) => {
  listDir(newPwd)
  userPwd.value = newPwd
})

const entries = shallowRef([

])

// ##############################
// --- File Transfer Hover Form ---
// ##############################

const uploadingFiles = ref([])
const downloadingFiles = ref([])

setTimeout(async () => {
  let result = await getDataOrPopupError(`/session/${props.session}/file_upload_status`)
  uploadingFiles.value = result
}, 0)

setTimeout(async () => {
  let result = await getDataOrPopupError(`/session/${props.session}/file_download_status`)
  downloadingFiles.value = result
}, 0)

function sleep(time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

const showUploadFileHoverForm = ref(false)

async function checkUploadStatus(stopSignal) {
  while (!stopSignal.signal) {
    await sleep(300)
    let result = await getDataOrPopupError(`/session/${props.session}/file_upload_status`)
    console.log(result)
    uploadingFiles.value = result
    if (result.length == 0) {
      return;
    }
  }
  let result = await getDataOrPopupError(`/session/${props.session}/file_upload_status`)
  uploadingFiles.value = result
}

async function checkDownloadStatus(stopSignal) {
  while (!stopSignal.signal) {
    await sleep(300)
    let result = await getDataOrPopupError(`/session/${props.session}/file_download_status`)
    console.log(result)
    downloadingFiles.value = result
    if (result.length == 0) {
      return;
    }
  }
  let result = await getDataOrPopupError(`/session/${props.session}/file_download_status`)
  downloadingFiles.value = result
}

async function submitUploadFile(form) {
  if (form == undefined) {
    return;
  }
  let stopSignal = { signal: false }
  let uploadFileCoro = postDataOrPopupError(`/session/${props.session}/upload_file`, form, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  let checkUploadsCoro = checkUploadStatus(stopSignal)
  let resp
  try {
    [resp, _] = await Promise.all([uploadFileCoro, checkUploadsCoro])
  } catch (e) {
    stopSignal.signal = true;
  }
  if (!resp) {
    addPopup("red", t.value.fileBrowser.uploadFailTitle, t.value.fileBrowser.uploadFailMsg)
  }
  await listDir(pwd.value)
}

// ###############################
// --- Folder entry click menu ---
// ###############################
let clickMenuEntry = undefined

function buildMenuItems() {
  return [
    { "name": "open_file", "text": t.value.fileBrowser.menuOpenFile, "icon": IconFile, "color": "white", "entry_type": ["file", "link-file"] },
    { "name": "new_file", "text": t.value.fileBrowser.menuNewFile, "icon": IconFileNew, "color": "white", "entry_type": ["empty", "file", "link-file"] },
    { "name": "duplicate_file", "text": t.value.fileBrowser.menuDuplicate, "icon": IconFile, "color": "white", "entry_type": ["file", "link-file"] },
    { "name": "upload_file", "text": t.value.fileBrowser.menuUpload, "icon": IconFileUpload, "color": "white", "entry_type": ["empty", "file", "link-file", "dir", "link-dir"] },
    { "name": "download_file", "text": t.value.fileBrowser.menuDownload, "icon": IconFileDownload, "color": "white", "entry_type": ["file", "link-file"] },
    { "name": "delete_file", "text": t.value.fileBrowser.menuDeleteFile, "icon": IconDelete, "color": "red", "entry_type": ["file", "link-file"] },
    { "name": "open_terminal_here", "text": t.value.fileBrowser.menuTerminal, "icon": IconTerminal, "color": "white", "entry_type": ["empty", "file", "link-file", "dir", "link-dir"] },
    { "name": "rename_file", "text": t.value.fileBrowser.menuRename, "icon": IconPenSquare, "color": "white", "entry_type": ["file", "link-file", "dir", "link-dir"] },
    { "name": "chmod_file", "text": t.value.fileBrowser.menuChmod, "icon": IconChmod, "color": "white", "entry_type": ["file", "link-file", "dir", "link-dir"] },
    { "name": "open_dir", "text": t.value.fileBrowser.menuOpenDir, "icon": IconDirectory, "color": "white", "entry_type": ["dir", "link-dir"] },
    { "name": "new_dir", "text": t.value.fileBrowser.menuNewDir, "icon": IconDirectory, "color": "white", "entry_type": ["empty", "file", "link-file", "dir", "link-dir"] },
    { "name": "delete_dir", "text": t.value.fileBrowser.menuDeleteDir, "icon": IconDelete, "color": "red", "entry_type": ["dir", "link-dir"] },
  ]
}
let menuItemsAll = buildMenuItems()
watch(t, () => { menuItemsAll = buildMenuItems() })
const ClickMenuFolderEntry = ClickMenuManager([

], (item) => {
  console.log(item)
  if (item.name == "open_file") {
    viewFile(clickMenuEntry.name)
    addPopup("blue", t.value.fileBrowser.openTipTitle, t.value.fileBrowser.openTipMsg)
  } else if (item.name == "open_dir") {
    changeDir(clickMenuEntry.name)
  } else if (item.name == "new_file") {
    confirmNewFile()
  } else if (item.name == "upload_file") {
    confirmUploadFile()
  } else if (item.name == "download_file") {
    downloadFile(pwd.value, clickMenuEntry.name)
  } else if (item.name == "rename_file") {
    confirmRenameFile(clickMenuEntry.name)
  } else if (item.name == "chmod_file") {
    openChmod(clickMenuEntry)
  } else if (item.name == "duplicate_file") {
    confirmDuplicateFile(clickMenuEntry.name)
  } else if (item.name == "delete_file") {
    confirmDeleteFile(clickMenuEntry.name)
  } else if (item.name == "delete_dir") {
    confirmDeleteDir(clickMenuEntry.name)
  } else if (item.name == "new_dir") {
    confirmNewDir()

  } else if (item.name == "open_terminal_here") {
    if (props.modalMode) {
      emit("open-terminal", pwd.value)
    } else {
      router.push({
        path: `/terminal/${props.session}`,
        query: {
          pwd: pwd.value
        }
      })
    }
  } else {
    addPopup("red", t.value.fileBrowser.internalErrTitle, t.value.fileBrowser.internalErrMsg.replace('{action}', item.name))
  }
})



function confirmNewFile() {
  showInputBox.value = true
  inputBoxTitle.value = t.value.fileBrowser.newFileTipTitle
  inputBoxNote.value = t.value.fileBrowser.newFileTipNote
  inputBoxRequireInput.value = true
  inputBoxCallback = async filename => {
    if (!filename) {
      showInputBox.value = false
      return
    }
    try {
      let success = await postDataOrPopupError(`/session/${props.session}/put_file_contents`, {
        text: "",
        encoding: "utf-8",
        filename: filename,
        current_dir: pwd.value
      })
      if (success) {
        addPopup("green", t.value.fileBrowser.newFileOkTitle, t.value.fileBrowser.newFileOkMsg.replace('{name}', filename))
      } else {
        addPopup("red", t.value.fileBrowser.newFileFailTitle, t.value.fileBrowser.newFileFailMsg.replace('{name}', filename))
      }
    } finally {
      showInputBox.value = false
    }

    await listDir(pwd.value)

    viewNewFile(filename)
  }
}

function confirmUploadFile() {
  showUploadFileHoverForm.value = true
}

function confirmRenameFile(filename) {
  showInputBox.value = true
  inputBoxTitle.value = t.value.fileBrowser.renameTipTitle
  inputBoxNote.value = t.value.fileBrowser.renameTipNote
  inputBoxRequireInput.value = true
  inputBoxCallback = async new_filename => {
    try {
      if (new_filename) {
        let result = await getDataOrPopupError(`/session/${props.session}/move_file`, {
          params: {
            filepath: (await joinPath(pwd.value, filename)),
            new_filepath: (await joinPath(pwd.value, new_filename))
          }
        })
        if (result) {
          addPopup("green", t.value.fileBrowser.renameOkTitle, t.value.fileBrowser.renameOkMsg.replace('{name}', filename))
        } else {
          addPopup("red", t.value.fileBrowser.renameFailTitle, t.value.fileBrowser.renameFailMsg.replace('{name}', filename))
        }
        await listDir(pwd.value)
      }
    } finally {
      showInputBox.value = false
    }
  }
}

function confirmDuplicateFile(filename) {
  showInputBox.value = true
  inputBoxTitle.value = t.value.fileBrowser.duplicateTipTitle
  inputBoxNote.value = t.value.fileBrowser.duplicateTipNote
  inputBoxRequireInput.value = true
  inputBoxCallback = async new_filename => {
    try {
      if (new_filename) {
        let result = await getDataOrPopupError(`/session/${props.session}/copy_file`, {
          params: {
            filepath: (await joinPath(pwd.value, filename)),
            new_filepath: (await joinPath(pwd.value, new_filename))
          }
        })
        if (result) {
          addPopup("green", t.value.fileBrowser.duplicateOkTitle, t.value.fileBrowser.duplicateOkMsg.replace('{name}', filename))
        } else {
          addPopup("red", t.value.fileBrowser.duplicateFailTitle, t.value.fileBrowser.duplicateFailMsg.replace('{name}', filename))
        }
        await listDir(pwd.value)
      }
    } finally {
      showInputBox.value = false
    }
  }
}


function confirmDeleteFile(filename) {
  showInputBox.value = true
  inputBoxTitle.value = t.value.fileBrowser.deleteFileTipTitle
  inputBoxNote.value = t.value.fileBrowser.deleteFileTipNote.replace('{name}', filename)
  inputBoxRequireInput.value = false
  inputBoxCallback = async result => {
    try {
      if (result) {
        let result = await getDataOrPopupError(`/session/${props.session}/delete_file`, {
          params: {
            current_dir: pwd.value,
            filename: filename
          }
        })
        if (result) {
          addPopup("green", t.value.fileBrowser.deleteFileOkTitle, t.value.fileBrowser.deleteFileOkMsg.replace('{name}', filename))
        } else {
          addPopup("red", t.value.fileBrowser.deleteFileFailTitle, t.value.fileBrowser.deleteFileFailMsg.replace('{name}', filename))
        }
        await listDir(pwd.value)
      }
    } finally {
      showInputBox.value = false
    }
  }
}


function confirmDeleteDir(filename) {
  showInputBox.value = true
  inputBoxTitle.value = t.value.fileBrowser.deleteDirTipTitle
  inputBoxNote.value = t.value.fileBrowser.deleteDirTipNote.replace('{name}', filename)
  inputBoxRequireInput.value = false
  inputBoxCallback = async result => {
    try {
      if (result) {
        let result = await getDataOrPopupError(`/session/${props.session}/delete_file`, {
          params: {
            current_dir: pwd.value,
            filename: filename
          }
        })
        if (result) {
          addPopup("green", t.value.fileBrowser.deleteDirOkTitle, t.value.fileBrowser.deleteDirOkMsg.replace('{name}', filename))
        } else {
          addPopup("red", t.value.fileBrowser.deleteDirFailTitle, t.value.fileBrowser.deleteDirFailMsg.replace('{name}', filename))
        }
        await listDir(pwd.value)
      }
    } finally {
      showInputBox.value = false
    }
  }
}

function confirmNewDir() {
  showInputBox.value = true
  inputBoxTitle.value = t.value.fileBrowser.newDirTipTitle
  inputBoxNote.value = t.value.fileBrowser.newDirTipNote
  inputBoxRequireInput.value = true
  inputBoxCallback = async dirname => {
    if (!dirname) {
      showInputBox.value = false
      return
    }
    try {
      let dirpath = await getDataOrPopupError("/utils/join_path", {
        params: {
          folder: pwd.value,
          entry: dirname
        }
      })
      let success = await getDataOrPopupError(`/session/${props.session}/mkdir`, {
        params: {
          dirpath: dirpath
        }
      })
      if (success) {
        addPopup("green", t.value.fileBrowser.newDirOkTitle, t.value.fileBrowser.newDirOkMsg.replace('{name}', dirname))
      } else {
        addPopup("red", t.value.fileBrowser.newDirFailTitle, t.value.fileBrowser.newDirFailMsg.replace('{name}', dirname))
      }
    } finally {
      showInputBox.value = false
    }
    await listDir(pwd.value)
  }
}

function onRightClickEntry(event) {
  const element = event.currentTarget
  const entry = entries.value[element.dataset.entryIndex]
  ClickMenuFolderEntry.items.value = menuItemsAll.filter(item => item.entry_type.includes(entry.entryType))
  clickMenuEntry = entry
  ClickMenuFolderEntry.onshow(event)
}

function onRightClickEmpty(event) {
  ClickMenuFolderEntry.items.value = menuItemsAll.filter(item => item.entry_type.includes("empty"))
  clickMenuEntry = undefined
  ClickMenuFolderEntry.onshow(event)
}


// ##################################
// --- File editor and CodeMirror ---
// ##################################

const userFilename = ref("")
let filename = ref("")
let fileEncoding = ref("")
const showFileEditorModal = ref(false)

const fileExtension = ref("")

const codeMirrorView = shallowRef()
const codeMirrorContent = ref("")
const codeMirrorTheme = EditorView.theme({
  "&": {
    "background-color": "var(--background-color-2)",
    "font-size": "1rem",
  },
  ".cm-gutters *": {
    "background-color": "var(--background-color-3)",

  }
}, { dark: true })

const lightThemes = ["pro", "paper"]
const codeMirrorExtensions = shallowRef([codeMirrorTheme, (lightThemes.includes(store.theme) ? noctisLilac : oneDark)])

function codeMirrorReady(payload) {
  codeMirrorView.value = payload.view
}

watch(fileExtension, (newFileExtension, _) => {
  let extensions = [codeMirrorTheme, (lightThemes.includes(store.theme) ? noctisLilac : oneDark)];
  let highlightings = [
    { suffix: ["cpp"], extension: () => cpp() },
    { suffix: ["css"], extension: () => css() },
    { suffix: ["html", "htm", "xhtml"], extension: () => html() },
    { suffix: ["java"], extension: () => java() },
    { suffix: ["js", "mjs"], extension: () => javascript() },
    { suffix: ["md"], extension: () => markdown() },
    { suffix: ["sh"], extension: () => StreamLanguage.define(shell) },
    { suffix: ["php", "php7", "php5", "phar"], extension: () => php() },
    { suffix: ["py"], extension: () => python() },
    { suffix: ["xml"], extension: () => xml() },
    { suffix: ["yaml"], extension: () => yaml() },
  ]
  let selectedHighlights = highlightings.filter(item => item.suffix.includes(newFileExtension))
  if (selectedHighlights.length) {
    extensions.push(selectedHighlights[0].extension())
  } else {
    console.log("Extension not supported", newFileExtension)
  }
  codeMirrorExtensions.value = extensions
})
watch(filename, (newFilename, _) => {
  if (newFilename.indexOf(".") == "") {
    return ""
  }
  let dotPosition = newFilename.lastIndexOf(".") + 1
  fileExtension.value = newFilename.substring(dotPosition)
})

async function saveFile() {
  filename.value = userFilename.value
  try {
    let success = await postDataOrPopupError(`/session/${props.session}/put_file_contents`, {
      text: codeMirrorContent.value,
      encoding: fileEncoding.value,
      filename: filename.value,
      current_dir: pwd.value
    })
    if (success) {
      addPopup("green", t.value.fileBrowser.saveOkTitle, t.value.fileBrowser.saveOkMsg.replace('{name}', filename.value))
    } else {
      addPopup("red", t.value.fileBrowser.saveFailTitle, t.value.fileBrowser.saveFailMsg.replace('{name}', filename.value))
    }
  } finally {
    await listDir(pwd.value)
  }
}

async function saveFileAndClose() {
  await saveFile()
  showFileEditorModal.value = false
}

// input box 

const showInputBox = ref(false)
const inputBoxTitle = ref("")
const inputBoxNote = ref("")
const inputBoxRequireInput = ref(false)
let inputBoxCallback = ref(undefined)

// #################
// --- Chmod modal ---
// #################

const showChmodModal = ref(false)
const chmodTarget = ref("")
const chmodTargetPath = ref("")
const chmodMode = ref("755")
const chmodPerms = ref({
  owner: { r: false, w: false, x: false },
  group: { r: false, w: false, x: false },
  other: { r: false, w: false, x: false },
})

watch(chmodPerms, (newVal) => {
  let o = (newVal.owner.r ? 4 : 0) + (newVal.owner.w ? 2 : 0) + (newVal.owner.x ? 1 : 0)
  let g = (newVal.group.r ? 4 : 0) + (newVal.group.w ? 2 : 0) + (newVal.group.x ? 1 : 0)
  let ot = (newVal.other.r ? 4 : 0) + (newVal.other.w ? 2 : 0) + (newVal.other.x ? 1 : 0)
  chmodMode.value = `${o}${g}${ot}`
}, { deep: true })

async function openChmod(entry) {
  chmodTarget.value = entry.name
  let path = await joinPath(pwd.value, entry.name)
  chmodTargetPath.value = path
  let p = String(entry.permission).padStart(3, "0").slice(-3)
  let bits = p.split("").map(Number)
  chmodPerms.value = {
    owner: { r: !!(bits[0] & 4), w: !!(bits[0] & 2), x: !!(bits[0] & 1) },
    group: { r: !!(bits[1] & 4), w: !!(bits[1] & 2), x: !!(bits[1] & 1) },
    other: { r: !!(bits[2] & 4), w: !!(bits[2] & 2), x: !!(bits[2] & 1) },
  }
  showChmodModal.value = true
}

function closeChmod() {
  showChmodModal.value = false
}

async function applyChmod() {
  let mode = chmodMode.value
  if (!/^[0-7]{3,4}$/.test(mode)) {
    addPopup("red", t.value.fileBrowser.chmodFormatErrTitle, t.value.fileBrowser.chmodFormatErrMsg)
    return
  }
  try {
    await getDataOrPopupError(`/session/${props.session}/chmod`, {
      params: {
        filepath: chmodTargetPath.value,
        mode: mode,
      }
    })
    addPopup("green", t.value.fileBrowser.chmodOkTitle, t.value.fileBrowser.chmodOkMsg.replace('{name}', chmodTarget.value).replace('{mode}', mode))
    showChmodModal.value = false
  } finally {
    await listDir(pwd.value)
  }
}

// #################
// --- Utilities ---
// #################


function readableFileMtime(mtime) {
  if (!mtime) return '—'
  const d = new Date(mtime * 1000)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function readableFilePerm(filePerm) {
  let result = ""
  for (let chr of filePerm) {
    let x = Number(chr)
    for (let [permIndex, permChr] of Array.from("rwx").entries()) {
      if (x & Math.pow(2, 2 - permIndex)) {
        result += permChr
      } else {
        result += "-"
      }
    }
  }
  return result
}


</script>

<template>
  <div class="file-panel">
    <div class="folder-control">
      <div class="folder-toolbar">
        <button class="tool-btn secondary" @click="changeDir('..')">
          <IconLeft /> {{ t.fileBrowser.btnUp }}
        </button>
        <button class="tool-btn secondary" @click="listDir(pwd)">
          <IconLoad /> {{ t.fileBrowser.btnRefresh }}
        </button>
        <button class="tool-btn secondary" @click="confirmNewDir">
          <IconPlus /> {{ t.fileBrowser.btnNewDir }}
        </button>
        <button class="tool-btn secondary" @click="confirmNewFile">
          <IconFileNew /> {{ t.fileBrowser.btnNewFile }}
        </button>
        <button class="tool-btn primary" @click="showUploadFileHoverForm = true">
          <IconFileUpload /> {{ t.fileBrowser.btnUpload }}
        </button>
      </div>

      <form action="" class="filepath-input" @submit="onUserInputPwd">
        <input v-model="userPwd" id="filepath-input" class="shadow-box" type="text" placeholder="/var/www/html">
        <div class="filepath-icon shadow-box" @click="onUserInputPwd">
          <IconRun />
        </div>
        <div class="filepath-icon shadow-box" @click="() => {
          listDir(pwd);
          userPwd = pwd;
        }">
          <IconLoad />
        </div>
      </form>
      <div class="breadcrumb-bar">
        <span
          v-for="(crumb, index) in breadcrumbs"
          :key="index"
          class="breadcrumb-item"
          @click="jumpBreadcrumb(index)"
        >{{ crumb.name }}</span>
      </div>
      <div class="file-list-panel scrollbar shadow-box" @click.right.stop="onRightClickEmpty">
        <div class="file-list-header">
          <div class="col-name">{{ t.fileBrowser.colName }}</div>
          <div class="col-mtime">{{ t.fileBrowser.colMtime }}</div>
          <div class="col-size">{{ t.fileBrowser.colSize }}</div>
          <div class="col-perm">{{ t.fileBrowser.colPerm }}</div>
          <div class="col-actions">{{ t.fileBrowser.colOps }}</div>
        </div>
        <div v-if="entries.length === 0" class="empty-dir">
          <p>{{ t.fileBrowser.emptyDir }}</p>
        </div>
        <div class="file-item" v-for="[entryIndex, entry] in entries.entries()" :key="entryIndex"
          @dblclick="onDoubleClickEntry" @click.right.stop="onRightClickEntry" :data-entry-index="entryIndex"
          :class="{ dir: ['dir', 'link-dir'].includes(entry.entryType) }">
          <div class="col-name">
            <component :is="entry.icon" class="entry-icon"></component>
            <a href="#" @click.prevent="openEntry(entry)" class="entry-name-link" :title="entry.name">{{ entry.name }}</a>
          </div>
          <div class="col-mtime">{{ readableFileMtime(entry.mtime) }}</div>
          <div class="col-size">{{ ['dir', 'link-dir'].includes(entry.entryType) ? '—' : readableFileSize(entry.filesize) }}</div>
          <div class="col-perm">{{ readableFilePerm(entry.permission) }}</div>
          <div class="col-actions entry-actions">
            <button class="action-btn action-open" @click.stop="openEntry(entry)">{{ t.fileBrowser.actOpen }}</button>
            <button v-if="['file', 'link-file'].includes(entry.entryType)" class="action-btn action-edit" @click.stop="viewFile(entry.name)">{{ t.fileBrowser.actEdit }}</button>
            <button v-if="['file', 'link-file'].includes(entry.entryType)" class="action-btn action-download" @click.stop="downloadFile(pwd, entry.name)">{{ t.fileBrowser.actDownload }}</button>
            <button class="action-btn action-rename" @click.stop="confirmRenameFile(entry.name)">{{ t.fileBrowser.actRename }}</button>
            <button class="action-btn action-delete" @click.stop="entry.entryType === 'dir' || entry.entryType === 'link-dir' ? confirmDeleteDir(entry.name) : confirmDeleteFile(entry.name)">{{ t.fileBrowser.actDelete }}</button>
            <button class="action-btn action-chmod" @click.stop="openChmod(entry)">{{ t.fileBrowser.actChmod }}</button>
          </div>
        </div>
      </div>
    </div>

  </div>

  <Teleport to="body">
    <transition>
      <div v-if="showFileEditorModal" class="file-editor-modal-overlay" @click.self="showFileEditorModal = false">
        <div class="file-editor-modal" @click.stop>
          <div class="file-editor-modal-header">
            <h3>{{ filename ? `${t.fileBrowser.editTitle} - ${filename}` : t.fileBrowser.newFileTitle }}</h3>
            <button class="file-editor-modal-close" @click="showFileEditorModal = false" :title="t.fileBrowser.closeTip">
              <IconCross />
            </button>
          </div>
          <div class="file-editor-modal-body">
            <div class="file-editor-control">
              <input type="text" name="filename" :placeholder="t.fileBrowser.filenamePh" v-model="userFilename">
              <input type="text" name="encoding" :placeholder="t.fileBrowser.encodingPh" v-model="fileEncoding">
              <button class="file-editor-save-btn" @click="saveFileAndClose">{{ t.fileBrowser.save }}</button>
            </div>
            <div class="file-editor-content scrollbar">
              <codemirror v-model="codeMirrorContent" placeholder="Content goes here..." :autofocus="true"
                :indent-with-tab="true" :tab-size="4" :extensions="codeMirrorExtensions" @ready="codeMirrorReady" />
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
  <transition>
    <div v-if="ClickMenuFolderEntry.show.value">
      <ClickMenu :mouse_x="ClickMenuFolderEntry.x" :mouse_y="ClickMenuFolderEntry.y"
        :menuItems="ClickMenuFolderEntry.items.value" @remove="ClickMenuFolderEntry.onremove"
        @clickItem="ClickMenuFolderEntry.onclick" />
    </div>
  </transition>

  <transition>
    <InputBox v-if="showInputBox" :title="inputBoxTitle" :note="inputBoxNote" :requireInput="inputBoxRequireInput"
      @result="inputBoxCallback" />
  </transition>

  <transition>
    <HoverForm :title="t.fileBrowser.uploadTitle" :callback="(result) => { submitUploadFile(result); showUploadFileHoverForm = false }"
      v-if="showUploadFileHoverForm">
      <input type="hidden" name="folder" :value="pwd">
      <div class="hover-form-line">
        <div class="input-file">
          <input type="file" name="file" id="file">
        </div>
      </div>
    </HoverForm>
  </transition>

  <Teleport to="body">
    <transition>
      <div v-if="showChmodModal" class="chmod-modal" @click.self="closeChmod">
        <div class="chmod-box">
          <h3>{{ t.fileBrowser.chmodTitle }}</h3>
          <p class="chmod-target">{{ chmodTarget }}</p>
          <div class="perm-grid">
            <div class="perm-col">
              <h4>{{ t.fileBrowser.chmodOwner }}</h4>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.owner.r"> {{ t.fileBrowser.chmodRead }}</label>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.owner.w"> {{ t.fileBrowser.chmodWrite }}</label>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.owner.x"> {{ t.fileBrowser.chmodExec }}</label>
            </div>
            <div class="perm-col">
              <h4>{{ t.fileBrowser.chmodGroup }}</h4>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.group.r"> {{ t.fileBrowser.chmodRead }}</label>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.group.w"> {{ t.fileBrowser.chmodWrite }}</label>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.group.x"> {{ t.fileBrowser.chmodExec }}</label>
            </div>
            <div class="perm-col">
              <h4>{{ t.fileBrowser.chmodOther }}</h4>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.other.r"> {{ t.fileBrowser.chmodRead }}</label>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.other.w"> {{ t.fileBrowser.chmodWrite }}</label>
              <label class="perm-check"><input type="checkbox" v-model="chmodPerms.other.x"> {{ t.fileBrowser.chmodExec }}</label>
            </div>
          </div>
          <div class="chmod-octal">0{{ chmodMode }}</div>
          <div class="chmod-actions">
            <button class="tool-btn secondary" @click="closeChmod">{{ t.fileBrowser.chmodCancel }}</button>
            <button class="tool-btn primary" @click="applyChmod">{{ t.fileBrowser.chmodApply }}</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>

  <transition>
    <HoverStatus v-if="uploadingFiles.length + downloadingFiles.length != 0">
      <div class="file-transfer">
        <h1 v-if="uploadingFiles.length != 0">{{ t.fileBrowser.uploadProgress }}</h1>
        <div class="file-transfer-file" v-for="file in uploadingFiles">
          <div class="file-transfer-percentage">
            <p>
              {{ Math.floor(file.percentage * 100) }}%
            </p>
          </div>
          <div class="file-transfer-fileinfo">
            <p class="file-transfer-filename">
              {{ file.file }}
            </p>
            <p class="file-transfer-meta">
              {{ readableFileSize(file.done_bytes) }}
              / {{ readableFileSize(file.max_bytes) }}
              at {{ file.folder }}
            </p>
          </div>

        </div>
        <h1 v-if="downloadingFiles.length != 0">{{ t.fileBrowser.downloadProgress }}</h1>
        <div class="file-transfer-file" v-for="file in downloadingFiles">
          <div class="file-transfer-percentage">
            <p>
              {{ Math.floor(file.percentage * 100) }}%
            </p>
          </div>
          <div class="file-transfer-fileinfo">
            <p class="file-transfer-filename">
              {{ file.file }}
            </p>
            <p class="file-transfer-meta">
              {{ readableFileSize(file.done_bytes) }}
              / {{ readableFileSize(file.max_bytes) }}
              at {{ file.folder }}
            </p>
          </div>

        </div>
      </div>
    </HoverStatus>
  </transition>

</template>

<style scoped>
.filepath-input {
  display: flex;
  height: 2.8rem;
}

input[type="text"] {
  font-size: 1.3rem;
  text-indent: 10px;
  color: var(--font-color-primary);
  border: none;
  outline: none;
  border-radius: 1rem;
}

.filepath-input input {
  background-color: var(--background-color-2);
  flex-grow: 1;
  min-width: 50px;
}

.filepath-icon {
  flex-grow: 0;
  flex-shrink: 0;
  width: 2.8rem;
  margin-left: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--background-color-2);
  border-radius: 1rem;
  transition: all 0.3s ease;
  opacity: 1;
}

.filepath-icon:hover {
  background-color: var(--background-color-3);
  outline: 2px solid var(--font-color-secondary);
}

.filepath-icon svg {
  width: 1.8rem;
}

.file-panel {
  display: flex;
  height: 100%;
  flex-grow: 1;
  justify-content: space-between;
  padding: 16px;
  gap: 16px;
  flex-wrap: wrap;
  box-sizing: border-box;
}

.folder-control {
  flex: 1 1 100%;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}


.folder-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: var(--control-height);
  padding: 0 14px;
  border-radius: var(--button-radius);
  border: var(--button-border);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
}

.tool-btn svg {
  width: 16px;
  height: 16px;
  stroke: currentColor;
}

.tool-btn.primary {
  background-color: var(--button-bg);
  color: var(--button-color);
  border-color: var(--button-bg);
  box-shadow: var(--shadow-button);
}

.tool-btn.primary:hover {
  background-color: var(--button-hover-bg);
  border-color: var(--button-hover-bg);
}

.tool-btn.secondary {
  background-color: var(--button-secondary-bg);
  color: var(--button-secondary-color);
  border-color: var(--button-secondary-bg);
}

.tool-btn.secondary:hover {
  background-color: var(--button-secondary-hover-bg);
}

.breadcrumb-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  padding: 4px 6px;
  font-size: 0.82rem;
  color: var(--font-color-secondary);
  min-height: 1.8rem;
}

.breadcrumb-item {
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--font-color-secondary);
  transition: background-color 0.15s, color 0.15s;
}

.breadcrumb-item:hover {
  background-color: var(--hover-bg);
  color: var(--accent-color);
}

.breadcrumb-item:not(:last-child)::after {
  content: "/";
  margin-left: 4px;
  color: var(--font-color-muted);
  pointer-events: none;
}

.breadcrumb-item:last-child {
  color: var(--font-color-primary);
  font-weight: var(--font-weight-medium);
  cursor: default;
}

.breadcrumb-item:last-child:hover {
  background-color: transparent;
  color: var(--font-color-primary);
}

.file-list-panel {
  flex: 1 1 auto;
  margin-top: 12px;
  min-height: 0;
  height: 0;
  border-radius: 1rem;
  background-color: var(--background-color-2);
  overflow-y: auto;
  transition: background 1s ease;
  display: flex;
  flex-direction: column;
}

.file-list-header,
.file-item {
  display: grid;
  grid-template-columns: 1fr 130px 110px 90px auto;
  gap: 8px;
  padding: 10px 16px;
  align-items: center;
  font-size: 0.85rem;
}

.col-mtime {
  color: var(--font-color-secondary);
  font-size: 0.8rem;
  font-family: var(--font-mono);
  white-space: nowrap;
}

.file-list-header {
  background-color: var(--background-color-3);
  color: var(--font-color-muted);
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 2;
}

.file-item {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s ease;
  user-select: none;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item:hover {
  background-color: var(--hover-bg);
}

.file-item.dir {
  background-color: var(--folder-row-bg);
}

.file-item.dir:hover {
  background-color: var(--folder-row-hover-bg);
}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.entry-icon {
  width: 1.2rem;
  height: 1.2rem;
  flex-shrink: 0;
}

.entry-name-link {
  color: var(--font-color-primary);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-name-link:hover {
  color: var(--accent-color);
  text-decoration: underline;
}

.col-size,
.col-perm {
  color: var(--font-color-secondary);
  font-size: 0.8rem;
}

.col-perm {
  font-family: var(--font-mono);
}

.entry-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border: none;
  border-radius: 5px;
  font-size: 0.75rem;
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}

.action-btn:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

.action-open {
  background-color: #e0e7ff;
  color: #3730a3;
}

.action-edit {
  background-color: #ede9fe;
  color: #5b21b6;
}

.action-download {
  background-color: #dcfce7;
  color: #15803d;
}

.action-rename {
  background-color: #fef9c3;
  color: #713f12;
}

.action-delete {
  background-color: #fee2e2;
  color: #991b1b;
}

.action-chmod {
  background-color: #e0f2fe;
  color: #0369a1;
}

.empty-dir {
  text-align: center;
  padding: 40px;
  color: var(--font-color-muted);
}

.file-editor-modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
  backdrop-filter: blur(2px);
}

.file-editor-modal {
  background-color: var(--background-color-1);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  width: min(900px, 95vw);
  height: min(700px, 90vh);
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.file-editor-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--background-color-2);
}

.file-editor-modal-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: var(--font-weight-semibold);
  color: var(--font-color-primary);
}

.file-editor-modal-close {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--font-color-secondary);
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
}

.file-editor-modal-close:hover {
  background-color: var(--hover-bg);
  color: var(--font-color-primary);
}

.file-editor-modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.file-editor-control {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.file-editor-control input {
  flex: 1 1 160px;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background-color: var(--background-color-3);
  color: var(--font-color-primary);
  font-size: var(--font-size-base);
  outline: none;
}

.file-editor-control input:focus {
  border-color: var(--accent-color);
}

.file-editor-save-btn {
  height: 34px;
  padding: 0 18px;
  border: none;
  border-radius: 6px;
  background-color: var(--button-bg);
  color: var(--button-color);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background-color 0.15s;
}

.file-editor-save-btn:hover {
  background-color: var(--button-hover-bg);
}

.file-editor-content {
  flex: 1 1 auto;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--background-color-2);
  border: 1px solid var(--border-color);
}

.file-editor-content :deep(.cm-editor) {
  height: 100%;
}

.file-transfer {
  padding: 20px;
  color: var(--font-color-primary);
}

.file-transfer p {
  margin: 0;
}

.file-transfer-file {
  background-color: #00000015;
  height: 100px;
  border-radius: 1rem;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 20px;
}

.file-transfer-fileinfo {
  display: flex;
  flex-direction: column;
  align-items: left;
}

.file-transfer-filename {
  font-size: 28px;
}

.file-transfer-meta {
  color: var(--font-color-secondary);
}

.file-transfer-percentage {
  margin-right: 20px;
  font-size: 36px;
  width: 130px;
  background-color: #00000015;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 70px;
  border-radius: 1rem;
}

.chmod-modal {
  position: fixed;
  inset: 0;
  background-color: var(--modal-overlay-bg);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: var(--card-backdrop);
}

.chmod-box {
  background-color: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--modal-radius);
  box-shadow: var(--shadow-float);
  padding: 28px;
  min-width: 320px;
  width: 26rem;
  color: var(--font-color-secondary);
}

.chmod-box h3 {
  margin: 0 0 8px 0;
  color: var(--font-color-primary);
  font-size: 1.1rem;
}

.chmod-target {
  font-size: 0.85rem;
  color: var(--font-color-muted);
  margin-bottom: 16px;
  word-break: break-all;
}

.perm-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.perm-col {
  background-color: var(--background-color-2);
  border-radius: 0.75rem;
  padding: 12px;
}

.perm-col h4 {
  font-size: 0.75rem;
  color: var(--font-color-muted);
  margin: 0 0 8px 0;
  text-align: center;
}

.perm-check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  margin: 4px 0;
  color: var(--font-color-primary);
  cursor: pointer;
}

.chmod-octal {
  text-align: center;
  font-size: 1.6rem;
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);
  color: var(--accent-color);
  background-color: var(--background-color-2);
  padding: 10px;
  border-radius: 0.75rem;
  margin-bottom: 16px;
}

.chmod-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

svg {
  stroke: var(--font-color-primary);
}
</style>
