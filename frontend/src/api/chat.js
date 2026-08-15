import request from './request'
import { sseRequest } from './request'

// === Session ===
export function listSessions() {
  return request.get('/sessions')
}

export function createSession(data) {
  return request.post('/sessions', data)
}

export function renameSession(sessionId, data) {
  return request.patch(`/sessions/${sessionId}`, data)
}

export function deleteSession(sessionId) {
  return request.delete(`/sessions/${sessionId}`)
}

export function getMessages(sessionId) {
  return request.get(`/sessions/${sessionId}/messages`)
}

// === Chat ===
// 非流式
export function sendMessage(sessionId, data) {
  return request.post(`/chat/${sessionId}`, data)
}

// 流式 SSE
export function streamChat(sessionId, data, token, callbacks) {
  return sseRequest({
    url: `/api/chat/${sessionId}/stream`,
    data,
    token,
    ...callbacks
  })
}
