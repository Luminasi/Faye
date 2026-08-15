import request from './request'

// 注册
export function register(data) {
  return request.post('/auth/register', data)
}

// 登录（form-data 以兼容 OAuth2PasswordBearer）
export function login(data) {
  const form = new URLSearchParams()
  form.append('username', data.username)
  form.append('password', data.password)
  return request.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
}

// 获取当前用户
export function getMe() {
  return request.get('/me')
}

// 修改密码
export function changePassword(data) {
  return request.post('/auth/change-password', data)
}
