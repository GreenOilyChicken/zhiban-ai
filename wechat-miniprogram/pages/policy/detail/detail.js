const app = getApp()

Page({
  data: {
    id: null,
    policy: null,
    loading: false,
    elderlyMode: true
  },

  onLoad(options) {
    const id = options.id
    this.setData({ id, elderlyMode: app.globalData.elderlyMode })
    if (id) {
      this.loadDetail(id)
    }
  },

  /**
   * 政策详情（附件一 §3.5 GET /api/help/gov-policy/{id}）
   */
  loadDetail(id) {
    this.setData({ loading: true })
    app.request({ url: `/help/gov-policy/${id}` })
      .then((res) => {
        this.setData({ policy: res || null, loading: false })
      })
      .catch(() => {
        this.setData({ loading: false })
        wx.showToast({ title: '加载失败', icon: 'none' })
      })
  },

  /**
   * 就本政策向 AI 提问（附件一 §4.1 政策问答）
   */
  onAskAI() {
    const title = (this.data.policy && this.data.policy.title) || ''
    const q = title ? `关于《${title}》，请帮我解读主要内容。` : '请帮我解读这条政策。'
    wx.navigateTo({
      url: `/pages/chat/chat?type=policy&q=${encodeURIComponent(q)}`
    })
  }
})
