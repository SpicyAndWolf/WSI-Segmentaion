// logger.js
const { createLogger, format, transports } = require("winston");

const logger = createLogger({
  level: "info", // 设置默认日志级别
  format: format.combine(
    format.timestamp({ format: "YYYY-MM-DD HH:mm:ss" }), // 添加时间戳
    format.printf(({ timestamp, level, message }) => {
      return `${timestamp} ${level}: ${message}`;
    }),
    format.errors({ stack: true }), // 支持错误堆栈
    format.json() // 使用 JSON 格式以更好地记录对象
  ),
  transports: [
    // 输出到控制台
    new transports.Console(),
    // 输出到文件
    new transports.File({ filename: "logs/info.log" }), // 日志文件路径
    new transports.File({ filename: "logs/error.log", level: "error" }), // 错误日志单独文件
  ],
});

module.exports = logger;
