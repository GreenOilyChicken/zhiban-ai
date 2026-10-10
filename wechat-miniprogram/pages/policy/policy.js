const app = getApp()

Page({
  data: {
    tabs: [
      { id: '', name: '全部' },
      { id: '养老', name: '养老' },
      { id: '旅游', name: '旅游' },
      { id: '政务', name: '政务' }
    ],
    activeTab: '',
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

  /**
   * 政策列表（附件一 §3.5 GET /api/help/gov-policy）
   */
  loadPolicies() {
    this.setData({ loading: true })
    const params = { page: 1, size: 20 }
    if (this.data.activeTab) {
      params.policyType = this.data.activeTab
    }

    app.request({ url: '/help/gov-policy', data: params })
      .then((res) => {
        this.setData({ policies: (res && res.records) || [], loading: false })
      })
      .catch(() => {
        this.setData({ loading: false })
      })
  },

  /**
   * 政策详情（附件一 §3.5 GET /api/help/gov-policy/{id}）
   */
  onPolicyTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/policy/detail/detail?id=${id}` })
  },

  onAskAI() {
    wx.navigateTo({ url: '/pages/chat/chat?type=policy' })
  }
})
