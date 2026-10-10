<template>
  <div class="help-center">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-inner">
        <div class="logo" @click="$router.push('/')">
          <el-icon size="24" color="#409EFF"><ChatDotRound /></el-icon>
          <span class="logo-text">知伴AI · 帮助中心</span>
        </div>
        <nav class="nav-links">
          <el-button text @click="$router.push('/')">首页</el-button>
          <el-button text @click="$router.push('/login')">管理后台</el-button>
        </nav>
      </div>
    </header>

    <!-- Tab 标签页（懒加载） -->
    <div class="content">
      <el-tabs v-model="activeTab" @tab-change="onTabChange" class="main-tabs">
        <!-- 政务服务 -->
        <el-tab-pane label="政务服务" name="gov">
          <div class="tab-content" v-if="loadedTabs.gov">
            <el-row :gutter="20">
              <el-col :xs="24" :md="16">
                <el-card shadow="never">
                  <template #header>
                    <div class="card-header">
                      <span>政策文件列表</span>
                      <el-button type="primary" size="small" @click="$router.push('/help/policies')">
                        查看全部
                      </el-button>
                    </div>
                  </template>
                  <el-table :data="policies" v-loading="loading.gov" stripe>
                    <el-table-column prop="title" label="政策标题" min-width="200" />
                    <el-table-column prop="documentNumber" label="文号" width="140" />
                    <el-table-column prop="issuingAuthority" label="发文机关" width="120" />
                    <el-table-column prop="publishDate" label="发布日期" width="120" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-card shadow="never">
                  <template #header>
                    <span>AI 政策问答</span>
                  </template>
                  <p class="qa-hint">输入您关心的政策问题，AI 为您解答</p>
                  <el-input
                    v-model="qaQuestion"
                    type="textarea"
                    :rows="3"
                    placeholder="例如：高龄补贴如何申请？"
                  />
                  <el-button
                    type="primary"
                    class="qa-btn"
                    :loading="qaLoading"
                    @click="handleAsk"
                  >
                    提问
                  </el-button>
                  <el-alert
                    v-if="qaAnswer"
                    :title="qaAnswer"
                    type="info"
                    :closable="false"
                    show-icon
                    class="qa-answer"
                  />
                </el-card>
              </el-col>
            </el-row>
          </div>
          <div v-else class="tab-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
        </el-tab-pane>

        <!-- 银发经济 -->
        <el-tab-pane label="银发经济" name="silver">
          <div class="tab-content" v-if="loadedTabs.silver">
            <el-card shadow="never">
              <template #header>
                <span>适老化政策与服务指南</span>
              </template>
              <el-table :data="silverPolicies" v-loading="loading.silver" stripe>
                <el-table-column prop="title" label="政策标题" min-width="200" />
                <el-table-column prop="documentNumber" label="文号" width="140" />
                <el-table-column prop="issuingAuthority" label="发文机关" width="120" />
                <el-table-column prop="publishDate" label="发布日期" width="120" />
                <el-table-column label="操作" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button text type="primary" @click="viewPolicyDetail(row)">详情</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 配额展示 -->
            <el-card shadow="never" class="quota-card">
              <template #header>
                <span>本月AI问答配额</span>
              </template>
              <QuotaBar :quota="quota" />
            </el-card>
          </div>
          <div v-else class="tab-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
        </el-tab-pane>

        <!-- 文旅项目 -->
        <el-tab-pane label="文旅项目" name="tourism">
          <div class="tab-content" v-if="loadedTabs.tourism">
            <el-row :gutter="20">
              <el-col :xs="24" :md="16">
                <el-card shadow="never">
                  <template #header>
                    <div class="card-header">
                      <span>文旅资讯与帮助文章</span>
                      <el-button type="primary" size="small" @click="$router.push('/help/articles')">
                        查看全部
                      </el-button>
                    </div>
                  </template>
                  <el-table :data="articles" v-loading="loading.tourism" stripe>
                    <el-table-column prop="title" label="文章标题" min-width="200" />
                    <el-table-column prop="category" label="分类" width="120" />
                    <el-table-column prop="updatedAt" label="更新时间" width="180" />
                    <el-table-column label="操作" width="80" fixed="right">
                      <template #default="{ row }">
                        <el-button text type="primary" @click="$router.push(`/help/article/${row.id}`)">阅读</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-card shadow="never">
                  <template #header>
                    <span>常见问题</span>
                  </template>
                  <el-collapse v-model="faqActive" v-loading="loading.faq">
                    <el-collapse-item
                      v-for="item in faqList"
                      :key="item.id"
                      :title="item.question"
                      :name="item.id"
                    >
                      <p>{{ item.answer }}</p>
                    </el-collapse-item>
                  </el-collapse>
                  <el-empty v-if="!loading.faq && faqList.length === 0" description="暂无FAQ" />
                </el-card>
              </el-col>
            </el-row>
          </div>
          <div v-else class="tab-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getGovPolicies,
  getArticles,
  getFaq,
  askPolicy,
  getQuota
} from '@/api/help'
import QuotaBar from '@/components/QuotaBar.vue'

