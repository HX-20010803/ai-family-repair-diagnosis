<template>
  <view class="input-bar">
    <button class="tool-button disabled" type="button" disabled>图</button>
    <button class="tool-button disabled" type="button" disabled>音</button>
    <textarea
      v-model="draft"
      class="text-input"
      auto-height
      maxlength="500"
      placeholder="描述故障现象、位置、持续时间"
      :disabled="disabled"
      @confirm="submit"
    />
    <button class="send-button" type="button" :disabled="disabled || !draft.trim()" @click="submit">发送</button>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const draft = ref('')

function submit() {
  if (props.disabled || !draft.value.trim()) return
  emit('send', draft.value.trim())
  draft.value = ''
}
</script>

<style scoped>
.input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e5f1ed;
}

.tool-button,
.send-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  border-radius: var(--radius-md);
  font-size: 13px;
  line-height: 1;
}

.tool-button::after,
.send-button::after {
  border: 0;
}

.tool-button {
  width: 38px;
  height: 38px;
  padding: 0;
  border: 1px solid var(--color-border);
  background: #f6fbf9;
  color: var(--color-muted);
}

.tool-button.disabled {
  opacity: 0.55;
}

.text-input {
  min-height: 38px;
  max-height: 92px;
  flex: 1;
  padding: 10px 11px;
  border: 1px solid #cfe4dd;
  border-radius: 12px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.35;
}

.send-button {
  width: 56px;
  height: 38px;
  padding: 0;
  background: linear-gradient(135deg, #13a58e 0%, #0b7566 100%);
  color: #fff;
  font-weight: 700;
}

.send-button[disabled] {
  background: #a8bab5;
  color: #edf3f1;
}
</style>
