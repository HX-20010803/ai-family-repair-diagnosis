<template>
  <view class="page-shell">
    <view class="app-header">
      <view>
        <h1 class="app-title">维修记录</h1>
        <p class="app-subtitle">第 1 版先保存诊断结果，后续支持费用回填和复发追踪</p>
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
      <view v-for="item in records.items" :key="item.id" class="panel record-card">
        <view class="card-title">维修记录</view>
        <view class="card-copy">诊断结果：{{ item.diagnosis_result_id }}</view>
        <view class="card-copy">位置：{{ item.house_area || '未填写' }}</view>
        <view class="card-copy">创建时间：{{ item.created_at || '-' }}</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRecordsStore } from '../../stores/records'

const records = useRecordsStore()

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
  margin-top: 14px;
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
