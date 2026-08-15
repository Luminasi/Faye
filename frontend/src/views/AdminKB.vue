<template>
  <div class="admin-layout h-full">
    <el-aside width="220px" class="sidebar">
      <div class="brand-wrap">
        <el-icon :size="26" color="#409eff"><Notebook /></el-icon>
        <span class="brand">知识库管理</span>
      </div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/admin/kb">
          <el-icon><Folder /></el-icon><span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon><span>返回问答</span>
        </el-menu-item>
        <el-menu-item index="/change-password">
          <el-icon><Lock /></el-icon><span>修改密码</span>
        </el-menu-item>
      </el-menu>
      <div class="side-foot">
        <el-dropdown trigger="click" @command="onCmd">
          <div class="user">
            <el-avatar :size="28" style="background:#409eff">{{ user?.username?.charAt(0).toUpperCase() }}</el-avatar>
            <span style="margin-left:8px">{{ user?.username }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout"><el-icon><SwitchButton /></el-icon> 退出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-aside>

    <el-main class="main">
      <div class="main-head">
        <div>
          <h3 style="margin:0">知识库管理</h3>
          <div class="sub">管理电商商品知识库、上传文档、管理授权</div>
        </div>
        <el-button type="primary" :icon="Plus" @click="showCreate = true">新建知识库</el-button>
      </div>

      <el-row :gutter="16">
        <el-col :span="8">
          <el-card shadow="never">
            <div class="kb-list-head">
              <strong>知识库列表</strong>
              <span style="color:#909399">{{ kbList.length }} 个</span>
            </div>
            <div class="kb-list" v-loading="loading">
              <div
                v-for="kb in kbList"
                :key="kb.id"
                class="kb-item"
                :class="{active: currentKB?.id === kb.id}"
                @click="selectKB(kb)"
              >
                <div class="kb-name">
                  <el-icon color="#409eff"><FolderOpened /></el-icon>
                  <span>{{ kb.name }}</span>
                </div>
                <div class="kb-desc" v-if="kb.description">{{ kb.description }}</div>
                <div class="kb-act">
                  <el-button link type="primary" size="small" @click.stop="onEdit(kb)">编辑</el-button>
                  <el-popconfirm title="确认删除该知识库？" @confirm="onDelete(kb.id)">
                    <template #reference>
                      <el-button link type="danger" size="small">删除</el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
              <el-empty v-if="kbList.length === 0 && !loading" description="还没有知识库，点击右上角新建" />
            </div>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card shadow="never" class="doc-card">
            <template #header>
              <div class="doc-head">
                <div>
                  <strong>{{ currentKB ? currentKB.name : '文档' }}</strong>
                  <span v-if="currentKB" style="color:#909399; margin-left:8px">
                    Collection: {{ currentKB.collection_name }}
                  </span>
                </div>
                <div>
                  <el-upload
                    :disabled="!currentKB"
                    :show-file-list="false"
                    :http-request="onUpload"
                    :before-upload="beforeUpload"
                    multiple
                  >
                    <el-button type="primary" :icon="Upload" :disabled="!currentKB" :loading="uploading">
                      上传文档
                    </el-button>
                  </el-upload>
                </div>
              </div>
            </template>
            <el-empty v-if="!currentKB" description="请先选择左侧知识库" />
            <template v-else>
              <el-table :data="docList" v-loading="docLoading" stripe size="small">
                <el-table-column prop="file_name" label="文件名" min-width="180" />
                <el-table-column prop="file_type" label="类型" width="80" align="center">
                  <template #default="{ row }">
                    <el-tag size="small">{{ row.file_type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="大小" width="90" align="center">
                  <template #default="{ row }">{{ (row.file_size/1024).toFixed(1) }} KB</template>
                </el-table-column>
                <el-table-column prop="chunk_count" label="分块数" width="80" align="center" />
                <el-table-column label="状态" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.status==='ready'" type="success" size="small">就绪</el-tag>
                    <el-tag v-else-if="row.status==='processing'" type="warning" size="small">处理中</el-tag>
                    <el-tooltip v-else :content="row.error_msg">
                      <el-tag type="danger" size="small">失败</el-tag>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="上传时间" width="170">
                  <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
                </el-table-column>
                <el-table-column label="操作" width="150" align="right" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" size="small" @click="onPreview(row)">分块预览</el-button>
                    <el-popconfirm title="确认删除该文档？" @confirm="onDeleteDoc(row.id)">
                      <template #reference>
                        <el-button link type="danger" size="small">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </template>
                </el-table-column>
              </el-table>
            </template>
          </el-card>
        </el-col>
      </el-row>
    </el-main>

    <!-- 新建/编辑知识库对话框 -->
    <el-dialog v-model="showCreate" :title="editingKB ? '编辑知识库' : '新建知识库'" width="460px">
      <el-form :model="kbForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="kbForm.name" placeholder="如：手机类商品知识库" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="kbForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate=false">取消</el-button>
        <el-button type="primary" @click="submitKB">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分块预览对话框 -->
    <el-dialog v-model="showPreview" title="文档分块预览" width="780px">
      <div v-loading="previewLoading">
        <div v-for="c in chunkList" :key="c.chunk_index" class="chunk-box">
          <div class="chunk-head">
            <el-tag size="small">Chunk #{{ c.chunk_index }}</el-tag>
            <span v-if="c.metadata?.page" style="color:#909399; font-size:12px; margin-left:8px">
              page: {{ c.metadata.page }}
            </span>
          </div>
          <div class="chunk-body">{{ c.content }}</div>
        </div>
        <el-empty v-if="previewChunks.length === 0 && !previewLoading" description="无分块数据" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Notebook, Folder, ChatDotRound, Lock, SwitchButton, Plus, Upload, FolderOpened
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  listKB, createKB, updateKB, deleteKB,
  listDocuments, uploadDocument, deleteDocument, previewChunks
} from '@/api/kb'

const router = useRouter()
const userStore = useUserStore()
const user = computed(() => userStore.user)
const activeMenu = computed(() => '/admin/kb')

const loading = ref(false)
const kbList = ref([])
const currentKB = ref(null)
const docList = ref([])
const docLoading = ref(false)
const uploading = ref(false)

const showCreate = ref(false)
const editingKB = ref(null)
const kbForm = reactive({ name: '', description: '' })

const showPreview = ref(false)
const previewLoading = ref(false)
const chunkList = ref([])

onMounted(async () => {
  await loadKBs()
})

async function loadKBs() {
  loading.value = true
  try {
    kbList.value = await listKB()
    if (kbList.value.length > 0) selectKB(kbList.value[0])
  } finally { loading.value = false }
}

function selectKB(kb) {
  currentKB.value = kb
  loadDocs()
}

async function loadDocs() {
  if (!currentKB.value) return
  docLoading.value = true
  try {
    docList.value = await listDocuments(currentKB.value.id)
  } finally { docLoading.value = false }
}

function onEdit(kb) {
  editingKB.value = kb
  kbForm.name = kb.name
  kbForm.description = kb.description || ''
  showCreate.value = true
}

async function submitKB() {
  if (!kbForm.name.trim()) return ElMessage.warning('请输入名称')
  try {
    if (editingKB.value) {
      await updateKB(editingKB.value.id, kbForm)
      ElMessage.success('已更新')
    } else {
      await createKB(kbForm)
      ElMessage.success('已创建')
    }
    showCreate.value = false
    kbForm.name = ''; kbForm.description = ''
    editingKB.value = null
    await loadKBs()
  } catch (_) {}
}

async function onDelete(id) {
  try {
    await deleteKB(id)
    ElMessage.success('已删除')
    if (currentKB.value?.id === id) { currentKB.value = null; docList.value = [] }
    await loadKBs()
  } catch (_) {}
}

function beforeUpload(file) {
  const okTypes = ['pdf','docx','doc','txt','md','markdown','html','htm','csv']
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!okTypes.includes(ext)) {
    ElMessage.error('不支持的文件类型，仅支持：' + okTypes.join('/'))
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件不能超过 50MB')
    return false
  }
  return true
}

async function onUpload({ file }) {
  if (!currentKB.value) return
  uploading.value = true
  try {
    await uploadDocument(currentKB.value.id, file)
    ElMessage.success(`文件 ${file.name} 上传成功，正在解析`)
    await loadDocs()
  } catch (_) {
  } finally { uploading.value = false }
}

async function onDeleteDoc(docId) {
  try {
    await deleteDocument(currentKB.value.id, docId)
    ElMessage.success('已删除')
    await loadDocs()
  } catch (_) {}
}

async function onPreview(row) {
  showPreview.value = true
  previewLoading.value = true
  chunkList.value = []
  try {
    chunkList.value = await previewChunks(currentKB.value.id, row.id)
  } finally { previewLoading.value = false }
}

function onCmd(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.admin-layout { display: flex; height: 100vh; }
.sidebar {
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
}
.brand-wrap {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #ebeef5;
}
.side-foot {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
}
.user { display: flex; align-items: center; cursor: pointer; }
.main { padding: 20px; background: #f5f7fa; overflow: auto; }
.main-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 4px 18px;
}
.sub { color: #909399; font-size: 13px; margin-top: 4px; }

.kb-list-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.kb-list { min-height: 380px; }
.kb-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.15s;
}
.kb-item:hover { border-color: #409eff; background: #f5faff; }
.kb-item.active { border-color: #409eff; background: #ecf5ff; }
.kb-name { display: flex; align-items: center; gap: 6px; font-weight: 600; }
.kb-desc { color: #909399; font-size: 12px; margin: 4px 0; }
.kb-act { text-align: right; }

.doc-card { min-height: 500px; }
.doc-head { display: flex; justify-content: space-between; align-items: center; }

.chunk-box {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 12px;
  overflow: hidden;
}
.chunk-head {
  background: #f5f7fa;
  padding: 6px 12px;
  border-bottom: 1px solid #ebeef5;
}
.chunk-body {
  padding: 10px 12px;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 14px;
}
</style>