const route = useRoute()
const router = useRouter()

// Tab 状态（懒加载：只在首次切换时加载数据）
const activeTab = ref('gov')
const loadedTabs = reactive({
  gov: false,
  silver: false,
  tourism: false
})

// 各 Tab 数据
const policies = ref([])
const silverPolicies = ref([])
const articles = ref([])
const faqList = ref([])
const quota = ref(null)

// 加载状态
const loading = reactive({
  gov: false,
  silver: false,
  tourism: false,
  faq: false
})

// AI 问答
const qaQuestion = ref('')
const qaAnswer = ref('')
const qaLoading = ref(false)
const faqActive = ref([])

onMounted(() => {
  const tab = route.query.tab
  if (tab && ['gov', 'silver', 'tourism'].includes(tab)) {
    activeTab.value = tab
  }
  loadTabData(activeTab.value)
})

function onTabChange(tabName) {
  loadTabData(tabName)
}

async function loadTabData(tabName) {
  if (loadedTabs[tabName]) return
  loadedTabs[tabName] = true

  if (tabName === 'gov') {
    await loadGovPolicies()
  } else if (tabName === 'silver') {
    await loadSilverPolicies()
    await loadQuota()
  } else if (tabName === 'tourism') {
    await loadArticles()
    await loadFaq()
  }
}

async function loadGovPolicies() {
  loading.gov = true
  try {
    const res = await getGovPolicies({ page: 0, size: 5 })
    policies.value = res.data?.content || res.data || []
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.gov = false
  }
}

async function loadSilverPolicies() {
  loading.silver = true
  try {
    const res = await getGovPolicies({ page: 0, size: 10, category: '银发经济' })
    silverPolicies.value = res.data?.content || res.data || []
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.silver = false
  }
}

async function loadArticles() {
  loading.tourism = true
  try {
    const res = await getArticles({ page: 0, size: 5 })
    articles.value = res.data?.content || res.data || []
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.tourism = false
  }
}

async function loadFaq() {
  loading.faq = true
  try {
    const res = await getFaq()
    faqList.value = res.data || []
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.faq = false
  }
}

async function loadQuota() {
  try {
    const res = await getQuota()
    quota.value = res.data || null
  } catch {
    // 错误已由拦截器处理
  }
}

async function handleAsk() {
  if (!qaQuestion.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  qaLoading.value = true
  qaAnswer.value = ''
  try {
    const res = await askPolicy({ question: qaQuestion.value })
    // 后端返回的是 string，不是 { answer: string }
    qaAnswer.value = typeof res.data === 'string' ? res.data : (res.data?.answer || '暂无回答')
  } catch {
    // 错误已由拦截器处理
  } finally {
    qaLoading.value = false
  }
}

function viewPolicyDetail(row) {
  router.push({ path: '/help/policies', query: { id: row.id } })
}
</script>

<style scoped>
.help-center {
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
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.main-tabs {
  background: #fff;
  border-radius: 8px;
  padding: 0 24px 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qa-hint {
  color: #909399;
  font-size: 14px;
  margin-bottom: 12px;
}

.qa-btn {
  margin-top: 12px;
  width: 100%;
}

.qa-answer {
  margin-top: 16px;
}

.quota-card {
  margin-top: 20px;
}

.tab-placeholder {
  padding: 20px 0;
}
</style>
