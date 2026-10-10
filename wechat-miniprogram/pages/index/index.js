const app = getApp()

Page({
  data: {
    elderlyMode: true,
    userName: '',
    todayDate: '',
    quickActions: [
      { id: 'medication', title: '用药指导', desc: '查询药物用法、相互作用', icon: 'pill' },
      { id: 'policy', title: '惠民政策', desc: '查询养老、医保等政策', icon: 'policy' },
      { id: 'tourism', title: '文旅导览', desc: '景点介绍、路线推荐', icon: 'tour' },
      { id: 'health', title: '健康咨询', desc: '慢病管理、照护建议', icon: 'health' }
    ]
  },

  onLoad() {
    const now = new Date()
    const dateStr = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`
    this.setData({
      todayDate: dateStr,
      elderlyMode: app.globalData.elderlyMode
    })
  },

  onShow() {
    this.setData({ elderlyMode: app.globalData.elderlyMode })
  },

  onQuickAction(e) {
    const id = e.currentTarget.dataset.id
    const routes = {
      medication: '/pages/medication/medication',
      policy: '/pages/policy/policy',
      tourism: '/pages/tourism/tourism',
      health: '/pages/chat/chat?type=health'
    }
    if (routes[id]) {
      wx.navigateTo({ url: routes[id] })
    }
  },

  onChatTap() {
    wx.navigateTo({ url: '/pages/chat/chat' })
  },

  onCallEmergency() {
    wx.showModal({
      title: '紧急呼叫',
      content: '确定要拨打120急救电话吗？',
      success(res) {
        if (res.confirm) {
          wx.makePhoneCall({ phoneNumber: '120' })
        }
      }
    })
  }
})
