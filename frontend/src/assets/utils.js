import axios from "axios"
import { popupsRef, currentSettings } from "./store"
import { ref, shallowRef } from "vue"
import { t } from "@/i18n"

// Always send cookies for same-origin requests
axios.defaults.withCredentials = true
// Mark all axios requests so the backend can distinguish XHR from browser navigation
axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest'

// Inject stored token as Bearer header (fallback for dev mode / cross-origin)
axios.interceptors.request.use(config => {
  const token = localStorage.getItem("ghost_auth_token")
  if (token) {
    config.headers = config.headers || {}
    config.headers["Authorization"] = `Bearer ${token}`
  }
  return config
})

// On 401, clear stored token and redirect to login page
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem("ghost_auth_token")
      window.location.href = "/login.html"
    }
    return Promise.reject(error)
  }
)

class UserError extends Error {
  constructor(message) {
    super(message);
    this.name = "UserError"
    this.message = t.value.errors.clientErrorDetail.replace('{message}', message)
  }
}

class ServerError extends Error {
  constructor(message) {
    super(message);
    this.name = "ServerError"
    this.message = t.value.errors.serverErrorDetail.replace('{message}', message)
  }
}

class TargetError extends Error {
  constructor(message) {
    super(message);
    this.name = "TargetError";
    this.message = t.value.errors.targetErrorDetail.replace('{message}', message)
  }
}

export async function joinPath(folder, entry) {
  return await getDataOrPopupError("/utils/join_path", {
    params: {
      folder: folder,
      entry: entry
    }
  })
}

export function getCurrentApiUrl() {
  return window.location.origin.includes("5173") ? `http://${window.location.hostname}:8022` : window.location.origin
}

export function doAssert(result, msg) {
  if (result) {
    return
  }
  if (msg) {
    throw Error(msg)
  } else {
    throw Error("Assertion failed, message is not provided")
  }
}

export function addPopup(color, title, msg) {
  popupsRef.value.addPopup(color, title, msg)
}

export function parseDataOrPopupError(resp) {
  if (resp.data.code != 0) {
    let title = t.value.errors.unknownError + `: ${resp.data.code}`
    let errorClass
    if (resp.data.code == -400) {
      title = t.value.errors.clientError
      errorClass = UserError
    } else if (resp.data.code == -500) {
      title = t.value.errors.serverError
      errorClass = ServerError
    } else if (resp.data.code == -600) {
      title = t.value.errors.targetError
      errorClass = TargetError
    } else {
      title = t.value.errors.error
      errorClass = Error
    }
    addPopup("red", title, resp.data.msg)
    throw new errorClass(resp.data.msg)
  }
  return resp.data.data
}


function handleRequestError(e, uri) {
  if (e.response) {
    let data = e.response.data
    if (data && typeof data === "object" && "code" in data) {
      return parseDataOrPopupError(e.response)
    }
    addPopup("red", t.value.errors.serverError, t.value.errors.cannotRequestUriHttp.replace('{uri}', uri).replace('{status}', e.response.status))
  } else if (e.request) {
    addPopup("red", t.value.errors.requestServerFailed, t.value.errors.cannotRequestUriRunning.replace('{uri}', uri))
  } else {
    addPopup("red", t.value.errors.requestFailed, e.message)
  }
  throw e
}

export async function getDataOrPopupError(uri, config) {
  let url = `${getCurrentApiUrl()}${uri}`
  let resp
  try {
    resp = await axios.get(url, config)
  } catch (e) {
    return handleRequestError(e, uri)
  }
  return parseDataOrPopupError(resp)
}

export async function postDataOrPopupError(uri, data, config = undefined) {
  let url = `${getCurrentApiUrl()}${uri}`
  let resp
  try {
    resp = await axios.post(url, data, config)
  } catch (e) {
    return handleRequestError(e, uri)
  }
  return parseDataOrPopupError(resp)
}


export function ClickMenuManager(items, handleSelected) {
  const showClickMenu = ref(false)
  const clickMenuX = ref(0)
  const clickMenuY = ref(0)

  function onShowClickMenu(event) {
    event.preventDefault()
    showClickMenu.value = true
    clickMenuX.value = event.clientX;
    clickMenuY.value = event.clientY;
  }
  function onclickEvent(item) {
    showClickMenu.value = false
    handleSelected(item)
  }
  function onRemove(_) {
    showClickMenu.value = false
  }
  return {
    "items": shallowRef(items),
    "show": showClickMenu,
    "onshow": onShowClickMenu,
    "onclick": onclickEvent,
    "onremove": onRemove,
    "x": clickMenuX,
    "y": clickMenuY,
  }
}


export function readableFileSize(fileSize) {
  if (fileSize == -1) {
    return "? KB"
  }
  let units = ["B", "KiB", "MiB", "GiB", "TiB"]
  let diff = 1024
  if (currentSettings.filesizeUnit == 1000) {
    units = ["B", "KB", "MB", "GB", "TB"]
    diff = 1000
  }
  if (fileSize < diff) {
    return `${fileSize}B`
  }
  for (let unit of units) {
    if (fileSize <= diff || unit == units[units.length - 1]) {
      return `${fileSize.toFixed(2)}${unit}`
    }
    fileSize /= diff
  }
}