const app = getApp()

Page({
  data: {
    drugName: '',
    answer: '',
    loading: false,
    elderlyMode: true,
    commonDrugs: [
      { name: '阿司匹林', category: '抗血小板' },
      { name: '硝酸甘油', category: '心绞痛急救' },
      { name: '氨氯地平', category: '降压药' },
      { name: '二甲双胍', category: '降糖药' },
      { name: '氯沙坦', category: '降压药' },
      { name: '瑞舒伐他汀', category: '降脂药' }
    ]
  },

  onLoad() {
    this.setData({ elderlyMode: app.globalData.elderlyMode })
  },

  onInput(e) {
    this.setData({ drugName: e.detail.value })
  },

  /**
   * 用药查询：走康养智能体对话接口（附件一 §6.2 用药指导工具）
   */
  onSearch() {
    const drug = this.data.drugName.trim()
    if (!drug) {
      wx.showToast({ title: '请输入药品名称', icon: 'none' })
      return
    }

    this.setData({ loading: true, answer: '' })
    app.sendChat(
      `请介绍「${drug}」的用途、常见不良反应、与其他药物的相互作用和禁忌人群，并说明用药注意事项。`,
      'elderly'
    ).then((res) => {
      this.setData({ answer: (res && res.content) || '暂时没有查到相关信息。', loading: false })
    }).catch(() => {
      this.setData({ loading: false })
      wx.showToast({ title: '查询失败，请稍后重试', icon: 'none' })
    })
  },

  onQuickSelect(e) {
    const name = e.currentTarget.dataset.name
    this.setData({ drugName: name })
    this.onSearch()
  },

  /**
   * 继续追问：跳转对话页
   */
  onAskMore() {
    wx.navigateTo({ url: '/pages/chat/chat?type=medication' })
  }
})
