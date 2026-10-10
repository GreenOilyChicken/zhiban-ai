<template>
  <div class="article-list">
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
            <span>帮助文章</span>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索文章"
              clearable
              style="width: 240px"
              @clear="loadArticles"
              @keyup.enter="loadArticles"
            >
              <template #append>
                <el-button :icon="Search" @click="loadArticles" />
              </template>
            </el-input>
          </div>
        </template>

        <div v-loading="loading">
          <div v-if="articles.length === 0 && !loading" class="empty">
            <el-empty description="暂无文章" />
          </div>
          <div
            v-for="article in articles"
            :key="article.id"
            class="article-item"
            @click="$router.push(`/help/article/${article.id}`)"
          >
            <div class="article-info">
              <h3 class="article-title">{{ article.title }}</h3>
              <div class="article-meta">
                <el-tag size="small" type="info" v-if="article.category">{{ article.category }}</el-tag>
                <span class="meta-date">{{ article.updatedAt || article.createdAt }}</span>
              </div>
              <p class="article-summary">{{ stripHtml(article.content) }}</p>
            </div>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>

        <div class="pagination" v-if="total > 0">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="loadArticles"
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getArticles } from '@/api/help'

const articles = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchKeyword = ref('')

onMounted(() => {
  loadArticles()
})

async function loadArticles() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value - 1,
      size: pageSize.value
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value

    const res = await getArticles(params)
    articles.value = res.data?.content || res.data?.records || []
    total.value = res.data?.totalElements || res.data?.total || 0
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function stripHtml(html) {
  if (!html) return ''
  return html.replace(/<[^>]+>/g, '').substring(0, 100) + '...'
}
</script>

<style scoped>
.article-list {
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
  max-width: 900px;
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
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty {
  padding: 40px 0;
}

.article-item {
  display: flex;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;
}

.article-item:hover {
  background: #f5f7fa;
}

.article-info {
  flex: 1;
}

.article-title {
  font-size: 16px;
  margin-bottom: 8px;
  color: #303133;
}

.article-item:hover .article-title {
  color: #409eff;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.meta-date {
  font-size: 12px;
  color: #909399;
}

.article-summary {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.arrow-icon {
  color: #c0c4cc;
  margin-left: 12px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
