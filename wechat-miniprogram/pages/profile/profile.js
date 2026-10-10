const app = getApp()

Page({
  data: {
    userInfo: null,
    elderlyMode: true,
    menuItems: [
      { id: 'history', title: '咨询记录', icon: '📋' },
      { id: 'favorite', title: '我的收藏', icon: '⭐' },
      { id: 'medication', title: '用药提醒', icon: '💊' },
      { id: 'appointment', title: '预约服务', icon: '📅' },
      { id: 'feedback', title: '意见反馈', icon: '💬' },
      { id: 'settings', title: '设置', icon: '⚙️' },
      { id: 'about', title: '关于我们', icon: 'ℹ️' }
    ]
  },

  onShow() {
    this.setData({
      userInfo: app.globalData.userInfo,
      elderlyMode: app.globalData.elderlyMode
    })
  },

  onMenuTap(e) {
    const id = e.currentTarget.dataset.id
    switch (id) {
      case 'history':
        // 咨询记录：跳转对话页查看/继续对话（附件一 §5.1）
        wx.navigateTo({ url: '/pages/chat/chat' })
        break
      case 'medication':
        wx.navigateTo({ url: '/pages/medication/medication' })
        break
      case 'settings':
        this.toggleElderlyMode()
        break
      case 'feedback':
        this.onFeedback()
        break
      case 'about':
        wx.showModal({
          title: '关于小芯',
          content: '小芯银发适老化AI陪伴系统 V1.0\n\n开发单位：知伴（湖州）智能科技有限公司\n\n为老年人提供用药指导、政策查询、文旅导览、健康咨询等AI服务。',
          showCancel: false
        })
        break
      default:
        wx.showToast({ title: '功能开发中', icon: 'none' })
    }
  },

  toggleElderlyMode() {
    const newMode = !this.data.elderlyMode
    app.globalData.elderlyMode = newMode
    wx.setStorageSync('elderlyMode', newMode)
    this.setData({ elderlyMode: newMode })
    wx.showToast({
      title: newMode ? '已开启大字模式' : '已关闭大字模式',
      icon: 'none'
    })
  },

  onFeedback() {
    wx.showModal({
      title: '意见反馈',
      editable: true,
      placeholderText: '请输入您的意见或建议',
      success(res) {
        if (res.confirm && res.content) {
          wx.showToast({ title: '感谢您的反馈', icon: 'success' })
        }
      }
    })
  },

  onCallEmergency(e) {
    const phone = e.currentTarget.dataset.phone
    wx.showModal({
      title: '确认拨打电话',
      content: `确定要拨打 ${phone} 吗？`,
      success(res) {
        if (res.confirm) {
          wx.makePhoneCall({ phoneNumber: phone })
        }
      }
    })
  },

  onLogin() {
    wx.login({
      success: (res) => {
        if (res.code) {
          app.login(res.code).then(() => {
            this.setData({ userInfo: app.globalData.userInfo })
            wx.showToast({ title: '登录成功', icon: 'success' })
          }).catch(() => {
            wx.showToast({ title: '登录失败', icon: 'none' })
          })
        }
      }
    })
  }
})
