<script setup>
import { ElCheckbox, ElButton } from "element-plus";
import FileList from "./FileList.vue";

defineProps({
  fileList: Array,
  selectedFiles: Array,
  selectAll: Boolean,
  analysisStatus: Object,
  currentFile: String,
});

defineEmits(["update:selectAll", "update:selectedFiles", "viewFile", "startAnalysis"]);
</script>

<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <ElCheckbox :value="selectAll" @change="$emit('update:selectAll', $event)">全选</ElCheckbox>
      <ElButton @click="$emit('startAnalysis')" class="analysis-btn">开始分析</ElButton>
    </div>
    <FileList
      :file-list="fileList"
      :selected-files="selectedFiles"
      :analysis-status="analysisStatus"
      :current-file="currentFile"
      @toggle-file-selection="$emit('update:selectedFiles', $event)"
      @view-file="$emit('viewFile', $event)"
    />
  </div>
</template>

<style scoped>
.sidebar {
  width: 250px;
  background-color: rgb(249, 249, 249);
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
}

.sidebar-header {
  padding: 10px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
}

.analysis-btn {
  background-image: linear-gradient(to right, #6f7172 0%, #979789 51%, #003973 100%);
  margin-left: 50px;
  text-align: center;
  text-transform: uppercase;
  transition: 0.2s;
  background-size: 200% auto;
  color: white;
  box-shadow: 0 0 20px #eee;
  border-radius: 10px;
}

.analysis-btn:hover {
  background-position: right center;
  color: rgb(236, 236, 236);
  text-decoration: none;
}

.analysis-btn:active {
  transition: 0.2s;
  transform: scale(1.02);
  box-shadow: 0 0 10px #eee;
}
</style>
