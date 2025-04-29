import pandas as pd
import matplotlib.pyplot as plt
import openslide
import numpy as np
import os
import math
from datetime import datetime

# 定义 slide 名称列表
slide_names = [
    "2001549007_101728"
]

# 基本变量
patch_size = 256  # patch 的大小
dict_name = "epoch25_acc9765"  # 模型字典名称
# model_name = f"resnet50-{patch_size}"  # 模型名称
model_name = "efficientnet_b2"
slide_fold = "/home/zyf/Database/WSI-notation/"  # svs 文件路径

def process_slide(slide_name):
    """处理单个 slide，为分类失败的 patch 根据预测类别生成不同颜色的半透明掩码"""
    # 读取 missPatch.csv 文件
    res_path = f"/home/zyf/Projects/WSI/New/predictRes/{slide_name}"
    miss_patch_file = os.path.join(res_path, f"missPatch-{model_name}-{dict_name}.csv")
    miss_df = pd.read_csv(miss_patch_file, header=None, names=['patch', 'predicted_class', 'true_label', 'prob_0', 'prob_1', 'prob_2'])
    
    # 创建 patch 到预测类别的映射
    patch_to_pred_class = miss_df.set_index('patch')['predicted_class'].to_dict()

    # 记录开始时间
    start = datetime.now()
    print(f"开始处理 {slide_name}...")

    # 打开 svs 文件
    slide_path = os.path.join(slide_fold, f"{slide_name}.svs")
    slide = openslide.OpenSlide(slide_path)

    # 选择可视化级别（例如 level 2）
    level = 2
    width, height = slide.level_dimensions[level]
    downsample = slide.level_downsamples[level]

    # 读取该级别的图像
    slide_image = slide.read_region((0, 0), level, (width, height))
    slide_image = np.array(slide_image)[:, :, :3]  # 转换为 RGB 格式

    # 创建与图像大小相同的掩码（RGBA）
    mask = np.zeros((height, width, 4), dtype=np.uint8)

    # 定义颜色映射（RGBA，带透明度）
    colors = {
        0: (255, 255, 0, 128),  # 黄色，半透明
        1: (0, 255, 0, 128),    # 绿色，半透明
        2: (255, 0, 0, 128)     # 红色，半透明
    }

    # 为每个分类失败的 patch 生成掩码
    for patch, pred_class in patch_to_pred_class.items():
        coords = patch.split('_')
        y = int(coords[0])  # patch 的 y 坐标
        x = int(coords[1])  # patch 的 x 坐标
        
        # 计算 patch 在当前级别的位置和大小
        patch_x = math.ceil(x / downsample)
        patch_y = math.ceil(y / downsample)
        patch_w = math.ceil(patch_size / downsample)
        patch_h = math.ceil(patch_size / downsample)
        
        # 确保 patch 在图像范围内
        if patch_x + patch_w <= width and patch_y + patch_h <= height:
            # 根据预测类别选择颜色
            color = colors[pred_class]
            # 在掩码上绘制矩形
            mask[patch_y:patch_y + patch_h, patch_x:patch_x + patch_w] = color

    # 将掩码覆盖到原始图像
    slide_image_rgba = np.zeros((height, width, 4), dtype=np.uint8)
    slide_image_rgba[:, :, :3] = slide_image
    slide_image_rgba[:, :, 3] = 255  # 原始图像完全不透明

    # 使用 alpha 混合
    alpha = mask[:, :, 3] / 255.0
    for c in range(3):
        slide_image_rgba[:, :, c] = (1 - alpha) * slide_image_rgba[:, :, c] + alpha * mask[:, :, c]

    # 保存结果图像
    plt.figure(figsize=(24, 24))
    plt.imshow(slide_image_rgba)
    plt.axis('off')  # 关闭坐标轴
    output_path = os.path.join(res_path, f'missPatchMaskColored-{model_name}-{dict_name}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"处理 {slide_name} 完成，用时 {datetime.now() - start}")

# 批量处理所有 slide
for slide_name in slide_names:
    process_slide(slide_name)