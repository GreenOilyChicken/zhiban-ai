<template>
  <div class="admin-quota">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>配额管理</span>
          <el-button type="primary" @click="loadQuota" :loading="loading">
            <el-icon class="el-icon--left"><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <div v-loading="loading">
        <el-descriptions v-if="quota" :column="1" border>
          <el-descriptions-item label="总配额">
            <span class="quota-value">{{ quota.totalQuota ?? 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="已使用">
            <span class="quota-value">{{ quota.usedQuota ?? 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="剩余配额">
            <span class="quota-value" :class="{ 'quota-warn': remainingPct < 20 }">
              {{ quota.remainingQuota ?? 0 }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="使用率">
            <QuotaBar :quota="quota" />
          </el-descriptions-item>
        </el-descriptions>

        <el-empty v-if="!quota && !loading" description="暂无配额数据" />
      </div>
    </el-card>

    <el-card shadow="never" class="stat-cards" v-if="quota">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="8">
          <el-statistic title="总配额" :value="quota.totalQuota ?? 0">
            <template #prefix>
              <el-icon color="#409eff"><DataLine /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-statistic title="已使用" :value="quota.usedQuota ?? 0">
            <template #prefix>
              <el-icon color="#e6a23c"><Warning /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-statistic title="剩余配额" :value="quota.remainingQuota ?? 0">
            <template #prefix>
              <el-icon color="#67c23a"><CircleCheck /></el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getQuota } from '@/api/help'
import QuotaBar from '@/components/QuotaBar.vue'

const quota = ref(null)
const loading = ref(false)

const remainingPct = computed(() => {
  if (!quota.value || !quota.value.totalQuota || quota.value.totalQuota === 0) return 0
  return Math.round((quota.value.remainingQuota / quota.value.totalQuota) * 100)
})

onMounted(() => {
  loadQuota()
})

async function loadQuota() {
  loading.value = true
  try {
    const res = await getQuota()
    quota.value = res.data || null
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quota-value {
  font-size: 20px;
  font-weight: 700;
}

.quota-warn {
  color: #f56c6c;
}

.stat-cards {
  margin-top: 20px;
}
</style>
