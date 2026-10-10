<template>
  <div class="quota-bar" v-if="quota">
    <div class="quota-text">
      <span>{{ quota.usedQuota ?? 0 }} / {{ quota.totalQuota ?? 0 }}</span>
      <span class="quota-remaining">剩余 {{ quota.remainingQuota ?? 0 }}</span>
    </div>
    <el-progress
      :percentage="percentage"
      :color="progressColor"
      :stroke-width="20"
      :text-inside="true"
      :format="formatText"
    />
  </div>
  <div v-else class="quota-bar-empty">
    <span>暂无配额数据</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  quota: {
    type: Object,
    default: null
  }
})

// 防止除以零：totalQuota 为 0 或 null 时返回 0
const percentage = computed(() => {
  const total = props.quota?.totalQuota
  const used = props.quota?.usedQuota
  if (!total || total === 0) return 0
  const pct = Math.round((used / total) * 100)
  return Math.min(pct, 100)
})

const progressColor = computed(() => {
  if (percentage.value >= 90) return '#f56c6c'
  if (percentage.value >= 70) return '#e6a23c'
  return '#67c23a'
})

function formatText() {
  return `${percentage.value}%`
}
</script>

<style scoped>
.quota-bar {
  width: 100%;
}

.quota-text {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}

.quota-remaining {
  color: #909399;
}

.quota-bar-empty {
  text-align: center;
  color: #c0c4cc;
  padding: 12px;
}
</style>
