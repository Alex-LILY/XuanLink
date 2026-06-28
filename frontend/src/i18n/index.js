import { ref, computed } from 'vue'
import zh from './zh.js'
import en from './en.js'

const dicts = { zh, en }

export const lang = ref(localStorage.getItem('xulink_lang') || 'zh')
export const t = computed(() => dicts[lang.value] || dicts.zh)

export function setLang(l) {
  lang.value = l
  localStorage.setItem('xulink_lang', l)
}

export function sessionTypeName(id, fallback) {
  return t.value.sessionTypes?.[id] || fallback || id
}
