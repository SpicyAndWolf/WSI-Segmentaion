const createError = require("http-errors");
const express = require("express");
const path = require("path");
const cookieParser = require("cookie-parser");
const logger = require("morgan");
const cors = require("cors");
const fileRoutes = require("./routes/fileRoutes");
const { Server } = require("socket.io");
const http = require("http");

// 路由定义
const indexRouter = require("./routes/index");

// 主程序
const app = express();

// 基本组件
app.use(cors());
app.use(logger("dev"));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());

// 挂载路由
app.use(express.static(path.join(__dirname, "public")));
app.use("/predictRes", express.static(path.join(__dirname, "public", "predictRes")));
app.use("/", indexRouter);
app.use("/api", fileRoutes);

// 创建 Socket.IO 服务器
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
  },
});

// 存储所有连接的客户端
const clients = new Set();
io.on("connection", (socket) => {
  clients.add(socket);
  socket.on("disconnect", () => {
    clients.delete(socket);
  });
});

// 广播消息给所有连接的客户端
app.broadcast = function broadcast(event, data) {
  io.emit(event, data);
};

// 确保未定义的路由返回标准的 404 错误
app.use(function (req, res, next) {
  next(createError(404));
});

// 全局错误处理中间件
app.use((err, req, res, next) => {
  console.log(err);
  res.status(err.status || 500).json({
    error: {
      message: err.message,
      ...(req.app.get("env") === "development" && { stack: err.stack }),
    },
  });
});

module.exports = { app, server };
