<template>
  <div class="home">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-inner">
        <div class="logo">
          <el-icon size="24" color="var(--zb-accent)"><ChatDotRound /></el-icon>
          <span class="logo-text">知伴AI</span>
        </div>
        <nav class="nav-links" aria-label="主导航">
          <el-button text @click="$router.push('/help')">帮助中心</el-button>
          <el-button text @click="$router.push('/login')">登录</el-button>
        </nav>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-inner">
        <p class="hero-eyebrow">双端智能体平台</p>
        <h1 class="hero-title">让政策触手可及，<br />让智慧惠及长者</h1>
        <p class="hero-subtitle">
          面向政务、银发经济与文旅项目的智能服务助手，
          把政策解读、办事指南与适老化陪伴装进一次对话。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push('/help')">
            进入帮助中心
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
          <el-button size="large" @click="goToTab('silver')">银发康养</el-button>
        </div>
      </div>
    </section>

    <!-- 三大方向卡片 -->
    <section class="directions" aria-label="服务方向">
      <div class="directions-grid">
        <article
          v-for="item in directions"
          :key="item.key"
          class="direction-card"
          :class="`is-${item.key}`"
          tabindex="0"
          role="button"
          :aria-label="`${item.title}：${item.desc}`"
          @click="goToTab(item.key)"
          @keydown.enter="goToTab(item.key)"
          @keydown.space.prevent="goToTab(item.key)"
        >
          <div class="card-icon">
            <el-icon size="32"><component :is="item.icon" /></el-icon>
          </div>
          <h3 class="card-title-text">{{ item.title }}</h3>
          <p class="card-desc">{{ item.desc }}</p>
          <span class="card-cta">
            {{ item.cta }}
            <el-icon><ArrowRight /></el-icon>
          </span>
        </article>
      </div>
    </section>

    <!-- 精选文章 + 系统公告（附件一 §4.1）-->
    <section class="home-content" aria-label="精选文章与公告">
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
import { ref, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { getArticles } from '@/api/help'
import { OfficeBuilding, FirstAidKit, Guide } from '@element-plus/icons-vue'

const router = useRouter()

const articles = ref([])
const loadingArticles = ref(false)

// 三大方向：图标全部使用真实存在的 Element Plus 图标
// 银发经济原用 <Senior /> —— 该图标在 @element-plus/icons-vue 中不存在，
// 故第二个卡片图标不渲染。改用 FirstAidKit（急救箱），契合"用药指导/康复计划"语义。
const directions = ref([
  {
    key: 'gov',
    title: '政务服务',
    desc: '政策解读、办事指南、智能问答，让政务服务更高效',
    cta: '查看政策',
    icon: markRaw(OfficeBuilding)
  },
  {
    key: 'silver',
    title: '银发经济',
    desc: '为老年群体提供贴心的政策帮助与生活指南服务',
    cta: '了解更多',
    icon: markRaw(FirstAidKit)
  },
  {
    key: 'tourism',
    title: '文旅项目',
    desc: '文旅资讯、景点推荐、活动指南，畅享文化之旅',
    cta: '探索文旅',
    icon: markRaw(Guide)
  }
])

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

/* —— 顶部导航 —— */
.header {
  background: var(--zb-surface);
  border-bottom: 1px solid var(--zb-border);
  box-shadow: var(--zb-shadow-xs);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: var(--zb-container);
  margin: 0 auto;
  padding: 0 var(--zb-space-6);
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--zb-space-2);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--zb-text);
  letter-spacing: 0.02em;
}

/* —— Hero：去紫蓝渐变，改沉静墨青底 + 微纹理 —— */
.hero {
  background:
    radial-gradient(900px 360px at 85% -10%, rgba(43, 106, 119, 0.10), transparent 60%),
    linear-gradient(180deg, #f0f4f5 0%, var(--zb-bg) 100%);
  border-bottom: 1px solid var(--zb-border);
  padding: var(--zb-space-12) var(--zb-space-6) var(--zb-space-10);
}

.hero-inner {
  max-width: 760px;
  margin: 0 auto;
  text-align: left;
}

.hero-eyebrow {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--zb-accent);
  margin-bottom: var(--zb-space-4);
}

