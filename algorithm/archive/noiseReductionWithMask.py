import pandas as pd
import matplotlib.pyplot as plt
import openslide
import numpy as np
import os
import argparse
from datetime import datetime
import math

# 定义 slide 名称列表
slide_names = [
    # "TCGA-D7-6524-01Z-00-DX1.ec1248f6-7d22-49c5-8300-673d25819e1d"
    "TCGA-BR-4253-11A-01-TS1.f9945942-7ec0-4b94-a3d6-663a04ce72ee"
    # "2001549007_101728"
]

# 基本变量
cox = 1
model_patch_size = 256
base_magnification = 40
dict_name = "epoch30+21-acc9819-finetune"
model_name = "resnet50-{}".format(model_patch_size)
# slide_fold = "/home/zyf/Database/WSI-notation/"
slide_fold = "/home/zyf/Database/TCGA/"

def process_slide(slide_name):
    """处理单个 slide，生成去噪后的半透明掩码并覆盖在原始图像上"""
    # 读取预测结果 CSV 文件
    res_path = f"/home/zyf/Projects/WSI/New/predictRes/{slide_name}"
    csv_file = os.path.join(res_path, f"predictions-{model_name}-{dict_name}.csv")
    df = pd.read_csv(csv_file, header=None, names=['patch', 'class', 'true_label', 'prob_0', 'prob_1', 'prob_2'])

    # 记录开始时间
    start = datetime.now()
    print(f"start processing {slide_name}...")

    # 打开WSI文件, 获取放大倍率，默认值为 40X
    slide = openslide.OpenSlide(os.path.join(slide_fold, slide_name + ".svs"))
    magnification = float(slide.properties.get('openslide.objective-power', 40))
    scale = magnification / base_magnification
    patch_size = int(256 * scale)  # 根据放大倍率调整提取尺寸

    # 计算图像的最大 x 和 y 坐标
    max_x = (df['patch'].str.split('_').str[1].astype(int).max() // cox) + patch_size
    max_y = (df['patch'].str.split('_').str[0].astype(int).max() // cox) + patch_size

    # 打开 svs 文件
    slide_path = os.path.join(slide_fold, f"{slide_name}.svs")
    slide = openslide.OpenSlide(slide_path)

    # 选择较低的分辨率级别（例如 level 2）进行可视化
    level = 2
    width, height = slide.level_dimensions[level]
    downsample = slide.level_downsamples[level]

    # 读取该级别的图像
    slide_image = slide.read_region((0, 0), level, (width, height))
    slide_image = np.array(slide_image)[:, :, :3]  # 转换为 numpy 数组，去除 alpha 通道

    # 创建一个与 slide_image 相同大小的掩码图像（RGBA）
    mask = np.zeros((height, width, 4), dtype=np.uint8)

    # 定义不同类别的颜色（RGBA，带透明度）
    colors = {
        0: (255, 255, 0, 128),  # 黄色，半透明
        1: (0, 255, 0, 128),    # 绿色，半透明
        2: (255, 0, 0, 128)     # 红色，半透明
    }

    # 创建 patch 集合和类别字典，用于去噪
    patch_set = set(df['patch'])  # 所有 patch 坐标的集合
    patch_to_class = df.set_index('patch')['class'].to_dict()  # patch 到类别的映射
    new_class = patch_to_class.copy()  # 复制一份用于存储去噪后的类别

    # 定义函数：获取邻居坐标
    def get_neighbors(y, x):
        neighbors = [
            (y - patch_size, x - patch_size), (y - patch_size, x), (y - patch_size, x + patch_size),
            (y, x - patch_size),                   (y, x + patch_size),
            (y + patch_size, x - patch_size), (y + patch_size, x), (y + patch_size, x + patch_size)
        ]
        # 过滤超出图像范围的邻居
        return [(ny, nx) for ny, nx in neighbors if ny >= 0 and nx >= 0 and ny < max_y and nx < max_x]

    # 去噪：调整 patch 类别
    for patch in df['patch']:
        coords = patch.split('_')
        y = int(coords[0])
        x = int(coords[1])
        current_class = patch_to_class[patch]
        
        # 获取邻居坐标和类别
        neighbors = get_neighbors(y, x)
        neighbor_classes = [patch_to_class[f"{ny}_{nx}"] for ny, nx in neighbors if f"{ny}_{nx}" in patch_set]
        
        # 如果所有邻居类别与当前 patch 不同，则调整为邻居中最常见的类别
        if neighbor_classes and all(cls != current_class for cls in neighbor_classes):
            class_counts = {}
            for cls in neighbor_classes:
                class_counts[cls] = class_counts.get(cls, 0) + 1
            max_count = max(class_counts.values())
            most_common_classes = [cls for cls, count in class_counts.items() if count == max_count]
            new_class[patch] = min(most_common_classes)
        else:
            new_class[patch] = current_class  # 保持原类别

    # 处理每个 patch 并绘制到掩码上
    for patch in df['patch']:
        coords = patch.split('_')
        y = int(coords[0])
        x = int(coords[1])
        cls = new_class[patch]
        
        # 计算 patch 在所选级别上的坐标和大小
        patch_x = math.ceil(x / downsample)
        patch_y = math.ceil(y / downsample)
        patch_w = math.ceil(patch_size / downsample)
        patch_h = math.ceil(patch_size / downsample)
        
        # 确保 patch 在图像范围内
        if patch_x + patch_w > width or patch_y + patch_h > height:
            continue
        
        # 在掩码上绘制半透明矩形
        color = colors[cls]
        mask[patch_y:patch_y + patch_h, patch_x:patch_x + patch_w] = color

    # 将掩码应用到原始图像上
    slide_image_rgba = np.zeros((height, width, 4), dtype=np.uint8)
    slide_image_rgba[:, :, :3] = slide_image
    slide_image_rgba[:, :, 3] = 255  # 设置原始图像为不透明

    # 使用 alpha 混合实现半透明效果
    alpha = mask[:, :, 3] / 255.0
    for c in range(3):
        slide_image_rgba[:, :, c] = (1 - alpha) * slide_image_rgba[:, :, c] + alpha * mask[:, :, c]

    # 显示和保存结果
    plt.figure(figsize=(12, 12))
    plt.imshow(slide_image_rgba)
    plt.axis('off')  # 关闭坐标轴
    output_path = os.path.join(res_path, f'noNoiseNew-{model_name}-{dict_name}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Processed {slide_name} in {datetime.now() - start}")

# 批量处理所有 slide
for slide_name in slide_names:
    process_slide(slide_name)