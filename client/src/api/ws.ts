import type { ChatEvent } from '@/types/chat'

type EventCallback<T = unknown> = (data: T) => void

/**
 * WebSocket 聊天管理器
 * - 指数退避重连（最多 5 次）
 * - 30s 心跳保活
 */
export class ChatWebSocket {
  private ws: WebSocket | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private retryCount = 0
  private maxRetries = 5
  private conversationId = ''
  private token = ''

  onMessage: EventCallback<ChatEvent> = () => {}
  onError: EventCallback<Event> = () => {}
  onClose: EventCallback<CloseEvent> = () => {}

  /** 建立连接 */
  connect(conversationId: string, token: string): void {
    this.conversationId = conversationId
    this.token = token
    this.retryCount = 0
    this._connect()
  }

  /** 断开连接 */
  disconnect(): void {
    this._clearTimers()
    if (this.ws) {
      this.ws.onclose = null
      this.ws.close()
      this.ws = null
    }
  }

  /** 发送消息 */
  send(message: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'message', content: message }))
    }
  }

  private _connect(): void {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${location.host}/api/v1/chat/ws/${this.conversationId}?token=${this.token}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.retryCount = 0
      this._startHeartbeat()
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data: ChatEvent = JSON.parse(event.data)
        this.onMessage(data)
      } catch {
        // ignore malformed frames
      }
    }

    this.ws.onerror = (event: Event) => {
      this.onError(event)
    }

    this.ws.onclose = (event: CloseEvent) => {
      this._clearTimers()
      this.onClose(event)
      this._scheduleReconnect()
    }
  }

  private _startHeartbeat(): void {
    this._clearTimers()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30_000)
  }

  private _scheduleReconnect(): void {
    if (this.retryCount >= this.maxRetries) return
    const delay = Math.min(1000 * 2 ** this.retryCount, 30_000)
    this.retryCount++
    this.reconnectTimer = setTimeout(() => this._connect(), delay)
  }

  private _clearTimers(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }
}

export default ChatWebSocket
