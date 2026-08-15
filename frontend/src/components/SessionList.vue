<template>
  <div class="session-list">
    <div class="list-title">我的会话</div>
    <div class="items">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="item"
        :class="{active: s.id === active}"
        @click="$emit('select', s.id)"
      >
        <el-icon class="icon"><ChatDotRound /></el-icon>
        <div class="info flex-1">
          <div class="title" :title="s.title">{{ s.title }}</div>
          <div class="time">{{ fmt(s.updated_at) }}</div>
        </div>
        <el-dropdown trigger="click" @command="(c) => onCmd(c, s)">
          <el-icon class="more"><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename"><el-icon><Edit /></el-icon> 重命名</el-dropdown-item>
              <el-dropdown-item command="delete" divided><el-icon><Delete /></el-icon> 删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <el-empty v-if="sessions.length === 0" description="暂无会话" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
import { ChatDotRound, MoreFilled, Edit, Delete } from '@element-plus/icons-vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  active: { type: [Number, String], default: null }
})
const emit = defineEmits(['select', 'rename', 'delete'])

function fmt(d) {
  const date = d ? new Date(d) : new Date()
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toTimeString().slice(0, 5)
  }
  return date.toLocaleDateString()
}
function onCmd(cmd, s) {
  if (cmd === 'rename') emit('rename', s)
  else if (cmd === 'delete') emit('delete', s)
}
</script>

<style scoped>
.session-list { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.list-title {
  padding: 10px 16px 6px;
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}
.items { flex: 1; overflow-y: auto; padding: 0 8px; }
.item {
  display: flex;
  align-items: center;
  padding: 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  gap: 8px;
}
.item:hover { background: #f5f7fa; }
.item.active { background: #ecf5ff; }
.icon { color: #909399; flex-shrink: 0; }
.item.active .icon { color: #409eff; }
.info { overflow: hidden; }
.title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #303133;
  font-weight: 500;
}
.time { font-size: 12px; color: #909399; margin-top: 2px; }
.more { color: #909399; padding: 4px; border-radius: 4px; }
.more:hover { background: #ebeef5; color: #606266; }
</style>
