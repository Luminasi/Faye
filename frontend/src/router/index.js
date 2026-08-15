import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { public: true, title: '注册' }
  },
  {
    path: '/',
    name: 'Root',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'ChatRoot',
    component: () => import('@/views/Chat.vue'),
    meta: { title: '知识库问答' }
  },
  {
    path: '/chat/:sessionId',
    name: 'ChatSession',
    component: () => import('@/views/Chat.vue'),
    meta: { title: '对话' }
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/ChangePassword.vue'),
    meta: { title: '修改密码' }
  },
  {
    path: '/admin/kb',
    name: 'AdminKB',
    component: () => import('@/views/AdminKB.vue'),
    meta: { title: '知识库管理', requireAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, _from, next) => {
  const userStore = useUserStore()
  document.title = (to.meta?.title ? to.meta.title + ' · ' : '') + '电商RAG问答系统'

  if (to.meta.public) return next()
  if (!userStore.isLoggedIn) return next({ name: 'Login', query: { redirect: to.fullPath } })

  // 登录用户首次进入任意受保护页面时（如刷新页面后），确保用户信息已从服务端同步
  // 失败时由全局 401 拦截器负责登出 + 跳登录，不会和登录成功提示撞在一起
  await userStore.ensureMe()

  if (to.meta.requireAdmin && !userStore.isAdmin) return next({ name: 'ChatRoot' })
  next()
})

export default router
