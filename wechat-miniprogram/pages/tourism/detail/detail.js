const app = getApp()

Page({
  data: {
    id: null,
    attraction: null,
    loading: false,
    elderlyMode: true
  },

  onLoad(options) {
    const id = options.id
    const name = options.name ? decodeURIComponent(options.name) : ''
    this.setData({ id, elderlyMode: app.globalData.elderlyMode })

    if (name) {
      this.loadByName(name)
    } else if (id) {
      this.setData({
        attraction: { name: `景点 #${id}`, summary: '请通过搜索或 AI 导览获取该景点详情。' }
      })
    }
  },

  /**
   * 通过文旅智能体获取景点详情（附件一 §6.4 景点导览）
   */
  loadByName(name) {
    this.setData({ loading: true })
    app.sendChat(
      `请介绍「${name}」的开放时间、门票价格、交通方式和主要看点。`,
      'tourism'
    ).then((res) => {
      this.setData({
        attraction: { name, summary: (res && res.content) || '' },
        loading: false
      })
    }).catch(() => {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    })
  },

  /**
   * 规划到该景点的路线
   */
  onPlanRoute() {
    const name = (this.data.attraction && this.data.attraction.name) || ''
    wx.navigateTo({
      url: `/pages/chat/chat?type=tourism&q=${encodeURIComponent('请帮我规划包含' + name + '的一日行程，按上下午晚间分段')}`
    })
  },

  onCallEmergency() {
    wx.makePhoneCall({ phoneNumber: '120' })
  }
})
