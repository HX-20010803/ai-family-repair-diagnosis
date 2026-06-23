<template>
  <view class="page-shell">
    <view class="app-header">
      <view>
        <h1 class="app-title">维修记录</h1>
        <p class="app-subtitle">点击记录可补充实际维修方式、费用和处理结果</p>
      </view>
    </view>

    <view v-if="records.loading" class="panel empty-records">
      <view class="card-title">正在加载记录</view>
      <view class="card-copy">请稍候。</view>
    </view>

    <view v-else-if="records.items.length === 0" class="panel empty-records">
      <view class="record-icon">记</view>
      <view class="card-title">暂无历史记录</view>
      <view class="card-copy">完成诊断后可以保存为维修记录，方便后续追踪费用和处理结果。</view>
    </view>

    <view v-else class="record-list">
      <view
        v-for="item in records.items"
        :key="item.id"
        class="panel record-card"
        @click="openDetail(item.id)"
      >
        <view class="card-head">
          <view class="card-title">{{ secondaryLabel(item.secondary_category) }}</view>
          <view v-if="item.urgency_level" class="urg-tag" :class="`level-${item.urgency_level}`">{{ item.urgency_level }}</view>
        </view>
        <view class="card-copy">位置：{{ item.house_area || '未填写' }}</view>
        <view class="card-foot">
          <view class="card-copy">{{ formatTime(item.created_at) }}</view>
          <view v-if="item.actual_cost != null" class="card-cost">¥{{ item.actual_cost }}</view>
          <view v-else-if="item.is_resolved === true" class="card-tag">已解决</view>
          <view v-else-if="item.is_resolved === false" class="card-tag muted-tag">未解决</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRecordsStore } from '../../stores/records'
import { secondaryLabel } from '../../services/records'

const records = useRecordsStore()

function openDetail(id: string) {
  uni.navigateTo({ url: `/pages/records/detail?id=${id}` })
}

function formatTime(value: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

onMounted(() => {
  records.fetchList()
})
</script>

<style scoped>
.record-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-card {
  padding: 14px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}

.card-cost {
  color: var(--color-primary-strong);
  font-size: 13px;
  font-weight: 700;
}

.card-tag {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-soft);
  color: var(--color-success);
  font-size: 12px;
  font-weight: 700;
}

.muted-tag {
  color: var(--color-muted);
}

.empty-records {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 18px;
  text-align: center;
}

.record-icon {
  display: flex;
  width: 52px;
  height: 52px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-surface-soft);
  color: var(--color-primary);
  font-size: 20px;
  font-weight: 800;
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
</style>
