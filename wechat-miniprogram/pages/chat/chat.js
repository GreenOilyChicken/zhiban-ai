const app = getApp()
const chatCache = require('../../utils/chatCache')

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

// 弱网/离线统一提示文案（附件一 §5.2）
const OFFLINE_TIP = '当前网络不可用，已显示本地缓存对话'

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
    sessionId: null,
    // 网络状态：在线才允许发送，避免静默失败
    online: true,
    offlineNotice: ''
  },

  onLoad(options) {
    const type = options.type || 'general'
    const agentType = TYPE_TO_AGENT[type] || app.globalData.agentType || 'elderly'

    // 启动恢复：优先展示本地缓存的最近对话（离线也能看到上次对话）
    this._requestFailedNotice = false
    const cached = chatCache.load(agentType)
    const messages = (cached && cached.messages && cached.messages.length)
      ? cached.messages
      : [{ role: 'bot', content: WELCOME[agentType] }]

    this.setData({
      agentType,
      elderlyMode: app.globalData.elderlyMode,
      messages,
      sessionId: (cached && cached.sessionId) || null
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

    // 网络状态监听（附件一 §5.2 弱网友好提示）
    this.initNetworkListener()

    // 从其他页面带问题跳转时自动发送
    if (options.q) {
      this.setData({ inputText: decodeURIComponent(options.q) })
      this.onSend()
    }
  },

  onShow() {
    // 从后台/其他页面返回时重新探测一次网络
    this.checkNetwork()
  },

  onUnload() {
    if (this.audioCtx) {
      this.audioCtx.destroy()
    }
    if (this.networkListener) {
      try {
        wx.offNetworkStatusChange(this.networkListener)
      } catch (e) {
        // 忽略：部分基础库不支持 offNetworkStatusChange
      }
      this.networkListener = null
    }
  },

  /* ------------------------------------------------------------------ *
   * 网络检测与弱网提示
   * ------------------------------------------------------------------ */

  /**
   * 注册网络状态变化监听；离线时展示提示条，恢复后自动隐藏
   */
  initNetworkListener() {
    this.networkListener = (res) => {
      const online = !!res.isConnected
      const wasOnline = this.data.online
      this.setData({
        online,
        offlineNotice: online
          ? (this._requestFailedNotice ? OFFLINE_TIP : '')
          : OFFLINE_TIP
      })
      if (!online) {
        wx.showToast({ title: OFFLINE_TIP, icon: 'none' })
      } else if (!wasOnline) {
        wx.showToast({ title: '网络已恢复', icon: 'success' })
      }
    }
    try {
      wx.onNetworkStatusChange(this.networkListener)
    } catch (e) {
      this.networkListener = null
    }
    this.checkNetwork()
  },

  /**
   * 主动探测当前网络类型（wx.getNetworkType）
   * @param {boolean} notify 是否对用户提示探测结果
   */
  checkNetwork(notify) {
    if (typeof wx.getNetworkType !== 'function') return
    wx.getNetworkType({
      success: (res) => {
        // networkType === 'none' 表示无网络
        const online = res.networkType !== 'none'
        // 请求失败留下的提示条不因「探测到网络类型正常」而被清掉，避免静默失败
        const notice = online
          ? (this._requestFailedNotice ? OFFLINE_TIP : '')
          : OFFLINE_TIP
        this.setData({
          online,
          offlineNotice: notice
        })
        if (notify) {
          wx.showToast({
            title: online ? '网络正常' : OFFLINE_TIP,
            icon: 'none'
          })
        }
      },
      fail: () => {
        // 探测失败不阻断使用，保持当前状态
      }
    })
  },

  /**
   * 点击提示条重试
   */
  onRetryNetwork() {
    // 用户主动重试：清除上一次请求失败留下的提示条，再重新探测
    this._requestFailedNotice = false
    this.checkNetwork(true)
  },

  /* ------------------------------------------------------------------ *
   * 对话缓存
   * ------------------------------------------------------------------ */

  /**
   * 持久化当前智能体的最近对话（最多 50 条，失败静默降级，不崩溃）
   */
  persistMessages(agentType, messages, sessionId) {
    const ok = chatCache.save(
      agentType || this.data.agentType,
      messages || this.data.messages,
      sessionId !== undefined ? sessionId : this.data.sessionId
    )
    if (!ok) {
      // 存储失败不阻塞对话，仅提示一次
      if (!this._cacheWarned) {
        this._cacheWarned = true
        wx.showToast({ title: '本地缓存写入失败', icon: 'none' })
      }
    }
    return ok
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

    // 离线时明确提示并阻止发送，不做静默失败
    if (!this.data.online) {
      this.setData({ offlineNotice: OFFLINE_TIP })
      wx.showToast({ title: OFFLINE_TIP, icon: 'none' })
      return
    }

    const messages = [...this.data.messages, { role: 'user', content: text }]
    this.setData({ messages, inputText: '', loading: true })
    // 先落盘用户消息：即使请求失败/超时，本地也留得住这条记录
    this.persistMessages(this.data.agentType, messages)

    app.sendChat(text, this.data.agentType, this.data.sessionId)
      .then((res) => {
        const reply = (res && res.content) || '抱歉，我没有理解您的问题。'
        const sessionId = (res && res.sessionId) || this.data.sessionId
        const nextMessages = [...this.data.messages, { role: 'bot', content: reply }]
        this._requestFailedNotice = false
        this.setData({
          messages: nextMessages,
          loading: false,
          sessionId,
          offlineNotice: ''
        })
        this.persistMessages(this.data.agentType, nextMessages, sessionId)
        if (this.data.speakEnabled) {
          this.speak(reply)
        }
      })
      .catch(() => {
        const nextMessages = [...this.data.messages, {
          role: 'bot',
          content: '抱歉，处理您的问题时出现了错误，请稍后重试。'
        }]
        // 请求失败：提示条 + 保留本地缓存对话（弱网友好提示）
        this._requestFailedNotice = true
        this.setData({
          messages: nextMessages,
          loading: false,
          offlineNotice: OFFLINE_TIP
        })
        this.persistMessages(this.data.agentType, nextMessages)
        this.checkNetwork()
      })
  },

  /**
   * 切换智能体（附件一 §3.4）
   */
  onSwitchAgent(e) {
    const key = e.currentTarget.dataset.key
    if (key === this.data.agentType) return

    // 切换前先保存当前智能体的对话
    this.persistMessages(this.data.agentType)

    const apply = () => {
      // 切换后加载对应智能体的本地缓存（分键存储）
      const cached = chatCache.load(key)
      const messages = (cached && cached.messages && cached.messages.length)
        ? cached.messages
        : [{ role: 'bot', content: WELCOME[key] }]
      this.setData({
        agentType: key,
        messages,
        sessionId: (cached && cached.sessionId) || null
      })
    }

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
    if (!this.data.online) {
      this.setData({ offlineNotice: OFFLINE_TIP })
      wx.showToast({ title: '当前网络不可用，语音输入暂不可用', icon: 'none' })
      return
    }
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
        this._requestFailedNotice = true
        this.setData({ offlineNotice: OFFLINE_TIP })
        wx.showToast({ title: '上传失败，请检查网络', icon: 'none' })
        this.checkNetwork()
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
    // audio.src 无法设置请求头，故通过查询参数携带 token
    const token = wx.getStorageSync('token') || ''
    let url = app.globalData.apiBaseUrl + '/voice/tts?text=' + encodeURIComponent(text.slice(0, 200))
    if (token) {
      url += '&token=' + encodeURIComponent(token)
    }
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
          // 同时清掉本地缓存，避免重进页面又恢复旧记录
          chatCache.clear(this.data.agentType)
          this.setData({
            messages: [{ role: 'bot', content: WELCOME[this.data.agentType] }],
            sessionId: null
          })
        }
      }
    })
  }
})
