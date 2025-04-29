<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import axios from "axios";
import { ElButton, ElSwitch, ElInput, ElTooltip, ElIcon, ElCheckbox, ElLoading, ElMessage } from "element-plus";
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import "element-plus/dist/index.css";
import { io } from "socket.io-client";

// 定义API端口
const API_URL = import.meta.env.VITE_API_URL;

// ToolBar基本参数
const isSidebarVisible = ref(true); // 控制侧边栏显示/隐藏
const isColorAdaptive = ref("notNormalized"); // 颜色自适应开关
const folderPath = ref("E:/Downloads/slides"); // 文件夹路径

// 文件列表相关
const fileList = ref([]); // 存储文件列表
const selectedFiles = ref([]); // 存储选中的文件名
const selectAll = ref(false); // 全选状态
const currentFile = ref(null); // 当前查看的文件
const currentFileOriginUrl = ref(""); // 当前查看的文件原图URL

// 分析状态和结果
const analysisStatus = ref({}); // 存储每个文件的分析状态

// WebSocket 连接
let socket = null;

onMounted(() => {
  socket = io(`${API_URL}`);
  socket.on("connect", () => {
    console.log("Socket.IO 连接已建立");
  });
  socket.on("file_processed", (data) => {
    if (data.status === "error") {
      // 分析失败
      ElMessage.error(`文件 ${data.file} 分析失败: ${data.message}`);

      // 更新分析状态
      analysisStatus.value[data.file] = {
        status: data.status,
        message: data.message,
      };
    } else if (data.status === "completed") {
      // 分析成功
      ElMessage.success(`文件 ${data.file} 分析完成`);
      const fileName = data.file.slice(0, data.file.lastIndexOf("."));
      const folderName = data.folderPath.split(/[\\/]/).pop();
      const isNormalized = data.isNormalized;
      const segmentationUrl = `${API_URL}/predictRes/${folderName}_${fileName}_${isNormalized}/${data.segmentationFileName}`;

      // 更新分析状态
      analysisStatus.value[data.file] = {
        status: "completed",
        tsr: data.tsr,
        tsr_hotspot: data.tsr_hotspot,
        segmentationUrl: segmentationUrl,
      };
    }
    if (currentFile.value === data.file) {
      currentFile.value = data.file;
    }
  });
  socket.on("connect_error", (error) => {
    console.error("Socket.IO 连接错误:", error);
    ElMessage.error("Socket.IO 连接失败");
  });
});

onUnmounted(() => {
  if (socket) {
    socket.disconnect();
  }
});

// 切换侧边栏显示状态
const toggleSidebar = () => {
  isSidebarVisible.value = !isSidebarVisible.value;
};

// 更新文件列表
const updateFileList = async () => {
  if (!folderPath.value) {
    ElMessage.error("请输入文件夹路径");
    return;
  }

  try {
    const response = await axios.post(`${API_URL}/api/getFileList`, {
      folderPath: folderPath.value,
    });

    if (response.data.success) {
      fileList.value = response.data.files;
      ElMessage.success("文件列表更新成功");
    } else {
      ElMessage.error(response.data.message || "获取文件列表失败");
    }
  } catch (error) {
    console.error("获取文件列表失败:", error);
    ElMessage.error("服务器错误，请检查后端服务");
  }
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
  selectAll.value = selectedFiles.value.length === fileList.value.length;
};

// 提取 PNG 图像
const extractPng = async (file) => {
  try {
    const response = await axios.post(`${API_URL}/api/originImage`, {
      slide_file_name: file,
      slide_folder: folderPath.value,
    });

    // 获取后端返回的文件名
    const originImageName = response.data.img_file_name;
    if (response.data.success) {
      currentFileOriginUrl.value = `${API_URL}/originImage/${originImageName}`;
    } else {
      ElMessage.error(response.data.message || "PNG 提取失败");
    }
  } catch (error) {
    console.error("提取 PNG 失败:", error);
    ElMessage.error("服务器错误");
  }
};

// 查看文件分析结果
const viewFile = async (file) => {
  currentFileOriginUrl.value = "";
  currentFileStatus.segmentationUrl = "";
  currentFileStatus.tsr = "";
  currentFileStatus.tsr_hotspot = "";
  currentFileStatus.status = "none";
  currentFile.value = file;
  await extractPng(file);
};

