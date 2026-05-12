import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, ApiError } from '@/lib/api'

/**
 * XBRL Markdown for Item 8 financial statements.
 * Per-accession cache + loading + error tracked separately so multiple filings
 * can be navigated without interference. Fetches are lazy — only triggered when
 * the user actively switches to the XBRL tab.
 */
export const useXbrlStore = defineStore('xbrl', () => {
  const cache = ref<Map<string, string>>(new Map())
  const loading = ref<Set<string>>(new Set())
  const errors = ref<Map<string, string>>(new Map())

  function get(accession: string): string | null {
    return cache.value.get(accession) ?? null
  }

  function isLoading(accession: string): boolean {
    return loading.value.has(accession)
  }

  function getError(accession: string): string | null {
    return errors.value.get(accession) ?? null
  }

  function setLoading(accession: string, on: boolean) {
    const next = new Set(loading.value)
    if (on) next.add(accession)
    else next.delete(accession)
    loading.value = next
  }

  function clearError(accession: string) {
    if (!errors.value.has(accession)) return
    const next = new Map(errors.value)
    next.delete(accession)
    errors.value = next
  }

  async function fetchXbrl(cik: string, accession: string): Promise<void> {
    if (cache.value.has(accession) || loading.value.has(accession)) return

    setLoading(accession, true)
    clearError(accession)

    try {
      const md = await api.xbrlMarkdown(cik, accession)
      const next = new Map(cache.value)
      next.set(accession, md)
      cache.value = next
    } catch (err) {
      let message: string
      if (err instanceof ApiError) {
        message =
          err.status === 422 ? `此 filing 沒有 XBRL 資料（${err.message}）` : err.message
      } else {
        message = err instanceof Error ? err.message : '未知錯誤'
      }
      const next = new Map(errors.value)
      next.set(accession, message)
      errors.value = next
    } finally {
      setLoading(accession, false)
    }
  }

  function retry(cik: string, accession: string): Promise<void> {
    clearError(accession)
    return fetchXbrl(cik, accession)
  }

  return { get, isLoading, getError, fetchXbrl, retry }
})
