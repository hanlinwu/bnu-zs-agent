import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPublicSystemBasicConfig } from '@/api/system'

type SystemBasic = {
  system_name: string
  system_logo: string
}

const DEFAULT_SYSTEM_BASIC: SystemBasic = {
  system_name: '京师小智',
  system_logo: '',
}

export const useSystemStore = defineStore('system', () => {
  const basic = ref<SystemBasic>({ ...DEFAULT_SYSTEM_BASIC })
  const loaded = ref(false)
  let loadingPromise: Promise<void> | null = null

  async function fetchBasic(force = false) {
    if (loaded.value && !force) return
    if (loadingPromise && !force) return loadingPromise

    loadingPromise = (async () => {
      try {
        const res = await getPublicSystemBasicConfig()
        basic.value = {
          system_name: res.data.value.system_name || DEFAULT_SYSTEM_BASIC.system_name,
          system_logo: res.data.value.system_logo || '',
        }
        loaded.value = true
      } catch {
        // keep defaults on failure
      } finally {
        loadingPromise = null
      }
    })()

    return loadingPromise
  }

  function setBasic(value: SystemBasic) {
    basic.value = {
      system_name: value.system_name || DEFAULT_SYSTEM_BASIC.system_name,
      system_logo: value.system_logo || '',
    }
    loaded.value = true
  }

  return {
    basic,
    loaded,
    fetchBasic,
    setBasic,
  }
})
