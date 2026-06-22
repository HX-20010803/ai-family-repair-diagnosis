<template>
  <view class="message-row" :class="message.role">
    <view class="bubble" :class="[message.role, message.kind]">
      <text>{{ message.text }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { ChatMessage } from '../../../types/diagnosis'

defineProps<{
  message: ChatMessage
}>()
</script>

<style scoped>
.message-row {
  display: flex;
  margin-bottom: 11px;
}

.message-row.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 84%;
  white-space: pre-line;
  border-radius: 14px;
  padding: 11px 13px;
  font-size: 14px;
  line-height: 1.55;
}

.bubble.assistant {
  border: 1px solid #d9ece6;
  background: #ffffff;
  color: var(--color-text);
  box-shadow: 0 8px 20px rgba(18, 66, 55, 0.06);
}

.bubble.user {
  background: linear-gradient(135deg, #0f8a77 0%, #087062 100%);
  color: #fff;
  box-shadow: 0 10px 20px rgba(15, 138, 119, 0.2);
}

.bubble.safety {
  border-color: #f0b7ad;
  background: #fff1ef;
  color: var(--color-danger);
  font-weight: 650;
}

.bubble.result {
  border-color: #9fd5c9;
  background: #edf9f5;
  color: var(--color-primary-strong);
  font-weight: 650;
}
</style>
