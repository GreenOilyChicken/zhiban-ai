import axios from 'axios'
import { ElMessage } from 'element-plus'

const TOKEN_KEY = 'zhiban_ai_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 请求拦截器：附加 JWT
request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => {
    // 二进制响应（如 TTS 音频）直接返回
    if (response.config?.responseType === 'blob' || response.config?.responseType === 'arraybuffer') {
      return response
    }

    const res = response.data

    // 业务码非 200 时统一提示（附件一 §3.6 错误码体系）
    if (res && typeof res === 'object' && 'code' in res && res.code !== 200) {
      if (res.code === 401) {
        ElMessage.error(res.message || '登录已过期，请重新登录')
        removeToken()
        window.location.href = '/login'
      } else {
        ElMessage.error(res.message || '请求失败')
      }
      return Promise.reject(new Error(res.message || '请求失败'))
    }

    return res
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        removeToken()
        window.location.href = '/login'
      } else if (status === 403) {
        ElMessage.error('无权限访问')
      } else if (status === 404) {
        ElMessage.error('请求的资源不存在')
      } else if (status === 429) {
        // 附件一 §3.6：接口频率限制返回 429
        ElMessage.warning('请求过于频繁，请稍后再试')
      } else if (status >= 500) {
        ElMessage.error('服务器异常，请稍后重试')
      } else {
        const msg = error.response.data?.message || '请求失败'
        ElMessage.error(msg)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络异常')
    }
    return Promise.reject(error)
  }
)

export default request
