const express = require("express");
const fs = require("fs").promises;
const router = express.Router();
const path = require("path");
const logger = require("../logger");
const { exec } = require("child_process");
const { json } = require("stream/consumers");

// 记录文件是否正在分析
const fileStatus = new Map();

async function isAnalyzed(isNormalized, fileName, folderName) {
  const resBaseFolder = path.join(__dirname, "../public/predictRes");
  const subFolderName = folderName + "_" + fileName + "_" + isNormalized;
  const subFolderPath = path.join(resBaseFolder, subFolderName);
  const result = {
    isSegemented: false,
    isPredicted: false,
    justOriginSegmented: false, // 是否仅分割过原图
    jsonFiles: [],
  };

  // 检查子目录是否存在，如果存在则代表之前分割过了
  try {
    await fs.access(subFolderPath);
    result.isSegemented = true;
  } catch (error) {
    if (isNormalized == "notNormalized") return result;
    else {
      // 对于需要标准化的情况，检查原图子目录是否存在，如果存在则代表已有未标准化的patch
      const subFolderNameOrigin = folderName + "_" + fileName + "_" + "notNormalized";
      const subFolderPathOrigin = path.join(resBaseFolder, subFolderNameOrigin);
      try {
        await fs.access(subFolderPathOrigin);
        result.justOriginSegmented = true;
        return result; // 原图分割过，返回结果
      } catch (error) {
        return result; // 原图也未分割，返回默认值
      }
    }
  }

  // 检查子目录下是否有json文件（是否已预测完全）
  if (result.isSegemented) {
    const files = await fs.readdir(subFolderPath);
    result.jsonFiles = files.filter((file) => path.extname(file).toLowerCase() === ".json");
    result.isPredicted = result.jsonFiles.length > 0;
  }

  return result;
}

async function processFile(folderPath, file, broadcast, fileStatus, isNormalized) {
  const fileKey = path.join(folderPath, file, isNormalized); // 使用完整路径+isNormalized作为唯一标识
  const pythonScript = path.join(__dirname, "../algorithm/main.py");
  let command = `python ${pythonScript} --slide_folder ${folderPath} --slide_file_name ${file} --isNormalized ${isNormalized}`;

  // 检查文件是否已分析过
  const fileName = path.basename(file, ".svs");
  const folderName = path.basename(folderPath);
  const jsonFolderName = folderName + "_" + fileName + "_" + isNormalized;
  const isAnalyzedResult = await isAnalyzed(isNormalized, fileName, folderName);

  // 如果已经有分析结果了，直接返回
  if (isAnalyzedResult.isPredicted) {
    logger.debug(`文件 ${file} 已分析过`);

    // 获取 JSON 文件路径
    const res_base_folder = path.join(__dirname, "../public/predictRes");
    const jsonFilePath = path.join(res_base_folder, jsonFolderName, isAnalyzedResult.jsonFiles[0]);

    try {
      // 读取 JSON 文件
      const resultData = await fs.readFile(jsonFilePath, "utf-8");
      const result = JSON.parse(resultData);

      // 广播分析完成事件
      fileStatus.set(fileKey, { status: "completed", result: result });
      broadcast("file_processed", {
        folderPath: folderPath,
        file: file,
        isNormalized: isNormalized,
        status: "completed",
        tsr: result.tsr,
        tsr_hotspot: result.tsr_hotspot,
        segmentationFileName: result.segmentationFileName,
      });
    } catch (error) {
      logger.error(`读取文件 ${jsonFilePath} 失败: ${error.message}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        folderPath: folderPath,
        file: file,
        isNormalized: isNormalized,
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

  // 检查是否仅分割过原图
  if (isAnalyzedResult.justOriginSegmented) {
    command += ` --justOriginSegmented True`;
  }

  // 执行 Python 脚本
  exec(command, async (error, stdout, stderr) => {
    if (error) {
      logger.error(`执行 Python 脚本时出错: ${error.message}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        folderPath: folderPath,
        file: file,
        isNormalized: isNormalized,
        status: "error",
        message: error.message,
      });
      return;
    }
    if (stderr) {
      logger.error(`Python 脚本 stderr: ${stderr}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        folderPath: folderPath,
        file: file,
        isNormalized: isNormalized,
        status: "error",
        message: stderr,
      });
      return;
    }
    try {
      // 解析 Python 脚本的输出，获取json文件路径
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
      fileStatus.set(fileKey, { status: "completed", result: result });
      broadcast("file_processed", {
        folderPath: folderPath,
        file: file,
        isNormalized: isNormalized,
        status: "completed",
        tsr: result.tsr,
        tsr_hotspot: result.tsr_hotspot,
        segmentationFileName: result.segmentationFileName,
      });
    } catch (parseError) {
      logger.error(`处理 Python 输出或读取 JSON 文件时出错: ${parseError.message}`);
      fileStatus.set(fileKey, { status: "error", result: null });
      broadcast("file_processed", {
        folderPath: folderPath,
        file: file,
        isNormalized: isNormalized,
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
  const { files, folderPath, isNormalized } = req.body;
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
    const fileKey = path.join(folderPath, file, isNormalized); // 使用完整路径+所用模型作为唯一标识
    const status = fileStatus.get(fileKey);

    // 如果之前处理过该slide
    if (status) {
      if (status.status === "completed") {
        // 文件已处理完成，直接返回结果
        results.push({
          folderPath: folderPath,
          file: file,
          status: "completed",
          tsr: status.result.tsr,
          tsr_hotspot: status.result.tsr_hotspot,
          segmentationFileName: status.result.segmentationFileName,
          isNormalized: isNormalized,
        });
      } else if (status.status === "analyzing") {
        // 文件正在处理，返回正在处理状态
        results.push({
          folderPath: folderPath,
          file: file,
          status: "analyzing",
          isNormalized: isNormalized,
        });
      } else {
        // 文件处理失败，重新处理
        toProcess.push(file);
        fileStatus.set(fileKey, { status: "analyzing", result: null });
        results.push({
          folderPath: folderPath,
          file: file,
          status: "analyzing",
          isNormalized: isNormalized,
        });
      }
    }
    // 如果所用模型不同、或从未处理，当作从未处理过
    else {
      toProcess.push(file);
      fileStatus.set(fileKey, { status: "analyzing", result: null });
      results.push({
        folderPath: folderPath,
        file: file,
        status: "analyzing",
        isNormalized: isNormalized,
      });
    }
  }

  // 返回当前文件的状态
  res.json({
    success: true,
    results: results,
  });

  // 处理新文件
  toProcess.forEach((file) => {
    processFile(folderPath, file, req.app.broadcast, fileStatus, isNormalized);
  });
});

module.exports = router;
