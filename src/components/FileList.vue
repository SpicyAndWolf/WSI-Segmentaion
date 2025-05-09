<script setup>
defineProps({
  fileList: Array,
  selectedFiles: Array,
  analysisStatus: Object,
  currentFile: String,
});

defineEmits(["toggleFileSelection", "viewFile"]);
</script>

<template>
  <div class="file-list">
    <div
      v-for="file in fileList"
      :key="file"
      class="file-item"
      :class="{
        selected: selectedFiles.includes(file),
        'current-file': file === currentFile,
        completed: analysisStatus[file]?.status === 'completed',
        analyzing: analysisStatus[file]?.status === 'analyzing',
        queued: analysisStatus[file]?.status === 'queued',
        error: analysisStatus[file]?.status === 'error',
      }"
      @click="$emit('toggleFileSelection', file)"
      @dblclick="$emit('viewFile', file)"
    >
      {{ file }}
    </div>
  </div>
</template>

<style scoped>
.file-list {
  flex: 1;
  overflow-y: auto;
}

.file-item {
  padding: 10px;
  padding-left: 15px;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.2s;
}

.file-item:hover {
  background-color: #f0f2f5;
  transform: translateX(4px);
}

.file-item.selected {
  background-color: rgb(227, 227, 227);
}

.file-item.completed {
  color: rgb(36, 211, 13);
}

.file-item.analyzing {
  color: rgb(14, 137, 238);
}

.file-item.queued {
  color: rgb(255, 153, 0);
}

.file-item.error {
  color: rgb(255, 0, 0);
}

.file-item.current-file {
  font-weight: 500;
  font-size: 18px;
  text-decoration: underline;
}
</style>
