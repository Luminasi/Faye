import { defineStore } from 'pinia'
import { login as apiLogin, getMe, changePassword as apiChangePassword, register as apiRegister } from '@/api/auth'

const TOKEN_KEY = 'rag_token'
const USER_KEY = 'rag_user'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
    // 标记是否已经尝试过 fetchMe，避免每个路由重复请求
    _meTried: false
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin'
  },
  actions: {
    async register(payload) {
      return await apiRegister(payload)
    },
    async login(payload) {
      const resp = await apiLogin(payload)
      this.token = resp.access_token
      // 登录接口已经返回了 username + role，直接用；不再立即调 getMe()
      // 避免“登录成功”和“登录过期”两个 toast 同时出现的时序问题
      this.user = {
        username: resp.username,
        role: resp.role,
        id: resp.user_id ?? undefined,
        email: resp.email ?? undefined
      }
      localStorage.setItem(TOKEN_KEY, this.token)
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      this._meTried = true
      return resp
    },
    /**
     * 仅在以下场景调用：
     *   - 刷新页面后 Pinia user 丢失但 token 还在时
     *   - 确实需要最新的 email/id 等信息时
     */
    async fetchMe() {
      if (!this.token) return null
      const me = await getMe()
      this.user = me
      localStorage.setItem(USER_KEY, JSON.stringify(me))
      this._meTried = true
      return me
    },
    async ensureMe() {
      // 已取过、或者没有 token、或者已经有 user 了，就不重复取
      if (this._meTried || !this.token) return
      if (this.user) { this._meTried = true; return }
      try {
        await this.fetchMe()
      } catch (_) {
        // 失败就当没拿到，交给全局 401 拦截器处理（会登出+跳登录）
      }
    },
    async changePassword(payload) {
      return await apiChangePassword(payload)
    },
    logout() {
      this.token = ''
      this.user = null
      this._meTried = false
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    }
  }
})
