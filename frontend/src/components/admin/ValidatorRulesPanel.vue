<script setup lang="ts">
import Card from '@/components/ui/Card.vue'
import { flagLabel, severityClasses } from '@/lib/flagLabels'
import type { ValidationSeverity } from '@/types/api'

// 本面板的內容鏡像 docs/validator-rules.md，後者再鏡像 api/sec_10k_pipeline/validators.py。
// 改動驗證器規則時，三處需同步。

interface RuleRow {
  id: string
  codes: string[]
  severities: ValidationSeverity[]
  severityNote?: string
  target: string
  summary: string
  detail: string
  source?: string
}

const rules: RuleRow[] = [
  {
    id: '0',
    codes: ['range_invalid'],
    severities: ['error'],
    target: 'raw_items',
    summary: '字元範圍須 0 ≤ start < end ≤ len(text)',
    detail:
      '對每個 raw item 的每段 span 檢查 0 ≤ start < end ≤ len(text)，抓「標題定位錯誤」「座標被夾成 0」「反向 range」等幾何 bug。',
  },
  {
    id: '2',
    codes: ['ordering_violation'],
    severities: ['warning', 'info'],
    severityNote: '多 span 路徑降為 info',
    target: 'raw_items',
    summary: 'item 物理位置須照編號順序遞增',
    detail:
      '把有幾何的 item 按標準編號排序，檢查 first-span 起始位置是否單調遞增，倒退即 flag。當任一 raw item 帶 spans（cross-reference / pdf-style parser）時降為 info，因這類年報的 SEC item 物理順序可能合法地不照編號。',
  },
  {
    id: "3'",
    codes: ['oversized_item'],
    severities: ['warning'],
    target: 'raw_items',
    summary: '單一 item 不該佔全體可讀內容過大比例',
    detail:
      '單一 item 可讀字數佔「全體 item 可讀總和」> 45%（OVERSIZED_RATIO）且絕對值 > 50,000 字，視為疑似吞併了漏抓的鄰近 item。僅在有幾何的 item ≥ 6 時檢查，並排除天生大的 item {1, 1A, 7, 8}。',
    source: '① 剖面：這四項 median ≥ 40k',
  },
  {
    id: '4',
    codes: ['required_item_missing', 'recommended_item_missing', 'unexpected_item_status'],
    severities: ['error', 'warning'],
    target: 'items',
    summary: '每個 item 的 status 須落在「正常」集合',
    detail:
      '依 ITEM_EXPECTED_STATUS 檢查每個 item 的 status。屬 CORE_ITEMS 卻不在預期集合 → required_item_missing（error）；例外 1A 且為 SRC → 降為 recommended_item_missing（warning，法規上 SRC 可省略 1A）；非核心 item 不在預期 → unexpected_item_status（warning，主要抓 Part III 的 missing）。',
    source: '① 剖面的 item 原型',
  },
  {
    id: '4b',
    codes: ['item8_undersized'],
    severities: ['warning'],
    target: 'items',
    summary: 'Item 8 標 extracted 卻過短（疑似漏抓的 by_reference）',
    detail:
      'Item 8 標 extracted 但可讀字數 < 40,000（ITEM8_MIN_EXTRACTED_READABLE）→ 疑似「財報見 F-pages」的指標文字沒被識別成 incorporated_by_reference。',
    source: '① 剖面：清理後 Item 8 extracted 的 p5 ≈ 74k',
  },
  {
    id: '4c',
    codes: ['item1a_undersized'],
    severities: ['warning'],
    target: 'items',
    summary: 'Item 1A 過短（門檻分 SRC / 非SRC）',
    detail:
      'Item 1A 標 extracted 但可讀字數低於下限 → 疑似被截斷或漏抓。唯一分規模的長度門檻：非SRC < 25,000、SRC < 20,000。',
    source: '② 規模分層：1A 是唯一明顯隨規模放大的 item（非SRC median 70k vs SRC 41k，1.73×）',
  },
  {
    id: '5',
    codes: ['status_field_contract'],
    severities: ['error'],
    target: 'items',
    summary: 'status 與 content / range 欄位須自洽',
    detail:
      'extracted → 必須有 content_text 且有 char_range；reserved / not_applicable / missing → content_text 與 char_range 皆須為 null；incorporated_by_reference → 契約寬鬆，不檢查。',
  },
  {
    id: '6',
    codes: ['extracted_empty'],
    severities: ['error'],
    target: 'items',
    summary: 'extracted 卻幾乎沒有可讀內容',
    detail: 'status = extracted 但可讀字數 < 50（EXTRACTED_MIN_READABLE）→ 內容幾乎為空，矛盾。',
  },
  {
    id: '7',
    codes: ['document_too_short', 'document_short'],
    severities: ['error', 'warning'],
    target: 'text',
    summary: '全文可讀長度過短',
    detail:
      '全文可讀字數 < 30,000（DOC_FLOOR_ERROR）→ document_too_short（error，很可能抓錯主文件或 preprocess 清掉內容）；< 80,000（DOC_FLOOR_WARN）→ document_short（warning）。',
    source: '①/③ 語料中最小的全文可讀長度 > 100k，故 30k/80k 為安全低標',
  },
  {
    id: '8',
    codes: ['low_confidence_parse', 'low_confidence_item'],
    severities: ['info'],
    target: 'raw_items + parse_result',
    summary: 'parser 信心低於門檻',
    detail:
      'parse_result.confidence < 0.7（CONFIDENCE_THRESHOLD）→ low_confidence_parse；任一 raw item confidence < 0.7 → low_confidence_item。info 不影響分數與有效性，僅提示。',
  },
  {
    id: '9',
    codes: ['low_item_coverage'],
    severities: ['error', 'warning'],
    severityNote: '< 25% 為 error，25–50% 為 warning',
    target: 'items',
    summary: '所有 item 可讀字數加總應接近全文總字數',
    detail:
      '將所有 item 的 content_text 可讀字數（去 HTML 與 marker 後）加總，除以全文可讀字數。比例 < 50%（ITEM_COVERAGE_WARN）→ warning；< 25%（ITEM_COVERAGE_ERROR）→ error。incorporated_by_reference / not_applicable 等無 content_text，故門檻設得寬鬆。觸發時通常代表 parser 切割嚴重失敗，有大段內容未歸屬到任何 Item。',
  },
]

