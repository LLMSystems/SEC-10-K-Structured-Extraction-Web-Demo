<script setup lang="ts">
import { computed } from 'vue'
import { Ban, ExternalLink, Minus } from 'lucide-vue-next'
import Drawer from '@/components/ui/Drawer.vue'
import ItemStatusBadge from '@/components/result/ItemStatusBadge.vue'
import { renderMarkdown } from '@/lib/markdown'
import { statusLabel } from '@/lib/statusLabels'
import { flagLabel, severityClasses } from '@/lib/flagLabels'
import type { FilingItem, ValidationFlag } from '@/types/api'

const props = defineProps<{
  open: boolean
  item: FilingItem | null
  flags: ValidationFlag[]
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

const renderedHtml = computed(() =>
  props.item?.content_text ? renderMarkdown(props.item.content_text) : '',
)
const charCount = computed(() => props.item?.content_text?.length ?? 0)
const hasContent = computed(
  () =>
    (props.item?.status === 'extracted' ||
      props.item?.status === 'incorporated_by_reference') &&
    !!renderedHtml.value,
)
const charRangeText = computed(() => {
  const r = props.item?.char_range
  return r ? `${r[0].toLocaleString()}–${r[1].toLocaleString()}` : null
})
</script>

<template>
  <Drawer :open="open" @close="emit('close')">
    <template #header>
      <div v-if="item" class="flex items-center gap-2 text-sm">
        <ItemStatusBadge :status="item.status" small />
        <span class="font-mono text-xs text-muted-foreground">Item {{ item.item_number }}</span>
        <span class="truncate font-semibold text-foreground">{{ item.item_title }}</span>
      </div>
    </template>

    <div v-if="item" class="px-5 py-4">
      <!-- Meta row -->
      <div class="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
        <span>{{ item.part }}</span>
        <span class="inline-flex items-center gap-1">
          狀態：<span class="text-foreground">{{ statusLabel(item.status) }}</span>
        </span>
        <span v-if="item.confidence != null">
          信心：<span class="tabular-nums text-foreground">{{ item.confidence.toFixed(2) }}</span>
        </span>
        <span v-if="charRangeText" class="font-mono">範圍 {{ charRangeText }}</span>
        <span v-if="charCount" class="tabular-nums">{{ charCount.toLocaleString() }} 字</span>
      </div>

      <!-- Item-level flags -->
      <ul v-if="flags.length" class="mt-4 space-y-1.5">
        <li
          v-for="(f, i) in flags"
          :key="i"
          class="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2"
        >
          <span
            class="mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium leading-none"
            :class="severityClasses(f.severity)"
          >
            {{ f.severity }}
          </span>
          <div class="min-w-0">
            <div class="text-sm font-medium text-foreground">{{ flagLabel(f.code) }}</div>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ f.message }}</p>
          </div>
        </li>
      </ul>

      <hr class="my-4 border-border" />

      <!-- Content -->
      <div
        v-if="hasContent"
        class="markdown-body text-[15px] leading-[1.75] text-foreground"
        v-html="renderedHtml"
      />
      <div
        v-else-if="item.status === 'not_applicable'"
        class="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-4"
      >
        <Minus class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <p class="text-sm italic text-muted-foreground">公司聲明此項目不適用。</p>
      </div>
      <div
        v-else-if="item.status === 'reserved'"
        class="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-4"
      >
        <Ban class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <p class="text-sm text-muted-foreground">SEC 規定保留項目，此項目不預期有內容。</p>
      </div>
      <div
        v-else
        class="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-4"
      >
        <ExternalLink class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <p class="text-sm text-muted-foreground">
          此項目無可顯示內容（{{ statusLabel(item.status) }}）。
        </p>
      </div>
    </div>
  </Drawer>
</template>
