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
    this.loadAttractions()
  },

  loadAttractions() {
    this.setData({ loading: true })
    app.request({
      url: '/help/tourism/attractions',
      data: { page: 1, size: 10 }
    }).then(res => {
      const attractions = res.records || res.list || []
      this.setData({ attractions, loading: false })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },

  onInput(e) {
    this.setData({ searchKeyword: e.detail.value })
  },

  onSearch() {
    const keyword = this.data.searchKeyword.trim()
    if (!keyword) {
      this.loadAttractions()
      return
    }
    this.setData({ loading: true })
    app.request({
      url: '/help/tourism/attractions',
      data: { keyword, page: 1, size: 10 }
    }).then(res => {
      this.setData({ attractions: res.records || [], loading: false })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },

  onAttractionTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/tourism/detail?id=${id}`
    })
  },

  onRouteTap(e) {
    const route = e.currentTarget.dataset.route
    wx.navigateTo({
      url: `/pages/chat/chat?type=tourism&q=${encodeURIComponent('我想了解' + route.name + '路线')}`
    })
  },

  onAskAI() {
    wx.navigateTo({
      url: '/pages/chat/chat?type=tourism'
    })
  }
})