.hero-title {
  font-size: clamp(30px, 4.2vw, 44px);
  line-height: 1.18;
  letter-spacing: -0.01em;
  font-weight: 700;
  color: var(--zb-text);
  margin-bottom: var(--zb-space-5);
  text-wrap: balance;
}

.hero-subtitle {
  font-size: 17px;
  line-height: 1.7;
  color: var(--zb-text-2);
  max-width: 60ch;
  margin: 0 0 var(--zb-space-8);
  text-wrap: pretty;
}

.hero-actions {
  display: flex;
  gap: var(--zb-space-3);
  flex-wrap: wrap;
}

/* —— 三大方向：去"三等分圆图标卡片"AI 味，改可点击整卡 + 左对齐 + cta 链接 —— */
.directions {
  max-width: var(--zb-container);
  margin: 0 auto;
  padding: var(--zb-space-10) var(--zb-space-6) var(--zb-space-12);
  width: 100%;
}

.directions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--zb-space-5);
}

@media (max-width: 900px) {
  .directions-grid {
    grid-template-columns: 1fr;
  }
}

.direction-card {
  display: flex;
  flex-direction: column;
  gap: var(--zb-space-3);
  padding: var(--zb-space-6);
  background: var(--zb-surface);
  border: 1px solid var(--zb-border);
  border-radius: var(--zb-radius-lg);
  box-shadow: var(--zb-shadow-sm);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  text-align: left;
  outline: none;
}

.direction-card:hover {
  border-color: var(--zb-accent-border);
  box-shadow: var(--zb-shadow-md);
  transform: translateY(-2px);
}

.direction-card:focus-visible {
  border-color: var(--zb-accent);
  box-shadow: 0 0 0 3px var(--zb-accent-soft);
}

.direction-card:active {
  transform: translateY(0);
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--zb-radius);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--zb-accent-soft);
  color: var(--zb-accent);
  margin-bottom: var(--zb-space-2);
}

.direction-card.is-gov .card-icon {
  background: var(--zb-accent-soft);
  color: var(--zb-accent);
}

.direction-card.is-silver .card-icon {
  background: var(--zb-success-soft);
  color: var(--zb-success);
}

.direction-card.is-tourism .card-icon {
  background: var(--zb-warning-soft);
  color: var(--zb-warning);
}

.card-title-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--zb-text);
  letter-spacing: 0.01em;
}

.card-desc {
  color: var(--zb-text-2);
  font-size: 14px;
  line-height: 1.65;
  flex-grow: 1;
}

.card-cta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 500;
  color: var(--zb-accent);
  margin-top: var(--zb-space-2);
  transition: gap 0.2s ease;
}

.direction-card:hover .card-cta {
  gap: 8px;
}

/* —— 精选文章 + 系统公告 —— */
.home-content {
  max-width: var(--zb-container);
  margin: 0 auto;
  padding: 0 var(--zb-space-6) var(--zb-space-12);
  width: 100%;
}

.content-card {
  border-radius: var(--zb-radius-lg);
  border-color: var(--zb-border);
  margin-bottom: var(--zb-space-6);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  display: inline-flex;
  align-items: center;
  gap: var(--zb-space-2);
  font-size: 16px;
  font-weight: 600;
  color: var(--zb-text);
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
  gap: var(--zb-space-3);
  padding: var(--zb-space-3) 2px;
  border-bottom: 1px solid var(--zb-border);
  cursor: pointer;
  transition: color 0.2s ease;
}

.article-item:last-child {
  border-bottom: none;
}

.article-item:hover .article-title {
  color: var(--zb-accent);
}

.article-title {
  font-size: 15px;
  color: var(--zb-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notice-item {
  display: flex;
  align-items: flex-start;
  gap: var(--zb-space-2);
  padding: 10px 0;
  font-size: 14px;
  color: var(--zb-text-2);
  line-height: 1.6;
  border-bottom: 1px dashed var(--zb-border);
}

.notice-item:last-child {
  border-bottom: none;
}

/* —— Footer —— */
.footer {
  text-align: center;
  padding: var(--zb-space-6);
  color: var(--zb-text-3);
  font-size: 14px;
  background: var(--zb-surface);
  border-top: 1px solid var(--zb-border);
  margin-top: auto;
}
</style>
