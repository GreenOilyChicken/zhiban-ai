<template>
  <div class="home">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-inner">
        <div class="logo">
          <el-icon size="28" color="#409EFF"><ChatDotRound /></el-icon>
          <span class="logo-text">知伴AI</span>
        </div>
        <nav class="nav-links">
          <el-button text @click="$router.push('/help')">帮助中心</el-button>
          <el-button text @click="$router.push('/login')">登录</el-button>
        </nav>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">知伴AI双端智能体平台</h1>
        <p class="hero-subtitle">
          面向政务、银发经济与文旅项目的智能服务助手<br />
          让政策触手可及，让智慧惠及长者
        </p>
        <el-button type="primary" size="large" @click="$router.push('/help')">
          进入帮助中心
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </section>

    <!-- 三大方向卡片 -->
    <section class="directions">
      <el-row :gutter="24" justify="center">
        <el-col :xs="24" :sm="8">
          <el-card class="direction-card" shadow="hover" @click="goToTab('gov')">
            <div class="card-icon gov">
              <el-icon size="40"><OfficeBuilding /></el-icon>
            </div>
            <h3>政务服务</h3>
            <p>政策解读、办事指南、智能问答，让政务服务更高效</p>
            <el-button type="primary" text>查看政策</el-button>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card class="direction-card" shadow="hover" @click="goToTab('silver')">
            <div class="card-icon silver">
              <el-icon size="40"><Senior /></el-icon>
            </div>
            <h3>银发经济</h3>
            <p>为老年群体提供贴心的政策帮助与生活指南服务</p>
            <el-button type="success" text>了解更多</el-button>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card class="direction-card" shadow="hover" @click="goToTab('tourism')">
            <div class="card-icon tourism">
              <el-icon size="40"><Guide /></el-icon>
            </div>
            <h3>文旅项目</h3>
            <p>文旅资讯、景点推荐、活动指南，畅享文化之旅</p>
            <el-button type="warning" text>探索文旅</el-button>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <!-- 精选文章 + 系统公告（附件一 §4.1）-->
    <section class="home-content">
      <el-row :gutter="24">
        <el-col :xs="24" :md="16">
          <el-card shadow="never" class="content-card">
            <template #header>
              <div class="card-head">
                <span class="card-title">
                  <el-icon><Document /></el-icon> 精选文章
                </span>
                <el-button text type="primary" @click="$router.push('/help/articles')">
                  查看全部 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
                </el-button>
              </div>
            </template>

            <div v-loading="loadingArticles">
              <el-empty v-if="!articles.length" description="暂无文章" :image-size="80" />
              <ul v-else class="article-list">
                <li
                  v-for="item in articles"
                  :key="item.id"
                  class="article-item"
                  @click="$router.push(`/help/article/${item.id}`)"
                >
                  <span class="article-title">{{ item.title }}</span>
                  <el-tag v-if="item.category" size="small" type="info">{{ item.category }}</el-tag>
                </li>
              </ul>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="8">
          <el-card shadow="never" class="content-card">
            <template #header>
              <span class="card-title">
                <el-icon><Bell /></el-icon> 系统公告
              </span>
            </template>
            <ul class="notice-list">
              <li v-for="(n, i) in notices" :key="i" class="notice-item">
                <el-tag size="small" :type="n.type">{{ n.tag }}</el-tag>
                <span>{{ n.text }}</span>
              </li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <p>知伴AI © 2026 · 双端智能体平台 · 技术驱动民生服务</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getArticles } from '@/api/help'

const router = useRouter()

const articles = ref([])
const loadingArticles = ref(false)

// 系统公告（当前为静态配置，可由管理端后续接入）
const notices = ref([
  { tag: '服务', type: 'primary', text: '银发康养智能体已上线，支持用药指导与康复计划' },
  { tag: '政策', type: 'success', text: '政策问答支持来源追溯，回答均标注政策文件' },
  { tag: '提示', type: 'warning', text: '健康类建议仅供参考，请遵医嘱' }
])

function goToTab(tab) {
  router.push({ path: '/help', query: { tab } })
}

async function loadArticles() {
  loadingArticles.value = true
  try {
    const res = await getArticles({ page: 1, size: 6 })
    articles.value = res.data?.records || []
  } catch {
    // 错误已由拦截器处理
  } finally {
    loadingArticles.value = false
  }
}

onMounted(loadArticles)
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
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
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.hero {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 80px 24px;
  text-align: center;
}

.hero-content {
  max-width: 700px;
  margin: 0 auto;
}

.hero-title {
  font-size: 36px;
  color: #fff;
  margin-bottom: 16px;
}

.hero-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.8;
  margin-bottom: 32px;
}

.directions {
  max-width: 1200px;
  margin: -40px auto 0;
  padding: 0 24px 60px;
  position: relative;
  z-index: 10;
}

.direction-card {
  text-align: center;
  padding: 20px 16px;
  cursor: pointer;
  transition: transform 0.3s;
  border-radius: 12px;
  margin-bottom: 24px;
}

.direction-card:hover {
  transform: translateY(-4px);
}

.card-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-icon.gov {
  background: #ecf5ff;
  color: #409eff;
}

.card-icon.silver {
  background: #f0f9eb;
  color: #67c23a;
}

.card-icon.tourism {
  background: #fdf6ec;
  color: #e6a23c;
}

.direction-card h3 {
  font-size: 20px;
  margin-bottom: 8px;
}

.direction-card p {
  color: #909399;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.footer {
  text-align: center;
  padding: 24px;
  color: #909399;
  font-size: 14px;
  background: #fff;
  margin-top: auto;
}

/* 精选文章 + 系统公告 */
.home-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 60px;
  width: 100%;
}

.content-card {
  border-radius: 12px;
  margin-bottom: 24px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.article-list,
.notice-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.article-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: color 0.2s;
}

.article-item:last-child {
  border-bottom: none;
}

.article-item:hover .article-title {
  color: #409eff;
}

.article-title {
  font-size: 15px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notice-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  border-bottom: 1px dashed #f0f0f0;
}

.notice-item:last-child {
  border-bottom: none;
}
</style>
