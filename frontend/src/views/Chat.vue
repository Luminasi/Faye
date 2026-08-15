<template>
  <div class="chat-layout h-full">
    <!-- 侧边栏：会话列表 + 用户信息 -->
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="w-full mb-4" :icon="Plus" @click="handleNewSession">
          新建对话
        </el-button>
        <el-select
          v-model="selectedKBs"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择参与检索的知识库"
          style="width: 100%"
          size="small"
          @change="emitKBsChange"
        >
          <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
      </div>
      <SessionList
        :sessions="sessions"
        :active="activeId"
        @select="handleSelect"
        @rename="handleRename"
        @delete="handleDelete"
      />
      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="onUserCmd">
          <div class="user-info">
            <el-avatar :size="32" style="background:#409eff">{{ user?.username?.charAt(0).toUpperCase() }}</el-avatar>
            <div style="flex:1; overflow:hidden; margin-left: 8px;">
              <div class="u-name">{{ user?.username }}</div>
              <div class="u-role">{{ user?.role === 'admin' ? '管理员' : '普通用户' }}</div>
            </div>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="pwd"><el-icon><Lock /></el-icon> 修改密码</el-dropdown-item>
              <el-dropdown-item v-if="user?.role === 'admin'" command="kb"><el-icon><Management /></el-icon> 知识库管理</el-dropdown-item>
              <el-dropdown-item command="logout" divided><el-icon><SwitchButton /></el-icon> 退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-aside>

    <!-- 主区：对话 -->
    <el-main class="chat-main">
      <div v-if="!activeId" class="chat-empty">
        <el-empty description="点击左侧「新建对话」开始知识库问答" :image-size="160" />
      </div>
      <div v-else class="chat-area">
        <div class="messages" ref="msgBoxRef">
          <div v-if="messages.length === 0" class="empty-tip">
            <el-icon :size="36" color="#c0c4cc"><ChatLineSquare /></el-icon>
            <p>开始你的第一个问题吧</p>
            <el-tag type="info" v-for="t in tips" :key="t" style="margin: 4px">{{ t }}</el-tag>
          </div>
          <MessageBubble
            v-for="(m, i) in messages"
            :key="i"
            :msg="m"
            :is-self="m.role === 'user'"
          />
          <div v-if="streaming" class="msg-row assistant">
            <el-avatar :size="32" style="background:#67c23a">AI</el-avatar>
            <div class="bubble ai">
              {{ streamingContent || ' ' }}
              <span class="typing-cursor">▍</span>
            </div>
          </div>
        </div>
        <div class="input-bar">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="请输入你的问题，Enter发送，Shift+Enter换行"
            @keydown="onKeydown"
            :disabled="streaming"
          />
          <el-button type="primary" :icon="Promotion" :disabled="streaming || !question.trim()" @click="send">
            发送
          </el-button>
        </div>
      </div>
    </el-main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, ArrowDown, Lock, Management, SwitchButton, Promotion, ChatLineSquare
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { listSessions, createSession, renameSession, deleteSession, getMessages, streamChat } from '@/api/chat'
import SessionList from '@/components/SessionList.vue'
import MessageBubble from '@/components/MessageBubble.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const user = computed(() => userStore.user)
const sessions = ref([])
const activeId = ref(null)
const messages = ref([])
const selectedKBs = ref([])
const kbList = ref([])

const question = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const msgBoxRef = ref(null)

const tips = [
  '这款手机电池续航怎么样？',
  '笔记本电脑支持几年保修？',
  '冰箱出现E5错误码怎么办？',
  '退货政策是怎样的？'
]

async function refreshSessions() {
  sessions.value = await listSessions()
}
function emitKBsChange() {}

onMounted(async () => {
  try { await refreshSessions() } catch (_) {}
  // 如果有 sessionId 参数
  if (route.params.sessionId) {
    activeId.value = Number(route.params.sessionId)
    await loadMessages()
  } else if (sessions.value.length > 0) {
    handleSelect(sessions.value[0].id)
  }
})

watch(() => route.params.sessionId, (newId) => {
  if (newId) {
    activeId.value = Number(newId)
    loadMessages()
  }
})

