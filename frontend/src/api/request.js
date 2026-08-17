import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'

const request = axios.create({
  baseURL: '/api',
  timeout: 300000
})

// 请求拦截：自动附带 Token
request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

// 响应拦截：401 自动登出跳转登录
request.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      ElMessage.warning('登录已过期，请重新登录')
      router.push({ name: 'Login' })
    } else if (status === 403) {
      ElMessage.error('无权限访问')
    } else {
      const msg = error.response?.data?.detail || error.message || '请求失败'
      ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
    return Promise.reject(error)
  }
)

/**
 * 使用 Fetch SSE 方式做流式请求（不经过 axios）
 * onData(chunk: string) 每次返回文本片段
 * onDone() 结束
 * onError(err) 异常
 */
export function sseRequest({ url, data, token, onData, onDone, onError }) {
  let abortCtrl = new AbortController()
  ;(async () => {
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(data),
        signal: abortCtrl.signal
      })
      if (!resp.ok) {
        let text = ''
        try { text = await resp.text() } catch (_) {}
        throw new Error(`HTTP ${resp.status} ${text}`)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // 按 SSE 格式拆分：每个事件以 \n\n 结束
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        for (const part of parts) {
          const lines = part.split('\n')
          for (const line of lines) {
            if (line.startsWith('data:')) {
              // 剥掉 "data:" 及其后的一个分隔空格，否则每个 chunk 都带前导
              // 空格：META:/[DONE] 判定会失败（" META:..."）、回答逐字被空格隔开
              const chunk = line.slice(5).replace(/^ /, '')
              if (chunk === '[DONE]') {
                onDone && onDone()
                return
              }
              if (chunk.startsWith('[ERROR]')) {
                onError && onError(new Error(chunk.slice(8).trim()))
                return
              }
              onData && onData(chunk)
            }
          }
        }
      }
      onDone && onDone()
    } catch (err) {
      if (err.name === 'AbortError') return
      onError && onError(err)
    }
  })()
  return {
    abort: () => abortCtrl.abort()
  }
}

export default request
