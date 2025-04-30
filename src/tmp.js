const mapStatus = (fileInfo) => {
  if (fileInfo.status === "completed") {
    const fileName = fileInfo.file.slice(0, fileInfo.file.lastIndexOf("."));
    const folderName = fileInfo.folderPath.split(/[\\/]/).pop();
    const isNormalized = fileInfo.isNormalized;
    const segmentationFileName = fileInfo.result.segmentationFileName;
    const tsr = fileInfo.result.tsr;
    const tsr_hotspot = fileInfo.result.tsr_hotspot;
    const segmentationUrl = `${API_URL}/predictRes/${folderName}_${fileName}_${isNormalized}/${segmentationFileName}`;

    return {
      status: "completed",
      tsr: tsr,
      tsr_hotspot: tsr_hotspot,
      segmentationUrl: segmentationUrl,
    };
  } else if (fileInfo.status === "analyzing") {
    return {
      status: "analyzing",
      message: "正在分析...",
    };
  } else if (fileInfo.status === "queued") {
    return {
      status: "queued",
      message: "等待处理中...",
    };
  } else if (fileInfo.status === "error") {
    return {
      status: "error",
      message: fileInfo.result.message || "分析失败",
    };
  }
};