async function handleNewSession() {
  const s = await createSession({ title: '新对话 ' + new Date().toLocaleString('zh-CN') })
  sessions.value.unshift(s)
  handleSelect(s.id)
}

function handleSelect(id) {
  activeId.value = id
  router.replace({ name: 'ChatSession', params: { sessionId: id } })
  loadMessages()
}

async function loadMessages() {
  if (!activeId.value) return
  try {
    messages.value = await getMessages(activeId.value)
  } catch (_) {
    messages.value = []
  }
  await nextTick()
  scrollBottom()
}

async function handleRename(s) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新标题', '重命名会话', {
      inputValue: s.title,
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    await renameSession(s.id, { title: value })
    s.title = value
  } catch (_) {}
}

async function handleDelete(s) {
  try {
    await ElMessageBox.confirm(`确认删除会话「${s.title}」？`, '提示', { type: 'warning' })
    await deleteSession(s.id)
    sessions.value = sessions.value.filter(x => x.id !== s.id)
    if (activeId.value === s.id) {
      activeId.value = null
      messages.value = []
      router.replace({ name: 'ChatRoot' })
    }
  } catch (_) {}
}

function onUserCmd(cmd) {
  if (cmd === 'pwd') router.push('/change-password')
  else if (cmd === 'kb') router.push('/admin/kb')
  else if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function scrollBottom() {
  nextTick(() => {
    if (msgBoxRef.value) msgBoxRef.value.scrollTop = msgBoxRef.value.scrollHeight
  })
}

async function send() {
  const q = question.value.trim()
  if (!q || streaming.value || !activeId.value) return
  messages.value.push({ role: 'user', content: q, created_at: new Date() })
  question.value = ''
  scrollBottom()

  streaming.value = true
  streamingContent.value = ''
  let finalSources = null
  let aborted = false

  streamChat(
    activeId.value,
    { question: q, kb_ids: selectedKBs.value.length ? selectedKBs.value : null, stream: true },
    userStore.token,
    {
      onData: (chunk) => {
        // 协议：META:开头是 JSON 元信息（sources等）
        if (chunk.startsWith('META:')) {
          try { finalSources = JSON.parse(chunk.slice(5))?.sources } catch (_) {}
          return
        }
        streamingContent.value += chunk
        scrollBottom()
      },
      onDone: () => {
        if (aborted) return
        messages.value.push({
          role: 'assistant',
          content: streamingContent.value || '（无回复内容）',
          sources: finalSources,
          created_at: new Date()
        })
        streaming.value = false
        streamingContent.value = ''
        scrollBottom()
      },
      onError: (err) => {
        aborted = true
        streaming.value = false
        streamingContent.value = ''
        ElMessage.error('问答失败：' + (err?.message || '未知错误'))
        // 回滚用户消息的移除
        scrollBottom()
      }
    }
  )
}
</script>

<style scoped>
.chat-layout { display: flex; height: 100vh; }
.sidebar {
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
}
.sidebar-header { padding: 16px; border-bottom: 1px solid #ebeef5; }
.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fafbfc;
}
.user-info { display: flex; align-items: center; cursor: pointer; }
.u-name { font-weight: 600; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.u-role { font-size: 12px; color: #909399; }

.chat-main { padding: 0; display: flex; flex-direction: column; background: #f7f9fc; }
.chat-empty { flex: 1; display: flex; align-items: center; justify-content: center; }
.chat-area { flex: 1; display: flex; flex-direction: column; height: 100%; }
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 15%;
}
.empty-tip { text-align: center; color: #909399; padding: 60px 0; }
.empty-tip p { margin: 10px 0 16px; }
.msg-row.assistant { display: flex; margin-bottom: 18px; }
.bubble.ai {
  margin-left: 10px;
  max-width: 78%;
  padding: 12px 16px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.typing-cursor { color: #409eff; animation: blink 0.9s steps(2) infinite; }
@keyframes blink { 50% { opacity: 0; } }

.input-bar {
  padding: 12px 15% 22px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.input-bar :deep(.el-textarea__inner) {
  font-size: 14px;
  border-radius: 10px;
}
</style>
