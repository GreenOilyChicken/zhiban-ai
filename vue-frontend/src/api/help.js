import request from './index'

// ==================== 文章相关 ====================

// 获取帮助文章列表（用户端）
export function getArticles(params) {
  return request.get('/help/articles', { params })
}

// 获取帮助文章详情（注意：单数 article，不是 articles）
export function getArticleDetail(id) {
  return request.get(`/help/article/${id}`)
}

// 创建文章（管理端）
export function createArticle(data) {
  return request.post('/admin/help/article', data)
}

// 更新文章（管理端）
export function updateArticle(id, data) {
  return request.put(`/admin/help/article/${id}`, data)
}

// 删除文章（管理端）
export function deleteArticle(id) {
  return request.delete(`/admin/help/article/${id}`)
}

// ==================== FAQ ====================

export function getFaq() {
  return request.get('/help/faq')
}

// ==================== 政策相关 ====================

// 获取政策列表（注意：gov-policy 单数，不是 gov-policies）
export function getGovPolicies(params) {
  return request.get('/help/gov-policy', { params })
}

// 创建政策（管理端）
export function createGovPolicy(data) {
  return request.post('/admin/help/gov-policy', data)
}

// 更新政策（管理端）
export function updateGovPolicy(id, data) {
  return request.put(`/admin/help/gov-policy/${id}`, data)
}

// 删除政策（管理端）
export function deleteGovPolicy(id) {
  return request.delete(`/admin/help/gov-policy/${id}`)
}

// AI 政策问答（响应是 string，不是 { answer: string }）
export function askPolicy(data) {
  return request.post('/help/gov-policy/ask', data)
}

// ==================== 配额 ====================

// 获取配额（需指定配额类型，附件一 §3.5）
export function getQuota(quotaType = 'POLICY_QA') {
  return request.get('/help/quota', { params: { quotaType } })
}

// ==================== 分类 ====================

export function getCategories() {
  return request.get('/help/categories')
}

// 政策详情（附件一 §3.5）
export function getGovPolicyDetail(id) {
  return request.get(`/help/gov-policy/${id}`)
}

// ==================== 认证 ====================

// 认证相关接口统一从 api/auth.js 导出，此处保留向后兼容的转发
export {
  login,
  register,
  guestLogin,
  sendSmsCode,
  phoneLogin,
  refreshToken,
  getUserInfo
} from './auth'