// ITEM_EXPECTED_STATUS：每個 item 的「正常」status 集合
interface ItemRow {
  item: string
  title: string
  statuses: string
  note: string
  core?: boolean
}
const itemStatus: ItemRow[] = [
  { item: '1', title: 'Business', statuses: 'extracted', note: '核心', core: true },
  { item: '1A', title: 'Risk Factors', statuses: 'extracted', note: '核心（SRC 缺失降 warning）', core: true },
  { item: '1B', title: 'Unresolved Staff Comments', statuses: 'not_applicable, extracted', note: '多為 N/A' },
  { item: '1C', title: 'Cybersecurity', statuses: 'extracted, not_applicable, missing', note: '2023+ 新規，過渡期容許 missing' },
  { item: '2', title: 'Properties', statuses: 'extracted', note: '核心', core: true },
  { item: '3', title: 'Legal Proceedings', statuses: 'extracted, not_applicable', note: '核心，但允許 N/A（無訴訟）', core: true },
  { item: '4', title: 'Mine Safety', statuses: 'not_applicable, extracted, missing', note: '多為 N/A' },
  { item: '5', title: 'Market for Common Equity', statuses: 'extracted', note: '核心', core: true },
  { item: '6', title: 'Reserved', statuses: 'reserved, extracted, not_applicable, missing', note: '2021+ 多為 reserved' },
  { item: '7', title: 'MD&A', statuses: 'extracted', note: '核心', core: true },
  { item: '7A', title: 'Market Risk', statuses: 'extracted, not_applicable', note: 'SRC 常為 N/A' },
  { item: '8', title: 'Financial Statements', statuses: 'extracted, incorporated_by_reference', note: '核心，允許 by_reference', core: true },
  { item: '9', title: 'Changes in Accountants', statuses: 'not_applicable, extracted, missing', note: '多為 N/A' },
  { item: '9A', title: 'Controls and Procedures', statuses: 'extracted', note: '核心', core: true },
  { item: '9B', title: 'Other Information', statuses: 'not_applicable, extracted', note: '—' },
  { item: '9C', title: 'Foreign Jurisdictions', statuses: 'not_applicable, missing, extracted', note: '2021+ 新增，早年容許 missing' },
  { item: '10–14', title: 'Part III', statuses: 'incorporated_by_reference, extracted', note: '多引用 proxy，missing 屬異常' },
  { item: '15', title: 'Exhibits', statuses: 'extracted', note: '核心', core: true },
  { item: '16', title: 'Form 10-K Summary', statuses: 'not_applicable, extracted', note: '選填，多為 N/A' },
]

