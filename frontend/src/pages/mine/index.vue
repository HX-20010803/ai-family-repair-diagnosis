<template>
  <view class="page-shell">
    <view class="app-header">
      <view>
        <h1 class="app-title">我的</h1>
        <p class="app-subtitle">H5 阶段使用本地匿名标识，清缓存后可能丢失历史归属</p>
      </view>
    </view>

    <view class="panel mine-card">
      <view class="card-title">游客模式</view>
      <view class="card-copy">手机号登录、微信 openid 和记录合并将在后续版本接入。</view>
    </view>
  </view>
</template>

<style scoped>
.mine-card {
  padding: 18px;
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
