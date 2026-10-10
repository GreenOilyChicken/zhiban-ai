<template>
  <div class="policy-qa">
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
            <span>AI 政策智能问答</span>
            <el-tag type="info">基于最新政策文件</el-tag>
          </div>
        </template>

        <!-- 历史对话 -->
        <div class="chat-area" ref="chatArea">
          <div v-if="chatHistory.length === 0" class="empty-chat">
            <el-icon size="48" color="#c0c4cc"><ChatLineSquare /></el-icon>
            <p>请输入您关心的政策问题，AI 将为您解答</p>
          </div>
          <div
            v-for="(item, index) in chatHistory"
            :key="index"
            :class="['chat-item', item.role]"
          >
            <div class="chat-avatar">
              <el-icon v-if="item.role === 'user'" size="20"><User /></el-icon>
              <el-icon v-else size="20"><ChatDotRound /></el-icon>
            </div>
            <div class="chat-bubble">
              {{ item.content }}
            </div>
          </div>
          <div v-if="qaLoading" class="chat-item assistant">
            <div class="chat-avatar">
              <el-icon size="20"><ChatDotRound /></el-icon>
            </div>
            <div class="chat-bubble typing">
              AI 正在思考...
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            placeholder="输入政策相关问题，例如：高龄补贴如何申请？"
            @keydown.enter.ctrl="handleAsk"
          />
          <el-button
            type="primary"
            size="large"
            :loading="qaLoading"
            :disabled="!question.trim()"
            @click="handleAsk"
          >
            <el-icon class="el-icon--left"><Promotion /></el-icon>
            发送
          </el-button>
        </div>

        <!-- 配额展示 -->
        <div class="quota-info" v-if="quota">
          <QuotaBar :quota="quota" />
        </div>

        <!-- 快捷问题 -->
        <div class="quick-questions">
          <p class="quick-label">常见问题：</p>
          <el-tag
            v-for="q in quickQuestions"
            :key="q"
            class="quick-tag"
            @click="useQuickQuestion(q)"
          >
            {{ q }}
          </el-tag>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { askPolicy, getQuota } from '@/api/help'
import QuotaBar from '@/components/QuotaBar.vue'

const question = ref('')
const qaLoading = ref(false)
const chatHistory = ref([])
const chatArea = ref(null)
const quota = ref(null)

const quickQuestions = [
  '高龄补贴如何申请？',
  '老年人医保报销比例是多少？',
  '残疾人补贴政策有哪些？',
  '文旅消费券怎么领？'
]

onMounted(async () => {
  await loadQuota()
})

async function loadQuota() {
  try {
    const res = await getQuota()
    quota.value = res.data || null
  } catch {
    // 错误已由拦截器处理
  }
}

async function handleAsk() {
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  const userQuestion = question.value
  chatHistory.value.push({ role: 'user', content: userQuestion })
  question.value = ''
  qaLoading.value = true
  await scrollToBottom()

  try {
    const res = await askPolicy({ question: userQuestion })
    // 后端返回的是 string，不是 { answer: string }
    const answer = typeof res.data === 'string' ? res.data : (res.data?.answer || '暂无回答')
    chatHistory.value.push({ role: 'assistant', content: answer })
  } catch {
    chatHistory.value.push({ role: 'assistant', content: '抱歉，服务暂时不可用，请稍后重试。' })
  } finally {
    qaLoading.value = false
    await scrollToBottom()
    // 刷新配额
    await loadQuota()
  }
}

function useQuickQuestion(q) {
  question.value = q
}

async function scrollToBottom() {
  await nextTick()
  if (chatArea.value) {
    chatArea.value.scrollTop = chatArea.value.scrollHeight
  }
}
</script>

<style scoped>
.policy-qa {
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

.chat-area {
  height: 400px;
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
}

.empty-chat p {
  margin-top: 12px;
  font-size: 14px;
}

.chat-item {
  display: flex;
  margin-bottom: 16px;
  gap: 10px;
}

.chat-item.user {
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid #e4e7ed;
}

.chat-bubble {
  max-width: 70%;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.chat-item.user .chat-bubble {
  background: #409eff;
  color: #fff;
}

.chat-item.assistant .chat-bubble {
  background: #fff;
  color: #303133;
  border: 1px solid #e4e7ed;
}

.chat-bubble.typing {
  color: #909399;
  font-style: italic;
}

.input-area {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-area .el-button {
  height: 88px;
}

.quota-info {
  margin-top: 20px;
}

.quick-questions {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.quick-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.quick-tag {
  margin-right: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}
</style>
