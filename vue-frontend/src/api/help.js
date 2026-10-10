import request from './index'
import { setToken } from './index'

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

// 获取配额（字段：totalQuota / usedQuota / remainingQuota）
export function getQuota() {
  return request.get('/help/quota')
}

// ==================== 分类 ====================

export function getCategories() {
  return request.get('/help/categories')
}

// ==================== 认证 ====================

export function login(data) {
  return request.post('/auth/login', data).then((res) => {
    if (res.data?.token) {
      setToken(res.data.token)
    }
    return res
  })
}

export function register(data) {
  return request.post('/auth/register', data)
}
