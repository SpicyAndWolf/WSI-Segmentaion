const express = require("express");
const fs = require("fs").promises;
const router = express.Router();
const path = require("path");
const logger = require("../logger");
const { exec } = require("child_process");
const { json } = require("stream/consumers");

// 记录文件是否正在分析
const fileStatus = new Map();

async function isAnalyzed(file_name) {
  const res_base_folder = path.join(__dirname, "../public/predictRes");
  const subFolderPath = path.join(res_base_folder, file_name);
  const result = {
    isSegemented: false,
    isPredicted: false,
    jsonFiles: [],
  };

  // 检查子目录是否存在
  try {
    await fs.access(subFolderPath);
    result.isSegemented = true;
  } catch (error) {
    return result;
  }

  // 检查子目录下是否有json文件（是否已预测完全）
  if (result.isSegemented) {
    const files = await fs.readdir(subFolderPath);
    result.jsonFiles = files.filter((file) => path.extname(file).toLowerCase() === ".json");
    result.isPredicted = result.jsonFiles.length > 0;
  }

  return result;
}

async function processFile(folderPath, file, broadcast, fileStatus) {
  const fileKey = path.join(folderPath, file); // 使用完整路径作为唯一标识
  const pythonScript = path.join(__dirname, "../algorithm/main.py");
  let command = `python ${pythonScript} --slide_folder "${folderPath}" --slide_file_name "${file}"`;

  // 检查文件是否已分析过
  const file_name = path.basename(file, ".svs"); // 重要! 不标const时是全局变量！
  const isAnalyzedResult = await isAnalyzed(file_name);

  // 如果已经有分析结果了，直接返回
  if (isAnalyzedResult.isPredicted) {
    logger.debug(`文件 ${file} 已分析过`);

    // 获取 JSON 文件路径
    const res_base_folder = path.join(__dirname, "../public/predictRes");
    const jsonFilePath = path.join(res_base_folder, file_name, isAnalyzedResult.jsonFiles[0]);

    try {
      // 读取 JSON 文件
      const resultData = await fs.readFile(jsonFilePath, "utf-8");
      const result = JSON.parse(resultData);

      // 广播分析完成事件
      fileStatus.set(fileKey, { status: "completed", result });
      broadcast("file_processed", {
        file,
        status: "completed",
        tsr: result.tsr,
        segmentationFileName: result.segmentationFileName,
      });
    } catch (error) {
      logger.error(`读取文件 ${jsonFilePath} 失败: ${error.message}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        file,
        status: "error",
        message: `无法读取结果文件: ${error.message}`,
      });
    }
    return;
  }

  // 检查是否已分割过
  if (isAnalyzedResult.isSegemented) {
    command += ` --isSegmented True`;
  }

  // 执行 Python 脚本
  exec(command, async (error, stdout, stderr) => {
    if (error) {
      logger.error(`执行 Python 脚本时出错: ${error.message}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        file,
        status: "error",
        message: error.message,
      });
      return;
    }
    if (stderr) {
      logger.error(`Python 脚本 stderr: ${stderr}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        file,
        status: "error",
        message: stderr,
      });
      return;
    }
    try {
      // 解析 Python 脚本的输出
      const lines = stdout.trim().split("\n");
      let jsonOutput = null;
      for (const line of lines.reverse()) {
        try {
          jsonOutput = JSON.parse(line);
          if (jsonOutput.res_json_path) {
            break;
          }
        } catch (e) {
          continue;
        }
      }
      const jsonFilePath = jsonOutput.res_json_path;

      // 读取 JSON 文件
      const resultData = await fs.readFile(jsonFilePath, "utf-8");
      const result = JSON.parse(resultData);

      // 广播分析完成事件
      fileStatus.set(fileKey, { status: "completed", result });
      broadcast("file_processed", {
        file,
        status: "completed",
        tsr: result.tsr,
        segmentationFileName: result.segmentationFileName,
      });
    } catch (parseError) {
      logger.error(`处理 Python 输出或读取 JSON 文件时出错: ${parseError.message}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        file,
        status: "error",
        message: "无法解析 Python 脚本输出或读取 JSON 文件",
      });
    }
  });
}

// 获取文件列表接口
router.post("/getFileList", async (req, res) => {
  const { folderPath } = req.body;
  logger.info(`请求的文件夹路径: ${folderPath}`);

  if (!folderPath) {
    return res.status(400).json({
      success: false,
      message: "文件夹路径不能为空",
    });
  }

  try {
    // 读取文件夹内容
    const files = await fs.readdir(folderPath);
    const wsiFiles = files.filter((file) => file.endsWith(".svs")); // 过滤出 .svs 文件

    // 返回结果
    res.json({
      success: true,
      files: wsiFiles,
    });
  } catch (error) {
    logger.error(`读取文件夹${folderPath}失败: ${error.message}`);
    res.status(500).json({
      success: false,
      message: `无法读取文件夹: ${error.message}`,
    });
  }
});

router.post("/analyze", (req, res) => {
  const { files, folderPath } = req.body;
  logger.info("请求的文件", files);
  if (!files || !Array.isArray(files)) {
    return res.status(400).json({
      success: false,
      message: "Invalid request: files must be an array",
    });
  }

  const results = [];
  const toProcess = [];

  // 检查每个文件的状态
  for (const file of files) {
    const fileKey = path.join(folderPath, file); // 使用完整路径作为唯一标识
    const status = fileStatus.get(fileKey);

    if (status && status.status === "completed") {
      // 文件已处理完成，直接返回结果
      results.push({
        file,
        status: "completed",
        tsr: status.result.tsr,
        segmentationFileName: status.result.segmentationFileName,
      });
    } else if (status && status.status === "analyzing") {
      // 文件正在处理，返回正在处理状态
      console.log(`文件 ${file} 正在处理`);
      results.push({
        file,
        status: "analyzing",
      });
    } else {
      // 文件未处理，加入待处理列表
      toProcess.push(file);
      fileStatus.set(fileKey, { status: "analyzing", result: null });
      results.push({
        file,
        status: "analyzing",
      });
    }
  }

  // 返回当前文件的状态
  res.json({
    success: true,
    results,
  });

  // 处理新文件
  toProcess.forEach((file) => {
    processFile(folderPath, file, req.app.broadcast, fileStatus);
  });
});

module.exports = router;
