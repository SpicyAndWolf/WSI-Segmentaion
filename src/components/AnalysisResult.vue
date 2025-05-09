<script setup>
import { ElButton } from "element-plus";

defineProps({
  currentFileStatus: Object,
  displayedImageType: String,
});

defineEmits(["switchImageType"]);
</script>

<template>
  <div class="analysis-result">
    <h3>分析结果</h3>
    <div v-if="currentFileStatus.status === 'none'" class="status-message">
      {{ currentFileStatus.message }}
    </div>
    <div v-else-if="currentFileStatus.status === 'analyzing'" class="status-message">
      <span>{{ currentFileStatus.message }}</span>
      <div class="loading"></div>
    </div>
    <div v-else-if="currentFileStatus.status === 'queued'" class="status-message">
      <span>{{ currentFileStatus.message }}</span>
      <div class="loading"></div>
    </div>
    <div v-else-if="currentFileStatus.status === 'error'" class="status-message">
      {{ currentFileStatus.message }}
    </div>
    <div v-else-if="currentFileStatus.status === 'not_analyzed'" class="status-message">
      {{ currentFileStatus.message }}
    </div>
    <div v-else class="result-content">
      <div class="segmentation-image">
        <img :src="currentFileStatus.displayedImageUrl" class="image" />
        <div class="image-switch-buttons">
          <ElButton
            :type="displayedImageType === 'segmentation' ? 'primary' : 'default'"
            @click="$emit('switchImageType', 'segmentation')"
          >
            分割结果
          </ElButton>
          <ElButton
            :type="displayedImageType === 'hotSpot' ? 'primary' : 'default'"
            @click="$emit('switchImageType', 'hotSpot')"
          >
            热点图
          </ElButton>
          <ElButton
            :type="displayedImageType === 'tumorEdge' ? 'primary' : 'default'"
            @click="$emit('switchImageType', 'tumorEdge')"
          >
            肿瘤边缘
          </ElButton>
        </div>
      </div>
      <div class="tsr-result">
        <p>TSR: {{ currentFileStatus.tsr }}</p>
        <p>热点区域TSR: {{ currentFileStatus.tsr_hotspot }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-result {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.image {
  max-width: 100%;
  height: auto;
}

.image-switch-buttons {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 10px;
}

h3 {
  margin-bottom: 10px;
  text-align: center;
}

.status-message {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #606266;
}

.loading {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-top: 20px;
}

.result-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tsr-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-bottom: 20px;
}

.tsr-result p {
  margin: 0px;
  font-size: 16px;
  font-weight: bold;
  text-align: center;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
