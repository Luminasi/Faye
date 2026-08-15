<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="always">
      <div class="brand">
        <el-icon :size="36" color="#409eff"><ChatDotRound /></el-icon>
        <h2>电商 RAG 知识库问答系统</h2>
        <p class="sub">基于 LangChain + 本地模型 · 企业级</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" @submit.prevent="doLogin">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名（admin）" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码（123456）"
            :prefix-icon="Lock" @keyup.enter="doLogin" />
        </el-form-item>
        <el-button type="primary" class="w-full" :loading="loading" @click="doLogin">登录</el-button>
        <div class="links">
          <router-link to="/register">还没有账号？立即注册</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: 'admin', password: '123456' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function doLogin() {
  if (!await formRef.value.validate()) return
  loading.value = true
  try {
    await userStore.login(form)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || (userStore.isAdmin ? '/admin/kb' : '/chat')
    router.push(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card { width: 420px; padding: 12px 6px; }
.brand { text-align: center; margin-bottom: 24px; }
.brand h2 { margin: 10px 0 4px; font-size: 22px; }
.sub { color: #909399; margin: 0 0 12px; }
.w-full { width: 100%; }
.links { text-align: center; margin-top: 16px; font-size: 14px; color: #409eff; }
</style>
