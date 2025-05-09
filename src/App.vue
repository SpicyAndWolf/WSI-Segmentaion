<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import axios from "axios";
import { ElMessage } from "element-plus";
import { io } from "socket.io-client";
import ToolBar from "./components/ToolBar.vue";
import Sidebar from "./components/SideBar.vue";
import MainContent from "./components/MainContent.vue";

const API_URL = import.meta.env.VITE_API_URL;

const isSidebarVisible = ref(true);
const isColorAdaptive = ref("notNormalized");
const folderPath = ref("E:/Downloads/slides");
const fileList = ref([]);
const selectedFiles = ref([]);
const selectAll = ref(false);
const currentFile = ref(null);
const currentFileOriginUrl = ref("");
const displayedImageType = ref("segmentation");
const analysisStatus = ref({});

let socket = null;

const mapStatus = (fileInfo) => {
  if (fileInfo.status === "completed") {
    const fileName = fileInfo.file.slice(0, fileInfo.file.lastIndexOf("."));
    const folderName = fileInfo.folderPath.split(/[\\/]/).pop();
    const isNormalized = fileInfo.isNormalized;
    const segmentationFileName = fileInfo.result.segmentationFileName;
    const tsr = fileInfo.result.tsr;
    const tsr_hotspot = fileInfo.result.tsr_hotspot;
    const hotSpotName = fileInfo.result.hotspot_file_name;
    const tumorEdgeName = fileInfo.result.tumorEdge_file_name;
    const predict_res_dir = `${API_URL}/predictRes/${folderName}_${fileName}_${isNormalized}`;
    return {
      status: "completed",
      tsr,
      tsr_hotspot,
      segmentationUrl: `${predict_res_dir}/${segmentationFileName}`,
      hotSpotUrl: `${predict_res_dir}/${hotSpotName}`,
      tumorEdgeUrl: `${predict_res_dir}/${tumorEdgeName}`,
    };
  } else if (fileInfo.status === "analyzing") {
    return { status: "analyzing", message: "正在分析..." };
  } else if (fileInfo.status === "queued") {
    return { status: "queued", message: "等待处理中..." };
  } else if (fileInfo.status === "error") {
    return { status: "error", message: fileInfo.result.message || "分析失败" };
  }
};

onMounted(() => {
  socket = io(`${API_URL}`);
  socket.on("connect", () => console.log("Socket.IO 连接已建立"));
  socket.on("file_processed", (fileInfo) => {
    analysisStatus.value[fileInfo.file] = mapStatus(fileInfo);
    if (currentFile.value === fileInfo.file) {
      currentFile.value = fileInfo.file;
    }
  });
  socket.on("connect_error", (error) => {
    console.error("Socket.IO 连接错误:", error);
    ElMessage.error("Socket.IO 连接失败");
  });
});

onUnmounted(() => {
  if (socket) socket.disconnect();
});

const toggleSidebar = () => {
  isSidebarVisible.value = !isSidebarVisible.value;
};

const normalizePath = (path) => path.replace(/\\/g, "/");

const updateFileList = async () => {
  if (!folderPath.value) {
    ElMessage.error("请输入文件夹路径");
    return;
  }
  try {
    const fileListResponse = await axios.post(`${API_URL}/api/getFileList`, {
      folderPath: folderPath.value,
    });
    if (fileListResponse.data.success) {
      fileList.value = fileListResponse.data.files;
      ElMessage.success("文件列表更新成功");
      const statusResponse = await axios.get(`${API_URL}/api/getAnalysisStatus`);
      if (statusResponse.data.success) {
        analysisStatus.value = {};
        statusResponse.data.fileInfos.forEach((fileInfo) => {
          const normalizedStatusFolderPath = normalizePath(fileInfo.folderPath);
          const normalizedFolderPath = normalizePath(folderPath.value);
          if (normalizedStatusFolderPath === normalizedFolderPath && fileInfo.isNormalized === isColorAdaptive.value) {
            analysisStatus.value[fileInfo.file] = mapStatus(fileInfo);
          }
        });
        ElMessage.success("文件分析状态同步成功");
      } else {
        ElMessage.error(fileListResponse.data.message || "同步文件状态失败");
      }
    } else {
      ElMessage.error(fileListResponse.data.message || "获取文件列表失败");
    }
  } catch (error) {
    console.error("获取文件列表失败:", error);
    ElMessage.error("服务器错误，请检查后端服务");
  }
};

