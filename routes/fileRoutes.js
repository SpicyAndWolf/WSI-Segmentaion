const express = require("express");
const fs = require("fs").promises;
const router = express.Router();
const path = require("path");
const { exec } = require("child_process");

async function processFile(folderPath, file, broadcast) {
  const pythonScript = path.join(__dirname, "../algorithm/main.py");
  const command = `python ${pythonScript} --slide_folder "${folderPath}" --slide_file_name "${file}"`;
  broadcast("file_processed", {
    file,
    status: "completed",
    tsr: 0.52,
    segmentationFileName:
      "predictionImg-resnet50-256-epoch30+21-acc9819-finetune-TCGA-D7-6524-01Z-00-DX1.ec1248f6-7d22-49c5-8300-673d25819e1d.png",
  });

  // exec(command, (error, stdout, stderr) => {
  //   if (error) {
  //     console.error(`执行 Python 脚本时出错: ${error.message}`);
  //     broadcast("file_processed", {
  //       file,
  //       status: "error",
  //       message: error.message,
  //     });
  //     return;
  //   }
  //   if (stderr) {
  //     console.error(`Python 脚本 stderr: ${stderr}`);
  //     broadcast("file_processed", {
  //       file,
  //       status: "error",
  //       message: stderr,
  //     });
  //     return;
  //   }
  //   console.log(`Python 脚本输出: ${stdout}`);
  //   try {
  //     const result = JSON.parse(stdout);
  //     broadcast("file_processed", {
  //       file,
  //       status: "completed",
  //       tsr: result.tsr,
  //       segmentationUrl: result.segmentationUrl,
  //     });
  //   } catch (parseError) {
  //     console.error(`解析 Python 输出时出错: ${parseError.message}`);
  //     broadcast("file_processed", {
  //       file,
  //       status: "error",
  //       message: "无法解析 Python 脚本输出",
  //     });
  //   }
  // });
}

// 获取文件列表接口
router.post("/getFileList", async (req, res) => {
  const { folderPath } = req.body;
  console.log("请求的文件夹路径:", folderPath);

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
    console.error("读取文件夹失败:", error);
    res.status(500).json({
      success: false,
      message: `无法读取文件夹: ${error.message}`,
    });
  }
});

router.post("/analyze", (req, res) => {
  const { files, folderPath } = req.body;
  if (!files || !Array.isArray(files)) {
    return res.status(400).json({
      success: false,
      message: "Invalid request: files must be an array",
    });
  }

  files.forEach((file) => {
    processFile(folderPath, file, req.app.broadcast);
  });

  res.json({ success: true, message: "Analysis started" });
});

module.exports = router;
