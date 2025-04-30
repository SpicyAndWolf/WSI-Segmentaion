const express = require("express");
const fs = require("fs").promises;
const router = express.Router();
const path = require("path");
const logger = require("../logger");
const { exec } = require("child_process");
const { json } = require("stream/consumers");

// 状态文件夹路径
const statusDir = path.join(__dirname, "../status");

// 任务队列，存储待处理的文件，控制并发数量
const taskQueue = [];
const maxConcurrent = 2;
let currentProcessing = 0;

// 记录文件分析状态
const fileStatus = new Map();

// 确保状态文件夹存在
async function ensureStatusDir() {
  try {
    await fs.access(statusDir);
  } catch (error) {
    await fs.mkdir(statusDir);
  }
}

// 生成状态文件路径
function getStatusFilePath(fileKey) {
  const safeKey = Buffer.from(fileKey).toString("base64"); // 使用 Base64 编码避免特殊字符
  return path.join(statusDir, `${safeKey}.json`);
}

// 加载所有状态文件到 Map
async function loadFileStatus(fileStatus) {
  await ensureStatusDir();
  const files = await fs.readdir(statusDir);
  for (const file of files) {
    if (file.endsWith(".json")) {
      const filePath = path.join(statusDir, file);
      try {
        const data = await fs.readFile(filePath, "utf-8");
        const statusData = JSON.parse(data);
        const fileKey = Buffer.from(file.replace(".json", ""), "base64").toString();
        fileStatus.set(fileKey, statusData);
      } catch (error) {
        logger.error(`加载状态文件 ${file} 失败: ${error.message}`);
      }
    }
  }
}

// 保存状态到文件
async function saveFileStatus(fileKey, statusData) {
  await ensureStatusDir();
  const filePath = getStatusFilePath(fileKey);
  try {
    await fs.writeFile(filePath, JSON.stringify(statusData, null, 2));
  } catch (error) {
    logger.error(`保存状态文件 ${filePath} 失败: ${error.message}`);
  }
}

// 从任务队列中取出任务并处理，同时控制并发数量
async function processNext(broadcast, fileStatus) {
  if (currentProcessing >= maxConcurrent || taskQueue.length === 0) {
    return; // 如果达到并发上限或队列为空，则停止
  }

  currentProcessing++; // 增加当前处理计数
  const task = taskQueue.shift(); // 从队列中取出一个任务
  const { folderPath, file, isNormalized } = task;
  const fileKey = path.join(folderPath, file, isNormalized);

  // 设置文件状态为 analyzing
  fileStatus.set(fileKey, { status: "analyzing", result: null });

  // 广播状态
  broadcast("file_processed", {
    folderPath,
    file,
    isNormalized,
    status: "analyzing",
    result: null,
  });

  try {
    // 处理文件并等待完成
    await processFile(folderPath, file, broadcast, fileStatus, isNormalized);
  } catch (error) {
    logger.error(`处理文件 ${file} 时出错: ${error.message}`);
  } finally {
    // 处理完成后，减少计数并继续下一个任务
    currentProcessing--;
    processNext(broadcast, fileStatus);
  }
}

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
  return new Promise((resolve, reject) => {
    const fileKey = path.join(folderPath, file, isNormalized);
    const pythonScript = path.join(__dirname, "../algorithm/main.py");
    let command = `python ${pythonScript} --slide_folder ${folderPath} --slide_file_name ${file} --isNormalized ${isNormalized}`;

    // 检查文件是否已分析过
    const fileName = path.basename(file, ".svs");
    const folderName = path.basename(folderPath);
    const jsonFolderName = folderName + "_" + fileName + "_" + isNormalized;

    isAnalyzed(isNormalized, fileName, folderName)
      .then((isAnalyzedResult) => {
        // 如果已经有分析结果了，直接返回
        if (isAnalyzedResult.isPredicted) {
          logger.debug(`文件 ${file} 已分析过`);

          // 获取 JSON 文件路径
          const res_base_folder = path.join(__dirname, "../public/predictRes");
          const jsonFilePath = path.join(res_base_folder, jsonFolderName, isAnalyzedResult.jsonFiles[0]);

          fs.readFile(jsonFilePath, "utf-8")
            .then((resultData) => {
              const result = JSON.parse(resultData);

              // 广播分析完成事件
              fileStatus.set(fileKey, { status: "completed", result: result });
              saveFileStatus(fileKey, { status: "completed", result: result }); // 保存状态到文件
              broadcast("file_processed", {
                folderPath: folderPath,
                file: file,
                isNormalized: isNormalized,
                status: "completed",
                result: result,
              });
              resolve(); // 解析 Promise
            })
            .catch((error) => {
              const errorMessage = `读取文件 ${jsonFilePath} 失败: ${error.message}`;
              logger.error(errorMessage);
              fileStatus.set(fileKey, { status: "error", result: { message: errorMessage } });
              saveFileStatus(fileKey, { status: "error", result: { message: errorMessage } });
              broadcast("file_processed", {
                folderPath: folderPath,
                file: file,
                isNormalized: isNormalized,
                status: "error",
                result: { message: errorMessage },
              });
              resolve(); // 即使错误也解析 Promise，确保队列继续处理
            });
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
            const errorMessage = `Python 脚本 error: ${error.message}`;
            logger.error(errorMessage);
            fileStatus.set(fileKey, { status: "error", result: { message: errorMessage } });
            saveFileStatus(fileKey, { status: "error", result: { message: errorMessage } });
            broadcast("file_processed", {
              folderPath: folderPath,
              file: file,
              isNormalized: isNormalized,
              status: "error",
              result: { message: errorMessage },
            });
            resolve(); // 解析 Promise
            return;
          }
          if (stderr) {
            const errorMessage = `Python 脚本 stderr: ${stderr}`;
            logger.error(errorMessage);
            fileStatus.set(fileKey, { status: "error", result: { message: errorMessage } });
            saveFileStatus(fileKey, { status: "error", result: { message: errorMessage } });
            broadcast("file_processed", {
              folderPath: folderPath,
              file: file,
              isNormalized: isNormalized,
              status: "error",
              result: { message: errorMessage },
            });
            resolve(); // 解析 Promise
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
            saveFileStatus(fileKey, { status: "completed", result: result });
            broadcast("file_processed", {
              folderPath: folderPath,
              file: file,
              isNormalized: isNormalized,
              status: "completed",
              result: result,
            });
            resolve();
          } catch (parseError) {
            const errorMessage = `处理 Python 输出或读取 JSON 文件时出错: ${parseError.message}`;
            logger.error(errorMessage);
            fileStatus.set(fileKey, { status: "error", result: { message: errorMessage } });
            saveFileStatus(fileKey, { status: "error", result: { message: errorMessage } });
            broadcast("file_processed", {
              folderPath: folderPath,
              file: file,
              isNormalized: isNormalized,
              status: "error",
              result: { message: errorMessage },
            });
            resolve();
          }
        });
      })
      .catch((error) => {
        const errorMessage = `检查文件是否已分析过时出错: ${error.message}`;
        logger.error(errorMessage);
        fileStatus.set(fileKey, { status: "error", result: { message: errorMessage } });
        saveFileStatus(fileKey, { status: "error", result: { message: errorMessage } });
        broadcast("file_processed", {
          folderPath: folderPath,
          file: file,
          isNormalized: isNormalized,
          status: "error",
          result: { message: errorMessage },
        });
        resolve();
      });
  });
}

