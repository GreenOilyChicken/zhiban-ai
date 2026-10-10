App({
  globalData: {
    userInfo: null,
    // 后端 API 基础地址（含 /api 前缀，附件一 §2.1 前后端分离）
    // 开发：本地后端；生产：替换为 HTTPS 域名（附件一 §10.3 要求 HTTPS）
    apiBaseUrl: 'http://127.0.0.1:8080/api',
    token: null,
    elderlyMode: true,
    fontSize: 'large',
    // 当前智能体（附件一 §3.4 三大方向）
    agentType: 'elderly'
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.token = token
    }

    const elderlyMode = wx.getStorageSync('elderlyMode')
    if (elderlyMode !== '' && elderlyMode !== undefined) {
      this.globalData.elderlyMode = elderlyMode
    }

    const agentType = wx.getStorageSync('agentType')
    if (agentType) {
      this.globalData.agentType = agentType
    }

    // 无 token 时自动游客登录（附件一 §3.1 游客登录）
    if (!this.globalData.token) {
      this.guestLogin().catch(() => {
        // 静默失败：进入页面后仍可浏览公开内容
      })
    }
  },

  /**
   * 游客登录：无需凭证，自动生成游客身份并返回 JWT
   */
  guestLogin() {
    return this.request({
      url: '/auth/guest-login',
      method: 'POST',
      skipAuth: true
    }).then((data) => {
      if (data && data.token) {
        this.globalData.token = data.token
        this.globalData.userInfo = {
          userId: data.userId,
          username: data.username,
          role: data.role
        }
        wx.setStorageSync('token', data.token)
      }
      return data
    })
  },

  /**
   * 微信登录：获取 code 后换取 token
   * 后端暂未提供 /auth/wx-login，当前降级为游客登录
   */
  login() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: () => {
          this.guestLogin().then(resolve).catch(reject)
        },
        fail: reject
      })
    })
  },

  /**
   * 通用请求
   * @param {Object} options {url, method, data, header, skipAuth}
   */
  request(options) {
    const { url, method = 'GET', data = {}, skipAuth = false } = options
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBaseUrl + url,
        method,
        data,
        header: Object.assign(
          { 'Content-Type': 'application/json' },
          skipAuth || !this.globalData.token
            ? {}
            : { Authorization: 'Bearer ' + this.globalData.token }
        ),
        success: (res) => {
          const body = res.data || {}

          // HTTP 429：接口频率限制（附件一 §3.6）
          if (res.statusCode === 429) {
            wx.showToast({ title: '操作太频繁，请稍后再试', icon: 'none' })
            reject(body)
            return
          }

          // 未认证：清空 token 并自动重试游客登录
          if (res.statusCode === 401 || body.code === 401) {
            this.handleAuthError()
            reject(body)
            return
          }

          if (body.code === 200) {
            resolve(body.data)
          } else {
            wx.showToast({ title: body.message || '请求失败', icon: 'none' })
            reject(body)
          }
        },
        fail: (err) => {
          // 弱网/断网友好提示（附件一 §5.2）
          wx.showToast({ title: '网络不给力，请检查网络', icon: 'none' })
          reject(err)
        }
      })
    })
  },

  handleAuthError() {
    this.globalData.token = null
    wx.removeStorageSync('token')
    // 自动重新游客登录，避免用户被迫手动操作
    this.guestLogin().catch(() => {
      wx.showToast({ title: '登录已过期，请重新进入', icon: 'none' })
    })
  },

  /**
   * 切换智能体（附件一 §3.4）
   */
  switchAgent(agentType) {
    return this.request({
      url: `/agent/switch/${agentType}`,
      method: 'POST'
    }).then((persona) => {
      this.globalData.agentType = agentType
      wx.setStorageSync('agentType', agentType)
      return persona
    })
  },

  /**
   * 发送对话消息（附件一 §3.2）
   */
  sendChat(content, agentType, sessionId) {
    return this.request({
      url: '/chat/send',
      method: 'POST',
      data: {
        content,
        agentType: agentType || this.globalData.agentType,
        sessionId: sessionId || null,
        messageType: 'text'
      }
    })
  }
})