// 开始分析
const startAnalysis = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.error("请先选择文件");
    return;
  }

  try {
    const response = await axios.post(`${API_URL}/api/analyze`, {
      files: selectedFiles.value,
      folderPath: folderPath.value,
      isNormalized: isColorAdaptive.value,
    });
    if (response.data.success) {
      ElMessage.success("分析已开始");
      const results = response.data.results;

      // 更新每个选中文件（过滤后）的分析状态
      results.forEach((result) => {
        if (result.status === "completed") {
          // 对于分析已完成的
          const fileName = result.file.slice(0, result.file.lastIndexOf("."));
          const folderName = result.folderPath.split(/[\\/]/).pop();
          const isNormalized = result.isNormalized;
          const segmentationUrl = `${API_URL}/predictRes/${folderName}_${fileName}_${isNormalized}/${result.segmentationFileName}`;
          analysisStatus.value[result.file] = {
            status: "completed",
            tsr: result.tsr,
            tsr_hotspot: result.tsr_hotspot,
            segmentationUrl: segmentationUrl,
          };
        } else if (result.status === "analyzing") {
          // 如果文件正在处理
          analysisStatus.value[result.file] = {
            status: "analyzing",
          };
        }
      });
    } else {
      ElMessage.error(response.data.message || "分析失败");
    }
  } catch (error) {
    console.error("分析失败:", error);
    ElMessage.error("服务器错误，请检查后端服务");
  }
};

// 计算当前文件的显示状态
const currentFileStatus = computed(() => {
  if (!currentFile.value) {
    return { status: "none", message: "请从左侧选择一个文件" };
  }
  const status = analysisStatus.value[currentFile.value];
  if (status) {
    if (status.status === "completed") {
      return {
        status: "completed",
        tsr: status.tsr,
        tsr_hotspot: status.tsr_hotspot,
        segmentationUrl: status.segmentationUrl,
      };
    } else if (status.status === "error") {
      return { status: "error", message: status.message };
    } else if (status.status === "analyzing") {
      return { status: "analyzing", message: "正在分析..." };
    }
  }
  return { status: "not_analyzed", message: "尚未分析" };
});
</script>

<template>
  <div class="container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <!-- 侧边栏控制按钮 -->
      <ElButton @click="toggleSidebar" class="switch-fileList">
        <ElIcon>
          <component :is="isSidebarVisible ? ArrowLeft : ArrowRight" />
        </ElIcon>
        {{ isSidebarVisible ? "隐藏侧边栏" : "显示侧边栏" }}
      </ElButton>

      <!-- 颜色自适应开关 -->
      <ElTooltip content="自适应颜色，开启后将增加约10分钟的分析时间" placement="bottom">
        <div class="switch-wrapper">
          <ElSwitch
            v-model="isColorAdaptive"
            active-text="颜色自适应"
            inactive-text="默认"
            active-value="normalized"
            inactive-value="notNormalized"
          />
        </div>
      </ElTooltip>

      <!-- 文件夹路径输入 -->
      <div class="path-input-wrapper">
        <ElInput v-model="folderPath" placeholder="请输入WSI文件夹路径" clearable />
        <ElButton @click="updateFileList" class="update-fileList-btn"> 更新 </ElButton>
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
            :class="{
              selected: selectedFiles.includes(file),
              'current-file': file === currentFile,
              completed: analysisStatus[file]?.status === 'completed',
              analyzing: analysisStatus[file]?.status === 'analyzing',
              error: analysisStatus[file]?.status === 'error',
            }"
            @click="toggleFileSelection(file)"
            @dblclick="viewFile(file)"
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
            <img :src="currentFile ? `${currentFileOriginUrl}` : ''" class="image" />
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
            <div v-else-if="currentFileStatus.status === 'error'" class="status-message">
              {{ currentFileStatus.message }}
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
                <p>热点区域TSR: {{ currentFileStatus.tsr_hotspot }}</p>
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
  background-color: rgb(218, 219, 219);
  margin-left: 20px;
  margin-right: 10px;
  border-radius: 15px;
}

.update-fileList-btn:hover {
  background-color: rgb(236, 245, 255);
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

.file-item.completed {
  color: rgb(36, 211, 13);
}
.file-item.analyzing {
  color: rgb(14, 137, 238);
}

.file-item.error {
  color: rgb(255, 0, 0);
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
