<template>
  <scroll-view class="quick-strip" scroll-x :show-scrollbar="false" enable-flex>
    <view class="quick-track">
      <button
        v-for="item in items"
        :key="item.text"
        class="quick-chip"
        type="button"
        @click="$emit('select', item.prompt)"
      >
        <text class="quick-icon">{{ item.icon }}</text>
        <text class="quick-label">{{ item.text }}</text>
      </button>
    </view>
  </scroll-view>
</template>

<script setup lang="ts">
defineEmits<{
  select: [prompt: string]
}>()

const items = [
  { icon: '水', text: '漏水渗水', prompt: '卫生间天花板一直滴水，帮我判断严重吗' },
  { icon: '堵', text: '马桶堵塞', prompt: '马桶堵了水下不去，应该怎么办' },
  { icon: '冷', text: '空调不冷', prompt: '空调开了半小时还是不制冷' },
  { icon: '电', text: '电路跳闸', prompt: '家里插座发黑还跳闸了' },
  { icon: '锁', text: '门锁故障', prompt: '门锁打不开，人在门外' },
  { icon: '霉', text: '墙面发霉', prompt: '墙角发霉越来越大' },
  { icon: '热', text: '热水器', prompt: '热水器不出热水，帮我排查' },
  { icon: '气', text: '燃气灶', prompt: '燃气灶打不着火还有燃气味' },
  { icon: '味', text: '地漏反味', prompt: '卫生间地漏一直反味' },
  { icon: '窗', text: '门窗五金', prompt: '窗户关不严还有松动' }
]
</script>

<style scoped>
.quick-strip {
  width: 100%;
  white-space: nowrap;
}

.quick-track {
  display: inline-flex;
  width: max-content;
  gap: 8px;
  padding: 1px 2px 4px;
}

.quick-chip {
  display: flex;
  width: auto;
  min-width: auto;
  min-height: 34px;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 7px 10px;
  border: 1px solid #d5e8e2;
  border-radius: 999px;
  background: #ffffff;
  color: var(--color-text);
  font-size: 12px;
  line-height: 1.25;
  text-align: center;
  box-shadow: 0 6px 14px rgba(15, 88, 77, 0.05);
}

.quick-chip::after {
  border: 0;
}

.quick-icon {
  display: inline-flex;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-surface-soft);
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 750;
}

.quick-label {
  white-space: nowrap;
}
</style>
