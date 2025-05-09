<script setup>
import ImageViewer from "./ImageViewer.vue";
import AnalysisResult from "./AnalysisResult.vue";

defineProps({
  currentFile: String,
  currentFileOriginUrl: String,
  currentFileStatus: Object,
  displayedImageType: String,
});

defineEmits(["switchImageType"]);
</script>

<template>
  <div class="content">
    <div class="analysis-container">
      <ImageViewer :image-url="currentFile ? currentFileOriginUrl : ''" title="原始图像" />
      <AnalysisResult
        :current-file-status="currentFileStatus"
        :displayed-image-type="displayedImageType"
        @switch-image-type="$emit('switchImageType', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.content {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.analysis-container {
  display: flex;
  gap: 20px;
  height: 100%;
}
</style>
