<template>
  <view class="safety-banner">
    <view class="safety-mark">!</view>
    <view>
      <view class="safety-title">安全优先</view>
      <view class="safety-copy">燃气味、冒烟、漏电、严重漏水靠近电源时，先停止使用并联系专业人员。</view>
    </view>
  </view>
</template>

<style scoped>
.safety-banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 11px 12px;
  border: 1px solid #f4d6a8;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #fff9ef 0%, #fff4de 100%);
  color: #5b3b08;
  box-shadow: 0 12px 28px rgba(177, 109, 25, 0.08);
}

.safety-mark {
  display: flex;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--color-warning);
  color: #fff;
  font-size: 14px;
  font-weight: 800;
}

.safety-title {
  font-size: 14px;
  font-weight: 750;
  line-height: 1.25;
}

.safety-copy {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.45;
}
</style>
