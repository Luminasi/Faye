<template>
  <div class="source-wrap">
    <div class="source-bar" @click="show = !show">
      <el-icon style="margin-right:6px; color:#e6a23c"><Notebook /></el-icon>
      <span>📚 参考来源（{{ sources.length }}）</span>
      <el-icon style="margin-left:auto; transition: transform .2s" :style="{transform: show ? 'rotate(180deg)' : ''}">
        <ArrowDown />
      </el-icon>
    </div>
    <transition name="slide">
      <div v-show="show" class="source-list">
        <div v-for="(s, i) in sources" :key="i" class="source-item">
          <div class="s-head">
            <el-tag size="small" type="warning">#{{ i + 1 }}</el-tag>
            <span class="s-name">{{ s.doc_name }}</span>
            <span v-if="s.page != null" class="s-extra">页{{ s.page }}</span>
            <span v-if="s.chunk_index != null" class="s-extra">Chunk {{ s.chunk_index }}</span>
          </div>
          <div class="s-body">
            {{ s.snippet }}
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Notebook, ArrowDown } from '@element-plus/icons-vue'

defineProps({ sources: { type: Array, required: true } })
const show = ref(true)
</script>

<style scoped>
.source-wrap { margin-top: 12px; border-top: 1px dashed #ebeef5; padding-top: 10px; }
.source-bar {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #909399;
  font-size: 13px;
  padding: 4px 0;
}
.source-list { margin-top: 6px; }
.source-item {
  border: 1px solid #faecd8;
  background: #fdf6ec;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 6px;
}
.s-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px; }
.s-name { color: #606266; font-weight: 600; }
.s-extra { color: #909399; font-size: 12px; }
.s-body {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  max-height: 160px;
  overflow: auto;
  padding: 6px 8px;
  background: #fff;
  border-radius: 4px;
  white-space: pre-wrap;
}
.slide-enter-active, .slide-leave-active { transition: all .2s; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
