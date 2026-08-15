<template>
  <div class="msg-row" :class="isSelf ? 'user' : 'assistant'">
    <el-avatar v-if="isSelf" :size="32" style="background:#409eff">我</el-avatar>
    <el-avatar v-else :size="32" style="background:#67c23a">AI</el-avatar>
    <div class="bubble" :class="isSelf ? 'me' : 'ai'">
      <div class="content">{{ msg.content }}</div>
      <SourceCard v-if="!isSelf && msg.sources && msg.sources.length" :sources="msg.sources" />
    </div>
    <el-avatar v-if="!isSelf" style="opacity:0; pointer-events:none" :size="32">AI</el-avatar>
  </div>
</template>

<script setup>
import SourceCard from './SourceCard.vue'
defineProps({
  msg: { type: Object, required: true },
  isSelf: { type: Boolean, default: false }
})
</script>

<style scoped>
.msg-row {
  display: flex;
  margin-bottom: 18px;
  align-items: flex-start;
  gap: 10px;
}
.msg-row.user { justify-content: flex-end; }
.bubble {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 10px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.bubble.me {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 2px;
}
.bubble.ai {
  background: #fff;
  border: 1px solid #ebeef5;
  border-top-left-radius: 2px;
}
.content { font-size: 15px; }
</style>
