<template>
  <view class="page-shell">
    <view class="app-header">
      <view>
        <h1 class="app-title">记录详情</h1>
        <p class="app-subtitle">补充实际维修结果，形成家庭维修档案</p>
      </view>
    </view>

    <view v-if="loading" class="panel block">
      <view class="card-title">正在加载记录</view>
      <view class="card-copy">请稍候。</view>
    </view>

    <view v-else-if="!record" class="panel block">
      <view class="card-title">记录不存在</view>
      <view class="card-copy">可能已被删除，请返回列表重试。</view>
    </view>

    <template v-else>
      <view class="panel block">
        <view class="card-head">
          <view class="card-title">{{ secondaryLabel(record.secondary_category) }}</view>
          <view v-if="record.urgency_level" class="urg-tag" :class="`level-${record.urgency_level}`">{{ record.urgency_level }}</view>
        </view>
        <view class="card-copy">位置：{{ record.house_area || '未填写' }}</view>
        <view class="card-copy">创建时间：{{ formatTime(record.created_at) }}</view>
      </view>

      <view v-if="record.possible_causes && record.possible_causes.length" class="panel block">
        <view class="card-title">可能原因</view>
        <view v-for="item in record.possible_causes" :key="item" class="list-item">{{ item }}</view>
      </view>

      <view v-if="record.forbidden_actions && record.forbidden_actions.length" class="panel block danger-block">
        <view class="card-title">不要做</view>
        <view v-for="item in record.forbidden_actions" :key="item" class="list-item">{{ item }}</view>
      </view>

      <view v-if="record.recommended_actions && record.recommended_actions.length" class="panel block">
        <view class="card-title">建议下一步</view>
        <view v-for="item in record.recommended_actions" :key="item" class="list-item">{{ item }}</view>
      </view>

      <view v-if="record.price_range" class="panel block">
        <view class="card-title">参考价格</view>
        <view class="price-text">{{ record.price_range }}</view>
      </view>

      <view class="panel block form-block">
        <view class="card-title">实际维修结果</view>

        <view class="form-row">
          <view class="form-label">实际维修方式</view>
          <textarea
            v-model="solutionDraft"
            class="form-textarea"
            auto-height
            maxlength="300"
            placeholder="如：联系物业更换角阀"
          />
        </view>

        <view class="form-row">
          <view class="form-label">实际费用（元）</view>
          <input v-model="costDraft" class="form-input" type="number" placeholder="可选" />
        </view>

        <view class="form-row">
          <view class="form-label">服务商 / 师傅</view>
          <input v-model="providerDraft" class="form-input" maxlength="40" placeholder="可选" />
        </view>

        <view class="form-row">
          <view class="form-label">是否解决</view>
          <view class="chip-row">
            <button
              v-for="opt in resolvedOptions"
              :key="opt.value"
              class="chip"
              :class="{ active: resolvedChoice === opt.value }"
              type="button"
              @click="resolvedChoice = opt.value"
            >{{ opt.label }}</button>
          </view>
        </view>

        <view class="form-row">
          <view class="form-label">是否复发</view>
          <view class="chip-row">
            <button
              v-for="opt in recurredOptions"
              :key="opt.value"
              class="chip"
              :class="{ active: recurredChoice === opt.value }"
              type="button"
              @click="recurredChoice = opt.value"
            >{{ opt.label }}</button>
          </view>
        </view>
      </view>

      <button class="primary-button" type="button" :disabled="submitting" @click="submit">{{ submitting ? '提交中…' : '保存回填信息' }}</button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { fetchRepairRecord, secondaryLabel, type RepairRecord, type RepairRecordPatch } from '../../services/records'
import { useRecordsStore } from '../../stores/records'

const records = useRecordsStore()
const record = ref<RepairRecord | null>(null)
const loading = ref(true)
const submitting = ref(false)

const solutionDraft = ref('')
const costDraft = ref('')
const providerDraft = ref('')
const resolvedChoice = ref<'unset' | 'yes' | 'no'>('unset')
const recurredChoice = ref<'unset' | 'yes' | 'no'>('unset')

const resolvedOptions = [
  { label: '未填', value: 'unset' as const },
  { label: '已解决', value: 'yes' as const },
  { label: '未解决', value: 'no' as const }
]
const recurredOptions = [
  { label: '未填', value: 'unset' as const },
  { label: '是', value: 'yes' as const },
  { label: '否', value: 'no' as const }
]

onLoad(async (query) => {
  const id = (query as { id?: string } | undefined)?.id
  if (!id) {
    loading.value = false
    return
  }
  try {
    record.value = await fetchRepairRecord(id)
    hydrateForm()
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
})

function hydrateForm() {
  if (!record.value) return
  solutionDraft.value = record.value.actual_solution || ''
  costDraft.value = record.value.actual_cost != null ? String(record.value.actual_cost) : ''
  providerDraft.value = record.value.provider_name || ''
  if (record.value.is_resolved === true) resolvedChoice.value = 'yes'
  else if (record.value.is_resolved === false) resolvedChoice.value = 'no'
  else resolvedChoice.value = 'unset'
  if (record.value.is_recurred === true) recurredChoice.value = 'yes'
  else if (record.value.is_recurred === false) recurredChoice.value = 'no'
  else recurredChoice.value = 'unset'
}

async function submit() {
  if (!record.value || submitting.value) return
  submitting.value = true
  const patch: RepairRecordPatch = {}
  const solution = solutionDraft.value.trim()
  if (solution) patch.actual_solution = solution
  const cost = costDraft.value.trim()
  if (cost !== '' && !Number.isNaN(Number(cost))) patch.actual_cost = Number(cost)
  const provider = providerDraft.value.trim()
  if (provider) patch.provider_name = provider
  if (resolvedChoice.value === 'yes') patch.is_resolved = true
  else if (resolvedChoice.value === 'no') patch.is_resolved = false
  if (recurredChoice.value === 'yes') patch.is_recurred = true
  else if (recurredChoice.value === 'no') patch.is_recurred = false

  try {
    await records.updateRecord(record.value.id, patch)
    uni.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 600)
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '保存失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

function formatTime(value: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.block {
  padding: 14px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 780;
}

.card-copy {
  margin-top: 6px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.5;
}

.list-item {
  margin-top: 8px;
  padding-left: 12px;
  border-left: 3px solid var(--color-border);
  font-size: 14px;
  line-height: 1.55;
}

.danger-block {
  border-color: #f0b7ad;
  background: #fff7f6;
}

.danger-block .list-item {
  border-left-color: var(--color-danger);
}

.price-text {
  margin-top: 6px;
  color: var(--color-primary-strong);
  font-size: 15px;
  font-weight: 700;
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 14px;
  line-height: 1.5;
}

.form-textarea {
  min-height: 56px;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 7px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.chip::after {
  border: 0;
}

.chip.active {
  border-color: var(--color-primary);
  background: var(--color-surface-soft);
  color: var(--color-primary-strong);
}

.primary-button {
  margin-top: 4px;
  padding: 13px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 750;
}

.primary-button::after {
  border: 0;
}

.primary-button[disabled] {
  opacity: 0.6;
}
</style>
