import request from './request'

const PREFIX = '/admin/kb'

// 知识库列表
export function listKB() {
  return request.get(PREFIX)
}

// 创建知识库
export function createKB(data) {
  return request.post(PREFIX, data)
}

// 更新知识库
export function updateKB(kbId, data) {
  return request.patch(`${PREFIX}/${kbId}`, data)
}

// 删除知识库
export function deleteKB(kbId) {
  return request.delete(`${PREFIX}/${kbId}`)
}

// 文档列表
export function listDocuments(kbId) {
  return request.get(`${PREFIX}/${kbId}/documents`)
}

// 上传文档
export function uploadDocument(kbId, file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`${PREFIX}/${kbId}/documents/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded * 100) / evt.total))
      }
    }
  })
}

// 删除文档
export function deleteDocument(kbId, docId) {
  return request.delete(`${PREFIX}/${kbId}/documents/${docId}`)
}

// 文档分块预览
export function previewChunks(kbId, docId) {
  return request.get(`${PREFIX}/${kbId}/documents/${docId}/chunks`)
}

// 授权用户访问知识库
export function grantPermission(kbId, userId) {
  return request.post(`${PREFIX}/${kbId}/permissions`, { user_id: userId })
}

// 撤销授权
export function revokePermission(kbId, userId) {
  return request.delete(`${PREFIX}/${kbId}/permissions/${userId}`)
}

// 用户列表（供授权使用）
export function listUsers() {
  return request.get(`${PREFIX}/users`)
}
