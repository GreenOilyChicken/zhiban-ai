const app = getApp()

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    chatType: 'general',
    elderlyMode: true
  },

  onLoad(options) {
    const type = options.type || 'general'
    this.setData({
      chatType: type,
      elderlyMode: app.globalData.elderlyMode
    })

    const welcomeMsgs = {
      general: '您好，我是小芯AI陪伴助手。您可以问我关于用药、政策、文旅、健康等方面的问题。',
      health: '您好，我可以为您提供慢病管理、照护建议等方面的咨询。请描述您的状况或问题。',
      medication: '您好，请告诉我您想了解的药物名称，我可以为您提供用药指导。',
      policy: '您好，我可以为您查询惠民政策、养老补贴、医保等信息。请描述您想了解的政策。',
      tourism: '您好，我可以为您推荐旅游景点和路线。请告诉我您想去的城市或景点。'
    }

    this.setData({
      messages: [{
        role: 'bot',
        content: welcomeMsgs[type] || welcomeMsgs.general
      }]
    })
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  onSend() {
    const text = this.data.inputText.trim()
    if (!text || this.data.loading) return

    const messages = [...this.data.messages, { role: 'user', content: text }]
    this.setData({
      messages,
      inputText: '',
      loading: true
    })

    app.request({
      url: '/help/gov-policy/ask',
      method: 'POST',
      data: { question: text, chatType: this.data.chatType }
    }).then(answer => {
      const newMessages = [...this.data.messages, { role: 'bot', content: answer }]
      this.setData({ messages: newMessages, loading: false })
    }).catch(err => {
      const newMessages = [...this.data.messages, {
        role: 'bot',
        content: '抱歉，处理您的问题时出现了错误，请稍后重试。'
      }]
      this.setData({ messages: newMessages, loading: false })
    })
  },

  onVoiceInput() {
    wx.showToast({ title: '语音输入开发中', icon: 'none' })
  },

  onClearChat() {
    wx.showModal({
      title: '清空对话',
      content: '确定清空所有对话记录吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({ messages: [this.data.messages[0]] })
        }
      }
    })
  }
})
