import cv2
import numpy as np
import os
import openslide
from datetime import datetime
import pandas as pd
import configparser
from utils.myLogger import setup_logger

# 设置日志记录器
logger = setup_logger()

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 基本变量
model_patch_size = int(config['DEFAULT']['model_patch_size'])
model_name = "resnet50-{}".format(model_patch_size)

def edgeDetect(slide_folder, slide_name, res_dir, isNormalized):
    """处理单个 slide，找到肿瘤区域边缘并可视化"""
    # 记录开始时间
    start = datetime.now()
    print(f"开始处理 {slide_name} 的肿瘤边缘检测...")

    # 确定dict_name
    config_type = 'DEFAULT'
    if isNormalized == "normalized":
        config_type = 'NORMALIZED'
    dict_name = config[config_type]['dict_name']
    
    # 打开 svs 文件获取缩略图
    slide_path = os.path.join(slide_folder, f"{slide_name}.svs")
    slide = openslide.OpenSlide(slide_path)
    
    # 选择最低分辨率级别
    level = slide.level_count - 1
    width, height = slide.level_dimensions[level]
    
    # 读取该级别的图像作为缩略图
    thumbnail = np.array(slide.read_region((0, 0), level, (width, height)))[:, :, :3]
    
    # 读取预测结果 CSV 文件
    csv_path = os.path.join(res_dir, f'predictions-{model_name}-{dict_name}.csv')
    if not os.path.exists(csv_path):
        print(f"预测 CSV 文件不存在: {csv_path}")
        return
    
    df = pd.read_csv(csv_path, header=0)
    
    # 提取 patch 坐标
    df['y'] = df['patch'].str.split('_').str[0].astype(int)
    df['x'] = df['patch'].str.split('_').str[1].astype(int)

    # 将 Stroma（类别 1）替换为 Tumor（类别 2）,目的是让肿瘤前缘的检测不只包含肿瘤区域
    df.loc[df['class'] == 1, 'class'] = 2
    
    # 获取高分辨率图像的尺寸
    width_high, height_high = slide.level_dimensions[0]
    
    # 计算缩放比例
    scale_x = width / width_high
    scale_y = height / height_high
    
    # 计算缩略图上 patch 的大小
    patch_width_low = int(model_patch_size * scale_x)
    patch_height_low = int(model_patch_size * scale_y)
    
    # 创建与缩略图大小相同的空白掩码
    tumor_mask = np.zeros((height, width), dtype=np.uint8)
    tumor_mask_area = height * width
    
    # 根据预测结果填充肿瘤区域
    for index, row in df.iterrows():
        if row['class'] == 2:  # 假设 2 表示 Tumor 类
            # 计算缩略图上的坐标
            x_low = int(row['x'] * scale_x)
            y_low = int(row['y'] * scale_y)
            # 填充肿瘤区域
            tumor_mask[y_low:y_low + patch_height_low, x_low:x_low + patch_width_low] = 255
    
    # 形态学操作优化掩码
    kernel = np.ones((3, 3), np.uint8)
    tumor_mask = cv2.morphologyEx(tumor_mask, cv2.MORPH_CLOSE, kernel)  # 闭操作：填充小空洞
    tumor_mask = cv2.morphologyEx(tumor_mask, cv2.MORPH_OPEN, kernel)   # 开操作：移除噪点
    
    # 找到肿瘤区域的轮廓
    contours, _ = cv2.findContours(tumor_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    
    # 过滤小面积的轮廓
    min_area = tumor_mask_area * 0.0005
    significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    # 创建结果可视化图像
    result_image = thumbnail.copy()
    
    # 在缩略图上绘制肿瘤边缘
    cv2.drawContours(result_image, significant_contours, -1, (255, 0, 0), 2)  # 红色边缘

    # 创建一个半透明的肿瘤区域覆盖层
    overlay = result_image.copy()
    cv2.drawContours(overlay, significant_contours, -1, (255, 0, 0), -1)  # 填充红色
    
    # 将原始图像与覆盖层混合
    alpha = 0.3  # 透明度
    result_image = cv2.addWeighted(overlay, alpha, result_image, 1 - alpha, 0)
    
    # 保存可视化结果
    img_name = f'tumor_edge-{model_name}-{dict_name}.png'
    output_path = os.path.join(res_dir, img_name)
    cv2.imwrite(output_path, cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR))
    
    logger.info(f"处理完成 {slide_name}，耗时: {datetime.now() - start}")
    logger.info(f"共找到 {len(significant_contours)} 个肿瘤区域。")
    logger.info(f"结果已保存至: {output_path}")
    return img_name

if __name__ == "__main__":
    slide_names = []
    for slide_name in slide_names:
        edgeDetect(slide_name)