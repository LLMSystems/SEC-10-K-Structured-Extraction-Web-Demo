<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  AlertCircle,
  Ban,
  Download,
  ExternalLink,
  FileText,
  Minus,
  RotateCw,
  Sparkles,
} from 'lucide-vue-next'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Tabs from '@/components/ui/Tabs.vue'
import TabsList from '@/components/ui/TabsList.vue'
import TabsTrigger from '@/components/ui/TabsTrigger.vue'
import TabsContent from '@/components/ui/TabsContent.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import MonoText from '@/components/common/MonoText.vue'
import { renderMarkdown } from '@/lib/markdown'
import { statusLabel } from '@/lib/statusLabels'
import { useJobStore } from '@/stores/job'
import { useXbrlStore } from '@/stores/xbrl'
import type { FilingItem } from '@/types/api'

const props = defineProps<{ item: FilingItem | null }>()

const jobStore = useJobStore()
const xbrl = useXbrlStore()

const charRangeText = computed(() => {
  if (!props.item?.char_range) return null
  const [a, b] = props.item.char_range
  return `字元範圍 ${a.toLocaleString()}–${b.toLocaleString()}`
})

const renderedHtml = computed(() => {
  if (!props.item?.content_text) return ''
  return renderMarkdown(props.item.content_text)
})

// Item 8 = "Financial Statements and Supplementary Data" in Part II.
// Only offer the XBRL toggle when the item has extractable content; for
// reserved / not_applicable / missing there's nothing to compare against.
const isItem8 = computed(
  () =>
    props.item?.part === 'Part II' &&
    props.item?.item_number === '8' &&
    (props.item?.status === 'extracted' ||
      props.item?.status === 'incorporated_by_reference'),
)

const cik = computed(() => jobStore.filingResult?.filing_info.cik ?? null)
const accession = computed(
  () => jobStore.filingResult?.filing_info.accession_number ?? null,
)

const xbrlMarkdown = computed(() =>
  accession.value ? xbrl.get(accession.value) : null,
)
const xbrlLoading = computed(() =>
  accession.value ? xbrl.isLoading(accession.value) : false,
)
const xbrlError = computed(() =>
  accession.value ? xbrl.getError(accession.value) : null,
)
const renderedXbrlHtml = computed(() =>
  xbrlMarkdown.value ? renderMarkdown(xbrlMarkdown.value) : '',
)

const activeTab = ref<'html' | 'xbrl'>('html')

// Reset to the HTML tab whenever the navigator picks a different item.
watch(
  () => props.item,
  () => {
    activeTab.value = 'html'
  },
)

watch(activeTab, (v) => {
  if (v !== 'xbrl') return
  if (!cik.value || !accession.value) return
  if (xbrlMarkdown.value || xbrlLoading.value) return
  xbrl.fetchXbrl(cik.value, accession.value)
})

// Elapsed-seconds counter, only ticks while the XBRL request is in flight.
const elapsedSec = ref(0)
let elapsedTimer: ReturnType<typeof setInterval> | null = null

function startElapsed() {
  elapsedSec.value = 0
  stopElapsed()
  elapsedTimer = setInterval(() => {
    elapsedSec.value += 1
  }, 1000)
}
function stopElapsed() {
  if (elapsedTimer !== null) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}
watch(xbrlLoading, (loading) => {
  if (loading) startElapsed()
  else stopElapsed()
})
onBeforeUnmount(stopElapsed)

function onRetryXbrl() {
  if (!cik.value || !accession.value) return
  xbrl.retry(cik.value, accession.value)
}

