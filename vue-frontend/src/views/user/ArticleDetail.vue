<template>
  <div class="article-detail">
    <header class="header">
      <div class="header-inner">
        <div class="logo" @click="$router.back()">
          <el-icon size="24" color="#409EFF"><Back /></el-icon>
          <span class="logo-text">返回列表</span>
        </div>
      </div>
    </header>

    <div class="content">
      <el-card shadow="never" v-loading="loading">
        <div v-if="article" class="article-body">
          <h1 class="title">{{ article.title }}</h1>
          <div class="meta">
            <el-tag size="small" type="info" v-if="article.category">{{ article.category }}</el-tag>
            <span class="meta-item">作者：{{ article.author || '管理员' }}</span>
            <span class="meta-item">更新时间：{{ article.updatedAt || article.createdAt }}</span>
          </div>
          <el-divider />
          <div class="content-html" v-html="article.content"></div>
        </div>
        <el-empty v-if="!article && !loading" description="文章不存在或已删除" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getArticleDetail } from '@/api/help'

const route = useRoute()
const article = ref(null)
const loading = ref(false)

onMounted(() => {
  loadArticle()
})

async function loadArticle() {
  const id = route.params.id
  if (!id) return
  loading.value = true
  try {
    const res = await getArticleDetail(id)
    article.value = res.data || null
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.article-detail {
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
  max-width: 800px;
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
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

.article-body {
  padding: 8px 4px;
}

.title {
  font-size: 26px;
  margin-bottom: 16px;
  line-height: 1.4;
}

.meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: #909399;
}

.meta-item {
  color: #909399;
}

.content-html {
  line-height: 1.8;
  font-size: 15px;
  color: #606266;
}

.content-html :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 12px 0;
}

.content-html :deep(p) {
  margin-bottom: 12px;
}
</style>
