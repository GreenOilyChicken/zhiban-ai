App({
  globalData: {
    userInfo: null,
    apiBaseUrl: 'https://api.zhiban-ai.com',
    token: null,
    elderlyMode: true,
    fontSize: 'large'
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
  },

  // 登录
  login(code) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBaseUrl + '/auth/wx-login',
        method: 'POST',
        data: { code },
        success: (res) => {
          if (res.data.code === 200) {
            this.globalData.token = res.data.data.token
            this.globalData.userInfo = res.data.data.userInfo
            wx.setStorageSync('token', res.data.data.token)
            resolve(res.data.data)
          } else {
            reject(res.data)
          }
        },
        fail: reject
      })
    })
  },

  // 通用请求
  request(options) {
    const { url, method = 'GET', data = {} } = options
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBaseUrl + url,
        method,
        data,
        header: {
          'Authorization': this.globalData.token ? 'Bearer ' + this.globalData.token : '',
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.data.code === 200) {
            resolve(res.data.data)
          } else if (res.data.code === 401) {
            this.handleAuthError()
            reject(res.data)
          } else {
            wx.showToast({ title: res.data.message || '请求失败', icon: 'none' })
            reject(res.data)
          }
        },
        fail: (err) => {
          wx.showToast({ title: '网络错误', icon: 'none' })
          reject(err)
        }
      })
    })
  },

  handleAuthError() {
    this.globalData.token = null
    wx.removeStorageSync('token')
    wx.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
    setTimeout(() => {
      wx.reLaunch({ url: '/pages/index/index' })
    }, 1500)
  }
})
