<script setup>
import { ref, computed } from "vue";
import { ElButton, ElSwitch, ElInput, ElTooltip, ElIcon, ElCheckbox, ElLoading } from "element-plus";
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import "element-plus/dist/index.css";

// ToolBar基本参数
const isSidebarVisible = ref(true); // 控制侧边栏显示/隐藏
const isColorAdaptive = ref(false); // 颜色自适应开关
const folderPath = ref(""); // 文件夹路径

// 文件列表相关
const fileList = ref([]); // 存储文件列表
const selectedFiles = ref([]); // 存储选中的文件名
const selectAll = ref(false); // 全选状态
const currentFile = ref(null); // 当前查看的文件

// 模拟文件列表数据
const mockFiles = ["wsi_sample1.svs", "wsi_sample2.svs", "wsi_sample3.svs", "wsi_sample4.svs"];

// 模拟分析状态和结果
const analysisStatus = ref({
  "wsi_sample1.svs": { status: "completed", tsr: 0.75, segmentationUrl: "https://i.vgy.me/QgKIBP.png" },
});
const isAnalyzing = ref(false); // 是否正在分析

// 切换侧边栏显示状态
const toggleSidebar = () => {
  isSidebarVisible.value = !isSidebarVisible.value;
};

// 更新文件列表
const updateFileList = () => {
  console.log("更新文件列表，路径：", folderPath.value);
  fileList.value = mockFiles;
};

// 全选/取消全选
const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedFiles.value = [...fileList.value];
  } else {
    selectedFiles.value = [];
  }
};

// 处理单个文件选中状态
const toggleFileSelection = (file) => {
  if (selectedFiles.value.includes(file)) {
    selectedFiles.value = selectedFiles.value.filter((f) => f !== file);
  } else {
    selectedFiles.value.push(file);
  }
  // 更新全选状态
  selectAll.value = selectedFiles.value.length === fileList.value.length;
};

// 查看文件分析结果
const viewFileAnalysis = (file) => {
  currentFile.value = file;
};

// 开始分析
const startAnalysis = () => {
  if (selectedFiles.value.length === 0) {
    console.log("请先选择文件");
    return;
  }
  isAnalyzing.value = true;
  console.log("开始分析选中的文件：", selectedFiles.value);

  // 模拟分析过程
  setTimeout(() => {
    selectedFiles.value.forEach((file) => {
      analysisStatus.value[file] = {
        status: "completed",
        tsr: Math.random().toFixed(2), // 模拟TSR结果
        segmentationUrl: "https://i.vgy.me/QgKIBP.png", // 模拟分割图
      };
    });
    isAnalyzing.value = false;
    // 如果当前查看的文件在分析列表中，更新显示
    if (currentFile.value && selectedFiles.value.includes(currentFile.value)) {
      currentFile.value = currentFile.value;
    }
  }, 2000); // 模拟2秒分析时间
};

// 计算当前文件的显示状态
const currentFileStatus = computed(() => {
  if (!currentFile.value) {
    return { status: "none", message: "请从左侧选择一个文件" };
  }
  if (isAnalyzing.value && selectedFiles.value.includes(currentFile.value)) {
    return { status: "analyzing", message: "正在分析..." };
  }
  if (analysisStatus.value[currentFile.value]) {
    return {
      status: analysisStatus.value[currentFile.value].status,
      tsr: analysisStatus.value[currentFile.value].tsr,
      segmentationUrl: analysisStatus.value[currentFile.value].segmentationUrl,
    };
  }
  return { status: "not_analyzed", message: "尚未分析" };
});
</script>

