/**
 * 对话记录本地缓存（附件一 V1.0 §5.2：「离线缓存最近对话记录，弱网环境下友好提示」）
 *
 * 设计说明：
 *  - 分键存储：键名 `chatHistory_<agentType>`。康养/政务/文旅三个智能体各自独立，
 *    切换智能体时能精确恢复对应历史，且单键体积更小、更不易触发 1MB 上限。
 *  - 容量控制：每个键最多保留最近 MAX_MESSAGES = 50 条消息（只留尾部，丢弃更早的）。
 *  - 写入降级：若 50 条仍写入失败（存储超限等），依次按 20 / 10 条重试，并截断单条正文长度；
 *    全部失败只返回 false，绝不抛出异常。
 *  - 所有 wx.*Storage* 调用均包裹 try/catch，存储异常不会导致页面崩溃。
 *
 * 存储结构：
 *   {
 *     version: 1,
 *     updatedAt: 时间戳,
 *     sessionId: '后端会话 id 或 null',
 *     messages: [{ role: 'user' | 'bot', content: '文本' }]
 *   }
 * 兼容旧数据：若读到的直接是消息数组，也能正常解析。
 */

var KEY_PREFIX = 'chatHistory_'
var MAX_MESSAGES = 50
var MAX_CONTENT_LENGTH = 2000
// 写入失败时的降级重试条数（依次尝试）
var FALLBACK_LIMITS = [MAX_MESSAGES, 20, 10]
var VERSION = 1

/**
 * 计算某个智能体的缓存键
 * @param {string} agentType
 * @return {string}
 */
function cacheKey(agentType) {
  return KEY_PREFIX + (agentType || 'elderly')
}

/**
 * 把任意输入规整成 {role, content}，非法消息返回 null
 */
function normalizeMessage(msg) {
  if (!msg || typeof msg !== 'object') return null
  var role = msg.role === 'user' ? 'user' : 'bot'
  var content = msg.content
  if (content === null || content === undefined) return null
  if (typeof content !== 'string') content = String(content)
  if (content.length > MAX_CONTENT_LENGTH) {
    content = content.slice(0, MAX_CONTENT_LENGTH)
  }
  if (!content) return null
  return { role: role, content: content }
}

/**
 * 清洗消息数组，并只保留最近 limit 条
 * @param {Array} messages
 * @param {number} limit
 * @return {Array}
 */
function sanitize(messages, limit) {
  var max = typeof limit === 'number' && limit > 0 ? limit : MAX_MESSAGES
  if (!messages || typeof messages.length !== 'number') return []
  var list = []
  for (var i = 0; i < messages.length; i++) {
    var m = normalizeMessage(messages[i])
    if (m) list.push(m)
  }
  // 只保留最近 max 条，保证不会超出小程序单键 1MB 限制
  if (list.length > max) {
    list = list.slice(list.length - max)
  }
  return list
}

/**
 * 保存某个智能体的最近对话
 * @param {string} agentType
 * @param {Array} messages
 * @param {string|null} sessionId
 * @return {boolean} 是否写入成功
 */
function save(agentType, messages, sessionId) {
  var key = cacheKey(agentType)
  for (var i = 0; i < FALLBACK_LIMITS.length; i++) {
    var payload = {
      version: VERSION,
      updatedAt: Date.now(),
      sessionId: sessionId || null,
      messages: sanitize(messages, FALLBACK_LIMITS[i])
    }
    try {
      wx.setStorageSync(key, payload)
      return true
    } catch (e) {
      // 存储超限/不可用：清掉半成品后降级重试
      try {
        wx.removeStorageSync(key)
      } catch (e2) {
        // 忽略：清理失败不影响降级重试
      }
    }
  }
  return false
}

/**
 * 读取某个智能体的缓存对话
 * @param {string} agentType
 * @return {{messages: Array, sessionId: string|null, updatedAt: number}|null}
 */
function load(agentType) {
  var key = cacheKey(agentType)
  var raw = null
  try {
    raw = wx.getStorageSync(key)
  } catch (e) {
    return null
  }
  if (!raw) return null

  // 兼容被序列化成字符串写入的情况
  if (typeof raw === 'string') {
    try {
      raw = JSON.parse(raw)
    } catch (e) {
      return null
    }
  }
  if (!raw || typeof raw !== 'object') return null

  var messages = []
  var sessionId = null
  var updatedAt = 0
  if (Object.prototype.toString.call(raw) === '[object Array]') {
    messages = sanitize(raw, MAX_MESSAGES)
  } else {
    messages = sanitize(raw.messages, MAX_MESSAGES)
    sessionId = raw.sessionId || null
    updatedAt = raw.updatedAt || 0
  }
  if (!messages.length) return null
  return { messages: messages, sessionId: sessionId, updatedAt: updatedAt }
}

/**
 * 清空某个智能体的缓存
 * @param {string} agentType
 * @return {boolean}
 */
function clear(agentType) {
  try {
    wx.removeStorageSync(cacheKey(agentType))
    return true
  } catch (e) {
    return false
  }
}

module.exports = {
  KEY_PREFIX: KEY_PREFIX,
  MAX_MESSAGES: MAX_MESSAGES,
  MAX_CONTENT_LENGTH: MAX_CONTENT_LENGTH,
  cacheKey: cacheKey,
  sanitize: sanitize,
  save: save,
  load: load,
  clear: clear
}
