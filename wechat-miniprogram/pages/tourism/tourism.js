const app = getApp()

Page({
  data: {
    elderlyMode: true,
    searchKeyword: '',
    attractions: [],
    loading: false,
    recommendedRoutes: [
      { id: 1, name: '北京一日游', spots: ['故宫', '天坛', '颐和园'], duration: '1天' },
      { id: 2, name: '杭州西湖休闲', spots: ['断桥', '雷峰塔', '苏堤'], duration: '1天' },
      { id: 3, name: '西安文化三日', spots: ['兵马俑', '大雁塔', '城墙'], duration: '3天' }
    ]
  },

  onLoad() {
    this.setData({ elderlyMode: app.globalData.elderlyMode })
  },

  onInput(e) {
    this.setData({ searchKeyword: e.detail.value })
  },

  /**
   * 景点查询：走文旅智能体（附件一 §6.4 景点导览）
   */
  onSearch() {
    const keyword = this.data.searchKeyword.trim()
    if (!keyword) {
      wx.showToast({ title: '请输入景点或城市名称', icon: 'none' })
      return
    }

    this.setData({ loading: true, attractions: [] })
    app.sendChat(
      `请介绍「${keyword}」的开放时间、门票价格、交通方式和主要看点。`,
      'tourism'
    ).then((res) => {
      this.setData({
        attractions: [{
          id: 0,
          name: keyword,
          summary: (res && res.content) || '暂时没有查到相关信息。'
        }],
        loading: false
      })
    }).catch(() => {
      this.setData({ loading: false })
      wx.showToast({ title: '查询失败，请稍后重试', icon: 'none' })
    })
  },

  /**
   * 路线规划：跳转对话页由文旅智能体规划（附件一 §6.4 路线规划）
   */
  onRouteTap(e) {
    const route = e.currentTarget.dataset.route
    wx.navigateTo({
      url: `/pages/chat/chat?type=tourism&q=${encodeURIComponent('请帮我规划' + route.name + '，按上下午晚间分段安排')}`
    })
  },

  /**
   * 景点详情页（附件一 §5.1 文旅导览）
   */
  onAttractionTap(e) {
    const name = e.currentTarget.dataset.name
    wx.navigateTo({
      url: `/pages/tourism/detail/detail?name=${encodeURIComponent(name)}`
    })
  },

  onAskAI() {
    wx.navigateTo({ url: '/pages/chat/chat?type=tourism' })
  },

  onCallEmergency() {
    wx.makePhoneCall({ phoneNumber: '120' })
  }
})