// 获取运行期间文件处理状态的路由
router.get("/getAnalysisStatus", (req, res) => {
  const fileInfos = Array.from(fileStatus.entries()).map(([key, value]) => {
    const parts = key.split(path.sep);
    const isNormalized = parts.pop();
    const file = parts.pop();
    const folderPath = parts.join(path.sep);
    return {
      folderPath: folderPath,
      file: file,
      isNormalized: isNormalized,
      status: value.status,
      result: value.result,
    };
  });

  res.json({
    success: true,
    fileInfos,
  });
});

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
    const wsiFiles = files.filter((file) => file.endsWith(".svs"));

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

  // 返回当前文件的状态
  const fileInfos = files.map((file) => {
    const fileKey = path.join(folderPath, file, isNormalized);
    const status = fileStatus.get(fileKey);
    if (status) {
      if (status.status === "completed") {
        return {
          folderPath,
          file,
          status: "completed",
          isNormalized,
          result: status.result,
        };
      } else if (status.status === "analyzing") {
        return {
          folderPath,
          file,
          status: "analyzing",
          isNormalized,
          result: null,
        };
      } else if (status.status === "queued") {
        return {
          folderPath,
          file,
          status: "queued",
          isNormalized,
          result: null,
        };
      } else if (status.status === "error") {
        fileStatus.set(fileKey, { status: "queued", result: null });
        taskQueue.push({ folderPath, file, isNormalized });
        return {
          folderPath,
          file,
          status: "queued",
          isNormalized,
          result: null,
        };
      }
    }
    // warning: 有并发导致的重复处理风险，现有的措施是限制按钮点击频率
    fileStatus.set(fileKey, { status: "queued", result: null });
    taskQueue.push({ folderPath, file, isNormalized });
    return {
      folderPath,
      file,
      status: "queued", // 未处理的文件标记为 queued
      isNormalized,
      result: null,
    };
  });

  // 返回答复
  res.json({
    success: true,
    fileInfos: fileInfos,
  });

  // 启动队列处理
  processNext(req.app.broadcast, fileStatus);
});

// 从文件系统加载状态文件到内存
loadFileStatus(fileStatus).then(() => {
  logger.info("文件状态已加载");
});

module.exports = router;