// 門檻常數與數據出處
const sources: { name: string; from: string }[] = [
  { name: 'ITEM_EXPECTED_STATUS / CORE_ITEMS', from: '① 逐 Item 剖面（item 原型、100% extracted 的核心清單）' },
  { name: 'NATURALLY_LARGE_ITEMS = {1,1A,7,8}', from: '① 剖面 median ≥ 40k' },
  { name: 'ITEM8_MIN_EXTRACTED_READABLE = 40k', from: '① Item 8 extracted 的 p5 ≈ 74k' },
  { name: 'ITEM1A_MIN_NON_SRC / _SRC = 25k / 20k', from: '② 規模分層（1A 1.73×；各桶最小值 ≈27.5k/30k）' },
  { name: 'DOC_FLOOR_ERROR / WARN = 30k / 80k', from: '①/③ 最小全文可讀長度 > 100k' },
  { name: '1C / 9C 容許 missing', from: '③ 時間切面（1C 2023 過渡期 2/9 缺漏；9C pre-2021 尚未存在）' },
]

function sevLabel(s: ValidationSeverity): string {
  return s
}
</script>

<template>
  <div class="space-y-6">
    <!-- 說明 -->
    <Card class="p-4">
      <h2 class="text-sm font-medium text-foreground">驗證層如何運作</h2>
      <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
        驗證層獨立於 parser，在 postprocess 之後執行，重新核對結構不變量，捕捉「parser 說成功、實際卻錯」的靜默錯誤，
        輸出 <code class="rounded bg-muted px-1 py-0.5 text-xs">QualityReport</code> 掛在
        <code class="rounded bg-muted px-1 py-0.5 text-xs">FilingOutput.quality</code>。
      </p>
      <div class="mt-3 flex flex-wrap gap-2 text-xs">
        <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5" :class="severityClasses('error')">
          error · 幾乎確定是 bug，扣 0.2 分、使 filing 無效
        </span>
        <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5" :class="severityClasses('warning')">
          warning · 可疑待人複查，扣 0.05 分
        </span>
        <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5" :class="severityClasses('info')">
          info · 提示，不影響分數
        </span>
      </div>
      <p class="mt-3 text-xs text-muted-foreground">
        分數公式：<code class="rounded bg-muted px-1 py-0.5">score = max(0, 1 − 0.2 × error 數 − 0.05 × warning 數)</code>。
        「可讀字數」= 去除 HTML 標籤與 [[ANCHOR]]/[[PAGE]] 注入標記後的字元數。
      </p>
    </Card>

    <!-- 規則細節 -->
    <Card class="overflow-hidden">
      <div class="border-b border-border px-4 py-3 text-sm font-medium text-foreground">
        規則清單（{{ rules.length }}）
      </div>
      <ul class="divide-y divide-border/60">
        <li v-for="r in rules" :key="r.id" class="px-4 py-3.5">
          <div class="flex flex-wrap items-center gap-2">
            <span class="inline-flex h-5 min-w-[1.75rem] items-center justify-center rounded bg-muted px-1.5 font-mono text-xs font-semibold text-foreground">
              {{ r.id }}
            </span>
            <span
              v-for="s in r.severities"
              :key="s"
              class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium leading-none"
              :class="severityClasses(s)"
            >
              {{ sevLabel(s) }}
            </span>
            <span class="text-xs text-muted-foreground">對象：{{ r.target }}</span>
            <span v-if="r.severityNote" class="text-xs text-muted-foreground/70">（{{ r.severityNote }}）</span>
          </div>
          <p class="mt-1.5 text-sm font-medium text-foreground">{{ r.summary }}</p>
          <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ r.detail }}</p>
          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <span
              v-for="c in r.codes"
              :key="c"
              class="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
            >
              {{ c }} · {{ flagLabel(c) }}
            </span>
          </div>
          <p v-if="r.source" class="mt-1.5 text-[11px] text-muted-foreground/70">
            數據出處：{{ r.source }}
          </p>
        </li>
      </ul>
    </Card>

    <!-- ITEM_EXPECTED_STATUS -->
    <Card class="overflow-hidden">
      <div class="border-b border-border px-4 py-3">
        <span class="text-sm font-medium text-foreground">ITEM_EXPECTED_STATUS</span>
        <span class="ml-2 text-xs text-muted-foreground">每個 item 的「正常」status 集合；不在集合內即觸發 Rule 4</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border text-left text-xs text-muted-foreground">
              <th class="px-4 py-2 font-medium">Item</th>
              <th class="px-4 py-2 font-medium">標題</th>
              <th class="px-4 py-2 font-medium">正常 status</th>
              <th class="px-4 py-2 font-medium">備註</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in itemStatus" :key="row.item" class="border-b border-border/60">
              <td class="px-4 py-2 font-mono text-xs font-medium">
                <span :class="row.core ? 'text-foreground' : 'text-muted-foreground'">{{ row.item }}</span>
                <span v-if="row.core" class="ml-1 rounded bg-primary/10 px-1 py-0.5 text-[9px] text-primary">核心</span>
              </td>
              <td class="px-4 py-2 text-foreground">{{ row.title }}</td>
              <td class="px-4 py-2 font-mono text-xs text-muted-foreground">{{ row.statuses }}</td>
              <td class="px-4 py-2 text-xs text-muted-foreground">{{ row.note }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
        核心 item（status 異常 → error）：<span class="font-mono text-foreground">1, 1A, 2, 3, 5, 7, 8, 9A, 15</span>
      </div>
    </Card>

    <!-- 數據出處 -->
    <Card class="overflow-hidden">
      <div class="border-b border-border px-4 py-3">
        <span class="text-sm font-medium text-foreground">門檻校準的數據出處</span>
        <span class="ml-2 text-xs text-muted-foreground">來自 34 份人工標註 10-K（eval_datasets/analysis）</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border text-left text-xs text-muted-foreground">
              <th class="px-4 py-2 font-medium">規則 / 常數</th>
              <th class="px-4 py-2 font-medium">數據出處</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sources" :key="s.name" class="border-b border-border/60">
              <td class="px-4 py-2 font-mono text-xs text-foreground">{{ s.name }}</td>
              <td class="px-4 py-2 text-xs text-muted-foreground">{{ s.from }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
        校準驗證：34 份正常 GT 全跑，status / 長度類規則僅 2 個 flag，皆為真實邊緣案例，零誤報。
        完整文件見 <code class="rounded bg-muted px-1 py-0.5">docs/validator-rules.md</code>。
      </div>
    </Card>
  </div>
</template>
