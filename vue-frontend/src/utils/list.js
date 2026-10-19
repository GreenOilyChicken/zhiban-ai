/**
 * 分页/列表响应解包工具
 *
 * 背景（重要）：
 *   后端统一返回 `Result<T>`，分页数据由 MyBatis-Plus 的 `Page` 序列化而来，
 *   字段为 `{ records, total, size, current, pages }`。
 *   但前端多个页面按 Spring Data 风格的 `content / totalElements` 取值，
 *   取不到时又回退成 `res.data || []`——而 `res.data` 是**对象**而非数组，
 *   于是把 `{records, total, ...}` 直接绑给了 `el-table`，
 *   导致运行时抛错：
 *     TypeError: xxx is not iterable
 *     TypeError: n.reduce is not a function
 *
 * 这里集中做「安全解包」：无论后端返回数组、records、content，
 * 还是异常对象，都保证调用方拿到**数组**，从根上避免上述崩溃。
 */

/**
 * 从任意响应体中取出列表数组
 *
 * @param {*} data 通常是 res.data
 * @returns {Array} 一定是数组（取不到时返回空数组）
 */
export function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object') {
    // MyBatis-Plus Page
    if (Array.isArray(data.records)) return data.records
    // Spring Data Page（兼容保留）
    if (Array.isArray(data.content)) return data.content
    // 常见的嵌套包装
    if (Array.isArray(data.list)) return data.list
    if (Array.isArray(data.items)) return data.items
  }
  return []
}

/**
 * 从任意响应体中取出总条数
 *
 * @param {*} data 通常是 res.data
 * @returns {number} 一定是数字（取不到时返回 0）
 */
export function unwrapTotal(data) {
  if (data && typeof data === 'object') {
    const t = data.total ?? data.totalElements
    if (typeof t === 'number' && Number.isFinite(t)) return t
  }
  // 退化：用数组长度兜底
  return unwrapList(data).length
}
