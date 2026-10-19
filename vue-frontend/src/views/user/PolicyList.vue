<template>
  <div class="policy-list">
    <header class="header">
      <div class="header-inner">
        <div class="logo" @click="$router.push('/help')">
          <el-icon size="24" color="#409EFF"><Back /></el-icon>
          <span class="logo-text">返回帮助中心</span>
        </div>
      </div>
    </header>

    <div class="content">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>政策文件列表</span>
            <div class="filter-area">
              <el-select
                v-model="selectedCategory"
                placeholder="选择分类"
                clearable
                style="width: 160px"
                @change="loadPolicies"
              >
                <el-option
                  v-for="cat in categories"
                  :key="cat"
                  :label="cat"
                  :value="cat"
                />
              </el-select>
              <el-input
                v-model="searchKeyword"
                placeholder="搜索政策标题"
                clearable
                style="width: 200px; margin-left: 12px"
                @clear="loadPolicies"
                @keyup.enter="loadPolicies"
              />
              <el-button type="primary" style="margin-left: 12px" @click="loadPolicies">搜索</el-button>
            </div>
          </div>
        </template>

        <el-table :data="policies" v-loading="loading" stripe>
          <el-table-column prop="title" label="政策标题" min-width="240" show-overflow-tooltip />
          <el-table-column prop="documentNumber" label="文号" width="160" />
          <el-table-column prop="issuingAuthority" label="发文机关" width="140" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="publishDate" label="发布日期" width="120" />
          <el-table-column prop="effectiveDate" label="生效日期" width="120" />
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="viewDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="loadPolicies"
          />
        </div>
      </el-card>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="政策详情" width="70%">
      <div v-if="currentDetail" class="policy-detail">
        <h2>{{ currentDetail.title }}</h2>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文号">{{ currentDetail.documentNumber }}</el-descriptions-item>
          <el-descriptions-item label="发文机关">{{ currentDetail.issuingAuthority }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ currentDetail.category }}</el-descriptions-item>
          <el-descriptions-item label="发布日期">{{ currentDetail.publishDate }}</el-descriptions-item>
          <el-descriptions-item label="生效日期">{{ currentDetail.effectiveDate }}</el-descriptions-item>
          <el-descriptions-item label="有效期至">{{ currentDetail.expiryDate || '长期' }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <div class="policy-body" v-html="currentDetail.content"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getGovPolicies, getCategories } from '@/api/help'

const route = useRoute()

const policies = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const categories = ref([])
const selectedCategory = ref('')
const searchKeyword = ref('')

const detailVisible = ref(false)
const currentDetail = ref(null)

onMounted(async () => {
  await loadCategories()
  await loadPolicies()
  // 如果 URL 带了 id 参数，自动打开详情
  if (route.query.id) {
    const target = policies.value.find((p) => String(p.id) === String(route.query.id))
    if (target) {
      viewDetail(target)
    }
  }
})

async function loadCategories() {
  try {
    const res = await getCategories()
    categories.value = res.data || []
  } catch {
    // 错误已由拦截器处理
  }
}

async function loadPolicies() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value
    }
    if (selectedCategory.value) params.category = selectedCategory.value
    if (searchKeyword.value) params.keyword = searchKeyword.value

    const res = await getGovPolicies(params)
    policies.value = res.data?.records || res.data?.content || []
    total.value = res.data?.totalElements || res.data?.total || 0
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function viewDetail(row) {
  currentDetail.value = row
  detailVisible.value = true
}
</script>

<style scoped>
.policy-list {
  min-height: 100vh;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
}

.filter-area {
  display: flex;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.policy-detail h2 {
  margin-bottom: 20px;
  font-size: 22px;
}

.policy-body {
  line-height: 1.8;
  font-size: 15px;
  color: #606266;
  white-space: pre-wrap;
}
</style>
