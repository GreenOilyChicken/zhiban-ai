import request from './index'
import { setToken } from './index'

// ==================== 认证（附件一 §3.1）====================

// 用户名密码登录
export function login(data) {
  return request.post('/auth/login', data).then((res) => {
    if (res.data?.token) {
      setToken(res.data.token)
    }
    return res
  })
}

// 注册
export function register(data) {
  return request.post('/auth/register', data)
}

// 游客登录：无需凭证，自动生成游客身份
export function guestLogin() {
  return request.post('/auth/guest-login').then((res) => {
    if (res.data?.token) {
      setToken(res.data.token)
    }
    return res
  })
}

// 发送短信验证码
export function sendSmsCode(phone) {
  return request.post('/auth/sms-code', { phone })
}

// 手机号 + 验证码登录
export function phoneLogin(data) {
  return request.post('/auth/phone-login', data).then((res) => {
    if (res.data?.token) {
      setToken(res.data.token)
    }
    return res
  })
}

// 刷新 Token
export function refreshToken() {
  return request.post('/auth/refresh').then((res) => {
    if (res.data?.token) {
      setToken(res.data.token)
    }
    return res
  })
}

// 当前用户信息
export function getUserInfo() {
  return request.get('/auth/user-info')
}

// ==================== 智能体（附件一 §3.4）====================

// 智能体列表
export function getAgentList() {
  return request.get('/agent/list')
}

// 获取指定智能体人设
export function getAgentPersona(agentType) {
  return request.get('/agent/persona', { params: { agentType } })
}

// 切换智能体
export function switchAgent(agentType) {
  return request.post(`/agent/switch/${agentType}`)
}

// ==================== 对话（附件一 §3.2）====================

// 发送消息
export function sendMessage(data) {
  return request.post('/chat/send', data)
}

// 会话列表
export function getChatSessions(params) {
  return request.get('/chat/sessions', { params })
}

// 历史消息
export function getChatHistory(params) {
  return request.get('/chat/history', { params })
}

// 新建会话
export function createChatSession(data) {
  return request.post('/chat/session', data)
}

// 删除会话
export function deleteChatSession(sessionId) {
  return request.delete(`/chat/session/${sessionId}`)
}

// ==================== 语音（附件一 §3.3）====================

// 发音人列表
export function getSpeakers() {
  return request.get('/voice/speakers')
}

// 切换发音人
export function switchSpeaker(speaker) {
  return request.post('/voice/speakers', null, { params: { speaker } })
}

// TTS 音频地址（直接用于 audio.src）
// 注意：audio.src / EventSource 无法设置 Authorization 请求头，
// 因此这里通过查询参数携带 JWT（后端 JwtAuthenticationFilter 已支持）。
export function ttsUrl(text, speaker) {
  const params = new URLSearchParams({ text })
  if (speaker) params.append('speaker', speaker)
  const token = getToken()
  if (token) params.append('token', token)
  return `/api/voice/tts?${params.toString()}`
}
