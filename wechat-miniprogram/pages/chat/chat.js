const app = getApp()

// 页面 type 参数 -> 后端 agentType 映射
const TYPE_TO_AGENT = {
  general: 'elderly',
  health: 'elderly',
  medication: 'elderly',
  policy: 'govpolicy',
  tourism: 'tourism'
}

const AGENTS = [
  { key: 'elderly', name: '康养助手' },
  { key: 'govpolicy', name: '政策助手' },
  { key: 'tourism', name: '文旅助手' }
]

const WELCOME = {
  elderly: '您好，我是小芯康养助手。可以帮您查询用药注意事项、慢病护理建议、康复计划，或者了解长护险政策。',
  govpolicy: '您好，我是小芯政策助手。可以帮您查询惠民政策、养老补贴、医保等信息，回答会标注政策来源。',
  tourism: '您好，我是小芯文旅助手。可以为您推荐景点、规划行程路线，或者讲讲景点背后的文化故事。'
}

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    recording: false,
    speakEnabled: false,
    agents: AGENTS,
    agentType: 'elderly',
    elderlyMode: true,
    sessionId: null
  },

  onLoad(options) {
    const type = options.type || 'general'
    const agentType = TYPE_TO_AGENT[type] || app.globalData.agentType || 'elderly'

    this.setData({
      agentType,
      elderlyMode: app.globalData.elderlyMode,
      messages: [{ role: 'bot', content: WELCOME[agentType] }]
    })

    this.recorderManager = wx.getRecorderManager()
    this.audioCtx = wx.createInnerAudioContext()

    this.recorderManager.onStop((res) => {
      this.setData({ recording: false })
      if (res.tempFilePath) {
        this.uploadAudio(res.tempFilePath)
      }
    })

    this.recorderManager.onError(() => {
      this.setData({ recording: false })
      wx.showToast({ title: '录音失败，请检查麦克风权限', icon: 'none' })
    })

    // 从其他页面带问题跳转时自动发送
    if (options.q) {
      this.setData({ inputText: decodeURIComponent(options.q) })
      this.onSend()
    }
  },

  onUnload() {
    if (this.audioCtx) {
      this.audioCtx.destroy()
    }
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  /**
   * 发送消息（附件一 §3.2 POST /api/chat/send）
   */
  onSend() {
    const text = this.data.inputText.trim()
    if (!text || this.data.loading) return

    const messages = [...this.data.messages, { role: 'user', content: text }]
    this.setData({ messages, inputText: '', loading: true })

    app.sendChat(text, this.data.agentType, this.data.sessionId)
      .then((res) => {
        const reply = (res && res.content) || '抱歉，我没有理解您的问题。'
        this.setData({
          messages: [...this.data.messages, { role: 'bot', content: reply }],
          loading: false,
          sessionId: (res && res.sessionId) || this.data.sessionId
        })
        if (this.data.speakEnabled) {
          this.speak(reply)
        }
      })
      .catch(() => {
        this.setData({
          messages: [...this.data.messages, {
            role: 'bot',
            content: '抱歉，处理您的问题时出现了错误，请稍后重试。'
          }],
          loading: false
        })
      })
  },

  /**
   * 切换智能体（附件一 §3.4）
   */
  onSwitchAgent(e) {
    const key = e.currentTarget.dataset.key
    if (key === this.data.agentType) return

    const apply = () => this.setData({
      agentType: key,
      messages: [{ role: 'bot', content: WELCOME[key] }],
      sessionId: null
    })

    app.switchAgent(key)
      .then(() => {
        apply()
        wx.showToast({ title: '已切换', icon: 'success' })
      })
      .catch(apply)
  },

  /**
   * 语音输入：录音 -> 上传 ASR（附件一 §3.3 POST /api/voice/asr）
   */
  onVoiceInput() {
    if (this.data.recording) {
      this.recorderManager.stop()
      return
    }

    this.setData({ recording: true })
    this.recorderManager.start({
      duration: 60000,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 48000,
      format: 'mp3'
    })
    wx.showToast({ title: '正在录音，再次点击停止', icon: 'none' })
  },

  /**
   * 上传录音做语音识别
   */
  uploadAudio(filePath) {
    wx.showLoading({ title: '识别中...' })
    wx.uploadFile({
      url: app.globalData.apiBaseUrl + '/voice/asr',
      filePath,
      name: 'file',
      header: app.globalData.token
        ? { Authorization: 'Bearer ' + app.globalData.token }
        : {},
      success: (res) => {
        try {
          const body = JSON.parse(res.data)
          const text = body && body.data
          if (text) {
            this.setData({ inputText: text })
            this.onSend()
          } else {
            wx.showToast({ title: '没有听清，请再说一次', icon: 'none' })
          }
        } catch (e) {
          wx.showToast({ title: '识别失败，请重试', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '上传失败，请检查网络', icon: 'none' })
      },
      complete: () => wx.hideLoading()
    })
  },

  /**
   * 语音播报开关（附件一 §3.3 TTS）
   */
  onToggleSpeak() {
    const enabled = !this.data.speakEnabled
    this.setData({ speakEnabled: enabled })
    wx.showToast({ title: enabled ? '已开启语音播报' : '已关闭语音播报', icon: 'none' })
  },

  /**
   * TTS 播报（附件一 §3.3 GET /api/voice/tts）
   */
  speak(text) {
    const url = app.globalData.apiBaseUrl + '/voice/tts?text=' + encodeURIComponent(text.slice(0, 200))
    if (this.audioCtx) {
      this.audioCtx.src = url
      this.audioCtx.play()
    }
  },

  onClearChat() {
    wx.showModal({
      title: '清空对话',
      content: '确定清空所有对话记录吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({
            messages: [{ role: 'bot', content: WELCOME[this.data.agentType] }],
            sessionId: null
          })
        }
      }
    })
  }
})
