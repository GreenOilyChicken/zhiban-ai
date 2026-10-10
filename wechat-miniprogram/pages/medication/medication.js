const app = getApp()

Page({
  data: {
    drugName: '',
    result: null,
    loading: false,
    elderlyMode: true,
    emergencyDrugs: [
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

  onSearch() {
    const drug = this.data.drugName.trim()
    if (!drug) {
      wx.showToast({ title: '请输入药品名称', icon: 'none' })
      return
    }
    this.setData({ loading: true, result: null })
    app.request({
      url: '/help/medication/guide',
      method: 'POST',
      data: { drug }
    }).then(res => {
      this.setData({ result: res, loading: false })
    }).catch(() => {
      this.setData({ loading: false })
      wx.showToast({ title: '查询失败，请稍后重试', icon: 'none' })
    })
  },

  onQuickSelect(e) {
    const name = e.currentTarget.dataset.name
    this.setData({ drugName: name })
    this.onSearch()
  }
})
