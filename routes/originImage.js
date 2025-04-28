const express = require("express");
const path = require("path");
const logger = require("../logger");
const fs = require("fs");
const router = express.Router();
const { exec } = require("child_process");

// 图片所在的目录
const originImagePath = path.join(__dirname, "../public", "originImage");
const pythonScript = path.join(__dirname, "../algorithm/utils/extractPng.py");

// 处理 predictRes 动态路由
router.post("/originImage", async (req, res) => {
  try {
    const { slide_file_name, slide_folder } = req.body;
    const slide_folder_name = path.basename(slide_folder); // 获取文件夹名称
    const slide_name = slide_file_name.split(".")[0];
    const img_file_name = slide_folder_name + "_" + slide_name + ".png";
    const img_path = path.join(originImagePath, img_file_name);

    // 检查文件是否存在
    if (fs.existsSync(img_path)) {
      return res.json({ success: true, message: "PNG 提取成功", img_file_name: img_file_name });
    }
    // 如果文件不存在，则提取图片
    else {
      const command = `python ${pythonScript} --slide_folder "${slide_folder}" --slide_file_name "${slide_file_name}"`;
      exec(command, async (error, stdout, stderr) => {
        if (error) {
          logger.error(`提取原图片时出错: ${error.message}`);
          return res.status(500).json({ success: false, message: "提取原图片失败" });
        }
        if (stderr) {
          logger.error(`提取原图片时出错: ${stderr}`);
          return res.status(500).json({ success: false, message: "提取原图片失败" });
        }
        return res.json({ success: true, message: "PNG 提取成功", img_file_name: img_file_name });
      });
    }
  } catch (err) {
    logger.error(`提取原图片时出错: ${err.message}`);
    return res.status(500).json({ success: false, message: "提取原图片失败" });
  }
});

module.exports = router;
