<script setup>
import { ElButton, ElSwitch, ElInput, ElTooltip, ElIcon } from "element-plus";
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";

defineProps({
  isSidebarVisible: Boolean,
  isColorAdaptive: String,
  folderPath: String,
});

defineEmits(["toggleSidebar", "update:isColorAdaptive", "update:folderPath", "updateFileList"]);
</script>

<template>
  <div class="toolbar">
    <ElButton @click="$emit('toggleSidebar')" class="switch-fileList">
      <ElIcon>
        <component :is="isSidebarVisible ? ArrowLeft : ArrowRight" />
      </ElIcon>
      {{ isSidebarVisible ? "隐藏侧边栏" : "显示侧边栏" }}
    </ElButton>

    <ElTooltip content="自适应颜色，开启后将增加约10分钟的分析时间" placement="bottom">
      <div class="switch-wrapper">
        <div class="switch-wrapper">
          <ElSwitch
            :modelValue="isColorAdaptive"
            active-text="颜色自适应"
            inactive-text="默认"
            active-value="normalized"
            inactive-value="notNormalized"
            @update:modelValue="
              $emit('update:isColorAdaptive', $event);
              $emit('updateFileList');
            "
          />
        </div>
      </div>
    </ElTooltip>

    <div class="path-input-wrapper">
      <ElInput
        :value="folderPath"
        placeholder="请输入WSI文件夹路径"
        clearable
        @input="$emit('update:folderPath', $event)"
      />
      <ElButton @click="$emit('updateFileList')" class="update-fileList-btn">更新</ElButton>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  width: 100%;
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
</style>
