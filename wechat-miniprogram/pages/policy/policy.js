const app = getApp()

Page({
  data: {
    tabs: [
      { id: 'gov_service', name: '政务服务' },
      { id: 'silver_economy', name: '银发经济' },
      { id: 'culture_tourism', name: '文旅项目' }
    ],
    activeTab: 'gov_service',
    policies: [],
    loading: false
  },

  onLoad() {
    this.loadPolicies()
  },

  onTabChange(e) {
    const tabId = e.currentTarget.dataset.id
    this.setData({ activeTab: tabId })
    this.loadPolicies()
  },

  loadPolicies() {
    this.setData({ loading: true })
    app.request({
      url: '/help/gov-policy',
      data: { category: this.data.activeTab, page: 1, size: 20 }
    }).then(res => {
      const policies = res.records || res.list || []
      this.setData({ policies, loading: false })
    }).catch(() => {
      this.setData({ loading: false })
    })
  },

  onPolicyTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/policy/detail?id=${id}`
    })
  },

  onAskAI() {
    wx.navigateTo({
      url: '/pages/chat/chat?type=policy'
    })
  }
})
