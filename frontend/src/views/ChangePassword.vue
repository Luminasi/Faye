<template>
  <div class="page-wrap">
    <el-card shadow="never" style="max-width: 520px; margin: 60px auto;">
      <template #header><h3 style="margin:0">修改密码</h3></template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submit">确认修改</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
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
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const rules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入', trigger: 'blur' },
    {
      validator: (_r, v, cb) => v === form.new_password ? cb() : cb(new Error('两次密码不一致')),
      trigger: 'blur'
    }
  ]
}

async function submit() {
  if (!await formRef.value.validate()) return
  loading.value = true
  try {
    await userStore.changePassword({
      old_password: form.old_password,
      new_password: form.new_password
    })
    ElMessage.success('修改成功，请重新登录')
    userStore.logout()
    router.push('/login')
  } finally {
    loading.value = false
  }
}
</script>
