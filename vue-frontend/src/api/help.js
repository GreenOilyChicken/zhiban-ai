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

// ==================== 管理端配额（附件一 §4.2 查看与调整）====================

// 查询配额列表（可按用户、类型过滤）
export function listQuotas(params) {
  return request.get('/admin/quota', { params })
}

// 调整指定用户指定类型的配额
export function adjustQuota(userId, quotaType, data) {
  return request.put(`/admin/quota/${userId}/${quotaType}`, data)
}

// ==================== 管理端知识库（附件一 §4.2 上传与同步）====================

// 上传知识库文档并同步索引
export function uploadKbDocument(file, collection = 'govpolicy', rebuild = true) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('collection', collection)
  formData.append('rebuild', String(rebuild))
  return request.post('/admin/kb/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000
  })
}

// 同步（重建）指定集合的知识库索引
export function syncKnowledgeBase(collection = 'govpolicy', rebuild = true) {
  return request.post('/admin/kb/sync', null, {
    params: { collection, rebuild },
    timeout: 300000
  })
}

// 相关推荐文章（附件一 §4.1 文章详情）
export function getRelatedArticles(id, limit = 5) {
  return request.get(`/articles/${id}/related`, { params: { limit } })
}

// ==================== 分类 ====================

export function getCategories(type) {
  return request.get('/help/categories', { params: type ? { type } : {} })
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
