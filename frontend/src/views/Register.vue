<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="always">
      <div class="brand"><h2>注册账号</h2><p class="sub">注册后即可使用知识库问答</p></div>
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="3-64位字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>
        <el-button type="primary" class="w-full" :loading="loading" @click="doRegister">注册</el-button>
        <div class="links"><router-link to="/login">已有账号？去登录</router-link></div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', email: '', password: '', confirm: '' })
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '长度 3-64', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_r, v, cb) => v === form.password ? cb() : cb(new Error('两次密码不一致')),
      trigger: 'blur'
    }
  ]
}

async function doRegister() {
  if (!await formRef.value.validate()) return
  loading.value = true
  try {
    await userStore.register({
      username: form.username,
      password: form.password,
      email: form.email || undefined
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
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
.brand { text-align: center; margin-bottom: 20px; }
.brand h2 { margin: 0 0 4px; }
.sub { color: #909399; margin: 0; }
.w-full { width: 100%; }
.links { text-align: center; margin-top: 16px; font-size: 14px; color: #409eff; }
</style>