function onDownloadXbrl() {
  if (!xbrlMarkdown.value || !accession.value) return
  const blob = new Blob([xbrlMarkdown.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${accession.value}-item8-xbrl.md`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div v-if="!item" class="flex h-full flex-col items-center justify-center p-12 text-center">
    <FileText class="h-10 w-10 text-muted-foreground/60" />
    <p class="mt-4 text-sm font-medium text-foreground">請選擇一個項目</p>
    <p class="mt-1 text-xs text-muted-foreground">
      從左側導覽列點選任一項目以查看其內文。
    </p>
  </div>

  <article
    v-else
    :key="`${item.part}-${item.item_number}`"
    class="px-8 py-10 animate-in fade-in slide-in-from-right-1 duration-200"
  >
    <header class="mb-8">
      <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <span class="font-medium tracking-widest">{{ item.part }}</span>
        <span aria-hidden>·</span>
        <span>Item {{ item.item_number }}</span>
        <Badge
          v-if="item.status === 'extracted'"
          variant="success"
          class="ml-auto"
        >
          已解析
        </Badge>
        <Badge
          v-else-if="item.status === 'incorporated_by_reference'"
          variant="info"
          class="ml-auto"
        >
          引用揭露
        </Badge>
        <Badge v-else variant="secondary" class="ml-auto">
          {{ statusLabel(item.status) }}
        </Badge>
      </div>
      <h1 class="mt-2 text-2xl font-semibold tracking-tight text-foreground">
        {{ item.item_title }}
      </h1>
      <MonoText v-if="charRangeText" class="mt-2 block text-xs text-muted-foreground">
        {{ charRangeText }}
      </MonoText>
    </header>

    <!-- Banner for incorporated_by_reference items (shown above content) -->
    <div
      v-if="item.status === 'incorporated_by_reference'"
      class="mb-6 flex items-start gap-3 rounded-lg border border-blue-500/30 bg-blue-500/5 p-4"
    >
      <ExternalLink class="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
      <div class="text-sm">
        <p class="font-medium text-foreground">以引用方式揭露</p>
        <p class="mt-1 text-muted-foreground">
          此項目的完整揭露位於另一份 SEC 文件（通常是 definitive proxy statement）。下方為 10-K
          中的引用通告原文。
        </p>
      </div>
    </div>

    <!-- Item 8: HTML / XBRL toggle -->
    <template v-if="isItem8">
      <Tabs v-model="activeTab" class="space-y-3">
        <div class="flex flex-wrap items-center gap-3">
          <TabsList>
            <TabsTrigger value="html">HTML 原文</TabsTrigger>
            <TabsTrigger value="xbrl">
              <Sparkles class="mr-1 h-3 w-3" />
              XBRL 結構化
            </TabsTrigger>
          </TabsList>
          <Button
            v-if="activeTab === 'xbrl' && xbrlMarkdown"
            variant="outline"
            size="sm"
            class="ml-auto"
            @click="onDownloadXbrl"
          >
            <Download class="h-3.5 w-3.5" />
            下載 .md
          </Button>
        </div>

        <TabsContent value="html">
          <div
            class="markdown-body text-[15px] leading-[1.75] text-foreground"
            v-html="renderedHtml"
          />
        </TabsContent>

        <TabsContent value="xbrl">
          <!-- Loading -->
          <div v-if="xbrlLoading" class="space-y-4">
            <div
              class="flex items-center gap-3 rounded-lg border border-border bg-muted/30 p-4"
            >
              <LoadingSpinner class="text-primary" />
              <div class="flex-1 text-sm">
                <p class="font-medium text-foreground">向 SEC 取得 XBRL 財報資料中…</p>
                <p class="mt-0.5 text-xs text-muted-foreground">
                  已等待 {{ elapsedSec }} 秒（一般需要 5–15 秒）
                </p>
              </div>
            </div>
            <Skeleton class="h-32 w-full" />
            <Skeleton class="h-32 w-full" />
            <Skeleton class="h-24 w-full" />
          </div>

          <!-- Error -->
          <div
            v-else-if="xbrlError"
            class="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4"
          >
            <AlertCircle class="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div class="flex-1 text-sm">
              <p class="font-medium text-foreground">XBRL 資料取得失敗</p>
              <p class="mt-1 text-muted-foreground">{{ xbrlError }}</p>
              <Button variant="outline" size="sm" class="mt-3" @click="onRetryXbrl">
                <RotateCw class="h-3.5 w-3.5" />
                重試
              </Button>
            </div>
          </div>

          <!-- Rendered Markdown -->
          <div
            v-else-if="renderedXbrlHtml"
            class="markdown-body text-[15px] leading-[1.75] text-foreground"
            v-html="renderedXbrlHtml"
          />

          <!-- Fallback (shouldn't normally appear because watch triggers fetch) -->
          <div v-else class="text-sm text-muted-foreground">
            正在準備載入 XBRL 資料…
          </div>
        </TabsContent>
      </Tabs>
    </template>

    <!-- Non-Item 8 extracted / incorporated content (unchanged path) -->
    <template
      v-else-if="
        (item.status === 'extracted' || item.status === 'incorporated_by_reference') &&
        renderedHtml
      "
    >
      <div
        class="markdown-body text-[15px] leading-[1.75] text-foreground"
        v-html="renderedHtml"
      />
    </template>

    <div
      v-else-if="item.status === 'not_applicable'"
      class="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-4"
    >
      <Minus class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <p class="text-sm italic text-muted-foreground">
        公司聲明此項目不適用。
      </p>
    </div>

    <div
      v-else-if="item.status === 'reserved'"
      class="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-4"
    >
      <Ban class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">
        SEC 規定保留項目，此項目不預期有內容。
      </p>
    </div>
  </article>
</template>
