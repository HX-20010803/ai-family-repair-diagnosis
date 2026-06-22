<template>
  <view class="page-shell chat-page">
    <view class="app-header">
      <view>
        <h1 class="app-title">维修诊断助手</h1>
        <p class="app-subtitle">3 分钟判断故障、风险、价格和下一步</p>
      </view>
      <button class="icon-button" type="button" @click="goRecords">记</button>
    </view>

    <SafetyBanner />

    <view class="chat-panel panel">
      <view class="assistant-intro">
        <view class="ai-avatar">AI</view>
        <view class="intro-body">
          <view class="intro-title">直接告诉我家里哪里不对劲</view>
          <view class="intro-copy">我会追问关键信息，并判断风险、价格和下一步。</view>
        </view>
      </view>

      <scroll-view class="message-list" scroll-y>
        <ChatMessage v-for="message in session.messages" :key="message.id" :message="message" />
        <view v-if="session.messages.length === 1 && !session.currentResult" class="prompt-panel">
          <view class="prompt-title">可以这样问</view>
          <QuickFaultChips @select="handleSend" />
        </view>
        <view v-if="session.error" class="error-text">{{ session.error }}</view>
      </scroll-view>

      <view v-if="session.currentResult" class="result-card">
        <view class="result-level" :class="`level-${session.currentResult.urgency.level}`">
          {{ session.currentResult.urgency.level }}
        </view>
        <view class="result-body">
          <view class="result-title">已生成结构化诊断</view>
          <view class="result-copy">{{ session.currentResult.urgency.reason }}</view>
          <button class="secondary-button" type="button" @click="goResult">查看结果</button>
        </view>
      </view>

      <view class="action-row" v-if="session.status === 'asking' && session.sessionId">
        <button class="secondary-button" type="button" @click="session.complete">直接生成结果</button>
        <text class="round-text">已追问 {{ session.roundCount }}/3 轮</text>
      </view>

      <ChatInput :disabled="isBusy" @send="handleSend" />
    </view>

    <button class="reset-button" type="button" @click="session.reset">开始新的诊断</button>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ChatInput from './components/ChatInput.vue'
import ChatMessage from './components/ChatMessage.vue'
import QuickFaultChips from './components/QuickFaultChips.vue'
import SafetyBanner from './components/SafetyBanner.vue'
import { useSessionStore } from '../../stores/session'

const session = useSessionStore()
const isBusy = computed(() => session.status === 'creating' || session.status === 'completing')

function handleSend(text: string) {
  session.send(text)
}

function goResult() {
  uni.navigateTo({ url: '/pages/result/index' })
}

function goRecords() {
  uni.navigateTo({ url: '/pages/records/index' })
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chat-panel {
  display: flex;
  min-height: 510px;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  padding: 14px;
  border-color: rgba(194, 224, 216, 0.9);
}

.message-list {
  height: 342px;
  padding: 2px 2px 8px;
}

.assistant-intro {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid rgba(202, 231, 224, 0.9);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #f4fffb 0%, #ecf9f5 100%);
}

.ai-avatar {
  display: flex;
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 850;
}

.intro-body {
  min-width: 0;
}

.intro-title {
  color: var(--color-primary-strong);
  font-size: 15px;
  font-weight: 820;
  line-height: 1.25;
}

.intro-copy {
  margin-top: 3px;
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.45;
}

.prompt-panel {
  max-width: 100%;
  margin: 2px 0 12px;
  padding: 2px 0 0;
  background: transparent;
}

.prompt-title {
  margin: 0 0 7px 2px;
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 760;
  line-height: 1.2;
}

.error-text {
  border-radius: var(--radius-md);
  background: #fff1ef;
  color: var(--color-danger);
  padding: 10px;
  font-size: 13px;
  line-height: 1.45;
}

.result-card {
  display: flex;
  gap: 10px;
  margin-top: 8px;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid #bfe7dc;
  background: #edf9f5;
}

.result-level {
  display: flex;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: #fff;
  font-size: 22px;
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

.result-body {
  min-width: 0;
  flex: 1;
}

.result-title {
  font-size: 14px;
  font-weight: 750;
}

.result-copy,
.round-text {
  margin-top: 3px;
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.45;
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 8px;
}

.secondary-button,
.reset-button {
  margin: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.88);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
}

.secondary-button::after,
.reset-button::after {
  border: 0;
}

.secondary-button {
  padding: 7px 10px;
  line-height: 1.2;
}

.reset-button {
  width: 100%;
  padding: 11px;
}
</style>