const toggleSelectAll = (value) => {
  selectAll.value = value;
  selectedFiles.value = value ? [...fileList.value] : [];
};

const toggleFileSelection = (file) => {
  if (selectedFiles.value.includes(file)) {
    selectedFiles.value = selectedFiles.value.filter((f) => f !== file);
  } else {
    selectedFiles.value.push(file);
  }
  selectAll.value = selectedFiles.value.length === fileList.value.length;
};

const extractPng = async (file) => {
  try {
    const response = await axios.post(`${API_URL}/api/originImage`, {
      slide_file_name: file,
      slide_folder: folderPath.value,
    });
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

const viewFile = async (file) => {
  currentFileOriginUrl.value = "";
  currentFile.value = file;
  await extractPng(file);
};

const switchImageType = (type) => {
  displayedImageType.value = type;
};

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
      response.data.fileInfos.forEach((fileInfo) => {
        analysisStatus.value[fileInfo.file] = mapStatus(fileInfo);
      });
    } else {
      ElMessage.error(response.data.message || "分析失败");
    }
  } catch (error) {
    console.error("分析失败:", error);
    ElMessage.error("服务器错误，请检查后端服务");
  }
};

const debounce = (fn, delay) => {
  let timer = null;
  return (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
};

const debouncedStartAnalysis = debounce(startAnalysis, 1000);

const currentFileStatus = computed(() => {
  if (!currentFile.value) {
    return { status: "none", message: "请从左侧选择一个文件" };
  }
  const status = analysisStatus.value[currentFile.value];
  if (status) {
    if (status.status === "completed") {
      const displayedImageUrl =
        displayedImageType.value === "segmentation"
          ? status.segmentationUrl
          : displayedImageType.value === "hotSpot"
          ? status.hotSpotUrl
          : status.tumorEdgeUrl;
      return {
        status: "completed",
        tsr: status.tsr,
        tsr_hotspot: status.tsr_hotspot,
        segmentationUrl: status.segmentationUrl,
        hotSpotUrl: status.hotSpotUrl,
        tumorEdgeUrl: status.tumorEdgeUrl,
        displayedImageUrl,
      };
    }
    return status;
  }
  return { status: "not_analyzed", message: "尚未分析" };
});
</script>

<template>
  <div class="container">
    <ToolBar
      :is-sidebar-visible="isSidebarVisible"
      :is-color-adaptive="isColorAdaptive"
      :folder-path="folderPath"
      @toggle-sidebar="toggleSidebar"
      @update:is-color-adaptive="isColorAdaptive = $event"
      @update:folder-path="folderPath = $event"
      @update-file-list="updateFileList"
    />
    <div class="main-content">
      <Sidebar
        v-if="isSidebarVisible"
        :file-list="fileList"
        :selected-files="selectedFiles"
        :select-all="selectAll"
        :analysis-status="analysisStatus"
        :current-file="currentFile"
        @update:select-all="toggleSelectAll"
        @update:selected-files="toggleFileSelection"
        @view-file="viewFile"
        @start-analysis="debouncedStartAnalysis"
      />
      <MainContent
        :current-file="currentFile"
        :current-file-origin-url="currentFileOriginUrl"
        :current-file-status="currentFileStatus"
        :displayed-image-type="displayedImageType"
        @switch-image-type="switchImageType"
      />
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

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