<template>
  <div class="container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <!-- 侧边栏控制按钮 -->
      <ElButton @click="toggleSidebar" type="Default" class="switch-fileList">
        <ElIcon>
          <component :is="isSidebarVisible ? ArrowLeft : ArrowRight" />
        </ElIcon>
        {{ isSidebarVisible ? "隐藏侧边栏" : "显示侧边栏" }}
      </ElButton>

      <!-- 颜色自适应开关 -->
      <ElTooltip content="自适应颜色，开启后将增加约10分钟的分析时间" placement="bottom">
        <div class="switch-wrapper">
          <ElSwitch v-model="isColorAdaptive" active-text="颜色自适应" inactive-text="默认" />
        </div>
      </ElTooltip>

      <!-- 文件夹路径输入 -->
      <div class="path-input-wrapper">
        <ElInput v-model="folderPath" placeholder="请输入WSI文件夹路径" clearable />
        <ElButton type="primary" @click="updateFileList" class="update-fileList-btn"> 更新 </ElButton>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 侧边栏 -->
      <div class="sidebar" v-if="isSidebarVisible">
        <!-- 功能按钮 -->
        <div class="sidebar-header">
          <ElCheckbox v-model="selectAll" @change="toggleSelectAll">全选</ElCheckbox>
          <ElButton @click="startAnalysis" class="analysis-btn"> 开始分析 </ElButton>
        </div>

        <!-- 文件名列表 -->
        <div class="file-list">
          <div
            v-for="file in fileList"
            :key="file"
            class="file-item"
            :class="{ selected: selectedFiles.includes(file), 'current-file': file === currentFile }"
            @click="toggleFileSelection(file)"
            @dblclick="viewFileAnalysis(file)"
          >
            {{ file }}
          </div>
        </div>
      </div>
      <!-- 主要内容区域 -->
      <div class="content">
        <div class="analysis-container">
          <!-- 原图 -->
          <div class="original-image">
            <h3>原始图像</h3>
            <img :src="currentFile ? 'https://i.vgy.me/QgKIBP.png' : ''" class="image" />
          </div>
          <!-- 分析结果 -->
          <div class="analysis-result">
            <h3>分析结果</h3>
            <div v-if="currentFileStatus.status === 'none'" class="status-message">
              {{ currentFileStatus.message }}
            </div>
            <div v-else-if="currentFileStatus.status === 'analyzing'" class="status-message">
              <span>{{ currentFileStatus.message }}</span>
              <div class="loading"></div>
            </div>
            <div v-else-if="currentFileStatus.status === 'not_analyzed'" class="status-message">
              {{ currentFileStatus.message }}
            </div>
            <div v-else class="result-content">
              <div class="segmentation-image">
                <img :src="currentFileStatus.segmentationUrl" alt="分割结果" class="image" />
              </div>
              <div class="tsr-result">
                <p>TSR: {{ currentFileStatus.tsr }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.toolbar {
  width: 100%;
  /* background-color: #f5f7fa; */
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding-top: 10px;
  padding-bottom: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.switch-fileList {
  margin-left: 10px;
  border-radius: 18px;
}

.switch-fileList:hover {
  transform: scale(1.05);
}

.switch-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.path-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
}

.update-fileList-btn {
  margin-left: 20px;
  margin-right: 10px;
  border-radius: 15px;
}

.update-fileList-btn:hover {
  transform: scale(1.02);
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 250px;
  background-color: rgb(249, 249, 249);
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
}

.sidebar-hidden {
  transform: translateX(-260px);
}

.sidebar-header {
  padding: 10px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
}

.analysis-btn {
  background-image: linear-gradient(to right, #6f7172 0%, #979789 51%, #003973 100%);
}
.analysis-btn {
  margin-left: 50px;
  text-align: center;
  text-transform: uppercase;
  transition: 0.2s;
  background-size: 200% auto;
  color: white;
  box-shadow: 0 0 20px #eee;
  border-radius: 10px;
  display: block;
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

.file-item.current-file {
  /* border: solid 2px rgb(36, 36, 36); */
  font-weight: 500;
  font-size: 18px;
  text-decoration: underline;
}

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

.original-image,
.analysis-result {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.image {
  max-width: 100%;
  height: auto;
}

.original-image h3,
.analysis-result h3 {
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

@media (max-width: 768px) {
  .toolbar {
    gap: 10px;
    flex-direction: column;
    align-items: center;
  }

  .path-input-wrapper {
    width: 100%;
  }

  .switch-fileList {
    width: 100%;
    text-align: center;
  }

  .sidebar {
    width: 200px;
  }

  .analysis-container {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 100%;
    position: absolute;
    z-index: 1000;
    height: calc(100vh - 50px);
  }
}
</style>
