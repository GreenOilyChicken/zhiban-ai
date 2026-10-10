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

    <!-- Footer -->
    <footer class="footer">
      <p>知伴AI © 2026 · 双端智能体平台 · 技术驱动民生服务</p>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goToTab(tab) {
  router.push({ path: '/help', query: { tab } })
}
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
</style>
