<template>
  <view class="page-shell">
    <view class="app-header">
      <view>
        <h1 class="app-title">诊断结果</h1>
        <p class="app-subtitle">AI 仅提供初步判断，安全风险请联系专业人员</p>
      </view>
    </view>

    <view v-if="result" class="result-detail">
      <view class="urgency panel">
        <view class="urgency-level" :class="`level-${result.urgency.level}`">{{ result.urgency.level }}</view>
        <view>
          <view class="card-title">紧急程度</view>
          <view class="card-copy">{{ result.urgency.reason }}</view>
        </view>
      </view>

      <view class="panel block">
        <view class="card-title">故障类型</view>
        <view class="card-copy">{{ result.fault_type.secondary }} / 置信度 {{ Math.round(result.fault_type.confidence * 100) }}%</view>
      </view>

      <view class="panel block">
        <view class="card-title">可能原因</view>
        <view v-for="item in result.possible_causes" :key="item" class="list-item">{{ item }}</view>
      </view>

      <view class="panel block danger-block" v-if="result.forbidden_actions.length">
        <view class="card-title">不要做</view>
        <view v-for="item in result.forbidden_actions" :key="item" class="list-item">{{ item }}</view>
      </view>

      <view class="panel block">
        <view class="card-title">建议下一步</view>
        <view v-for="item in result.recommended_actions" :key="item" class="list-item">{{ item }}</view>
      </view>

      <view class="panel block" v-if="result.price_reference">
        <view class="card-title">参考价格</view>
        <view class="price-text">{{ result.price_reference.range }}</view>
        <view class="card-copy">{{ result.price_reference.disclaimer }}</view>
      </view>

      <button class="primary-button" type="button" @click="saveRecord">保存为维修记录</button>

      <view class="disclaimer-footer">
        本结果由 AI 根据你的文字描述生成，仅供参考，不构成专业意见。涉及用电、燃气、漏水等可能影响人身或财产安全的情况，请优先联系物业或专业人员现场处理。
      </view>

      <view class="panel block feedback-block">
        <view class="card-title">这个诊断有帮助吗？</view>
        <view class="feedback-row">
          <button
            v-for="option in ratingOptions"
            :key="option.value"
            class="feedback-button"
            :class="{ active: feedbackRating === option.value }"
            type="button"
            @click="selectRating(option.value)"
          >
            {{ option.label }}
          </button>
        </view>
        <view v-if="feedbackRating" class="reason-row">
          <button
            v-for="tag in reasonOptions"
            :key="tag.value"
            class="reason-chip"
            :class="{ active: selectedReasons.includes(tag.value) }"
            type="button"
            @click="toggleReason(tag.value)"
          >
            {{ tag.label }}
          </button>
        </view>
        <button
          v-if="feedbackRating"
          class="secondary-action"
          type="button"
          :disabled="isSubmittingFeedback"
          @click="submitFeedback"
        >
          {{ feedbackSubmitted ? '已记录反馈' : '提交反馈' }}
        </button>
      </view>
    </view>

    <view v-else class="empty panel">
      <view class="card-title">暂无诊断结果</view>
      <view class="card-copy">请先在聊天页完成一次文字诊断。</view>
      <button class="primary-button" type="button" @click="goChat">去诊断</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { submitDiagnosisFeedback } from '../../services/diagnosis'
import { useRecordsStore } from '../../stores/records'
import { useSessionStore } from '../../stores/session'
import type { FeedbackRating } from '../../types/diagnosis'

const session = useSessionStore()
const records = useRecordsStore()
const result = computed(() => session.currentResult)
const feedbackRating = ref<FeedbackRating | null>(null)
const selectedReasons = ref<string[]>([])
const isSubmittingFeedback = ref(false)
const feedbackSubmitted = ref(false)

const ratingOptions: { label: string; value: FeedbackRating }[] = [
  { label: '有帮助', value: 'useful' },
  { label: '一般', value: 'neutral' },
  { label: '没帮助', value: 'not_useful' }
]

const reasonOptions = [
  { label: '分类准', value: 'category_accurate' },
  { label: '风险有用', value: 'risk_helpful' },
  { label: '建议清楚', value: 'clear_next_step' },
  { label: '价格有参考', value: 'price_helpful' },
  { label: '分类不准', value: 'category_inaccurate' },
  { label: '建议太泛', value: 'too_generic' }
]

function goChat() {
  uni.navigateBack()
}

async function saveRecord() {
  if (!result.value) return
  await records.saveRecord(result.value.id)
  session.status = 'saved'
  uni.showToast({ title: '已保存记录', icon: 'success' })
}

function selectRating(rating: FeedbackRating) {
  feedbackRating.value = rating
  feedbackSubmitted.value = false
}

function toggleReason(reason: string) {
  feedbackSubmitted.value = false
  selectedReasons.value = selectedReasons.value.includes(reason)
    ? selectedReasons.value.filter((item) => item !== reason)
    : [...selectedReasons.value, reason]
}

async function submitFeedback() {
  if (!result.value || !feedbackRating.value || isSubmittingFeedback.value) return
  isSubmittingFeedback.value = true
  try {
    await submitDiagnosisFeedback(result.value.id, feedbackRating.value, selectedReasons.value)
    feedbackSubmitted.value = true
    uni.showToast({ title: '已记录反馈', icon: 'success' })
  } finally {
    isSubmittingFeedback.value = false
  }
}
</script>

<style scoped>
.result-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.urgency {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px;
}

.urgency-level {
  display: flex;
  width: 54px;
  height: 54px;
  flex: 0 0 54px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: #fff;
  font-size: 28px;
  font-weight: 850;
}

.level-S {
  background: var(--color-danger);
}

.level-A {
  background: #c05621;
}

.level-B {
  background: var(--color-warning);
}

.level-C {
  background: var(--color-success);
}

.block,
.empty {
  padding: 14px;
}

.danger-block {
  border-color: #f0b7ad;
  background: #fff7f6;
}

.card-title {
  font-size: 15px;
  font-weight: 780;
  line-height: 1.3;
}

.card-copy {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.5;
}

.list-item {
  margin-top: 8px;
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.45;
}

.price-text {
  margin-top: 8px;
  color: var(--color-primary-strong);
  font-size: 17px;
  font-weight: 800;
}

.primary-button {
  width: 100%;
  margin: 2px 0 0;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 760;
}

.primary-button::after {
  border: 0;
}

.feedback-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.feedback-row,
.reason-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-button,
.reason-chip,
.secondary-action {
  margin: 0;
  border: 1px solid var(--color-border);
  background: #fff;
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.2;
}

.feedback-button::after,
.reason-chip::after,
.secondary-action::after {
  border: 0;
}

.feedback-button {
  flex: 1;
  min-width: 76px;
  padding: 10px 8px;
  border-radius: var(--radius-md);
}

.reason-chip {
  padding: 8px 10px;
  border-radius: 999px;
}

.feedback-button.active,
.reason-chip.active {
  border-color: var(--color-primary);
  background: var(--color-surface-soft);
  color: var(--color-primary-strong);
  font-weight: 760;
}

.secondary-action {
  align-self: flex-start;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  color: var(--color-primary);
  font-weight: 760;
}

.secondary-action[disabled] {
  opacity: 0.6;
}

.disclaimer-footer {
  margin: 2px 0 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.5;
}
</style>
