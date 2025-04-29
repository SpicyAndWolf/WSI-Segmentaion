import openslide
import cv2
import numpy as np
import os
from datetime import datetime
import matplotlib.pyplot as plt
import json

# patch_size
patch_size= 256

def get_tissue_part(slide_min, grey=None):
    # 如果未提供灰度图像，则将输入图像转换为灰度图
    if not grey:
        grey = cv2.cvtColor(slide_min, cv2.COLOR_BGR2GRAY)

    # 使用Canny边缘检测提取图像边缘
    Canny_grey = cv2.Canny(grey, 5, 50)  # 低阈值5，高阈值100

    # 定义形态学操作的核（3x3）
    kernel_size = 3
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    # 对边缘进行操作
    tissue_part = cv2.dilate(Canny_grey, kernel, iterations=3) # 膨胀, 连接断开的边缘
    tissue_part = cv2.erode(tissue_part, kernel, iterations=3) # 腐蚀, 去除小区域
    
    # 找到所有外部轮廓
    contours, _ = cv2.findContours(tissue_part, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_threshold = np.count_nonzero(tissue_part) * 0.02 # 面积阈值，小于该值的轮廓将被忽略

    # 保留所有超过面积阈值的轮廓
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > area_threshold:
            valid_contours.append(contour)
    
    # 创建一个空白图像，绘制所有有效轮廓。如果没有找到有效轮廓，打印警告，并返回全黑图像
    if not valid_contours:
        print("Warning: No contours found with area greater than threshold.")
        tissue_part = np.zeros_like(tissue_part)
    else:
        tissue_part = cv2.drawContours(np.zeros_like(tissue_part), valid_contours, -1, (255, 255, 255), -1)

    # 返回组织区域mask
    return tissue_part

def slide2patches(slide_fold, slide_file_name, patches_folder):
    # 开始计时
    startTime=datetime.now()

    # 设置工作分辨率级别和patch尺寸
    slide_level = 0
    patch_width, patch_height = (patch_size, patch_size)  # patch的宽度和高度
    
    # 打开WSI文件
    slide = openslide.OpenSlide(os.path.join(slide_fold, slide_file_name + ".svs"))
    width_max, height_max = slide.level_dimensions[0]
    
    # 获取各个分辨率级别的尺寸，并计算比例
    level_min = slide.level_count - 1
    width_min, height_min = slide.level_dimensions[level_min]
    width_current, height_current = slide.level_dimensions[slide_level]
    cox_min_to_max = width_max // width_min
    cox_current_to_max= width_max // width_current
    cox_min_to_current = width_current / width_min
    
    # 读取最低分辨率图像
    slide_min = np.array(slide.read_region((0, 0), level_min, (width_min, height_min)))[:, :, :3]
    
    # 找到核心组织
    tissue_part = get_tissue_part(slide_min)
        
    # 计算组织区域的边界框
    tissue_left_min, tissue_top_min, tissue_width_min, tissue_height_min = cv2.boundingRect(tissue_part)
    tissue_left = round(tissue_left_min * cox_min_to_max) 
    tissue_top = round(tissue_top_min * cox_min_to_max)
    tissue_width = round(tissue_width_min * cox_min_to_max)
    tissue_height = round(tissue_height_min * cox_min_to_max)
    
    # 加载geojson文件
    geojson_path=os.path.join(slide_fold, slide_file_name + ".geojson")
    with open(geojson_path, 'r') as f:
        geojson_data = json.load(f)

    # 提取多边形和分类信息，并转换坐标到 slide_level
    annotations = []
    classes = set() # 用于创建文件夹
    for feature in geojson_data['features']:
        if feature['geometry']['type'] == 'Polygon':
            coordinates = feature['geometry']['coordinates'][0]
            classification = feature['properties']['classification']['name']
            classes.add(classification)
            coordinates = [[int(x / cox_current_to_max), int(y / cox_current_to_max)] for x, y in coordinates]
            annotations.append({
                'coordinates': coordinates,
                'classification': classification
            })
    classes.add("Unknown")

    # 在循环前创建所有类别文件夹
    for class_name in classes:
        class_folder = os.path.join(patches_folder, class_name)
        os.makedirs(class_folder, exist_ok=True)

    # 创建类别掩码（在slide_level分辨率下）
    class_masks = {}
    for annotation in annotations:
        class_name = annotation['classification']
        if class_name not in class_masks:
            class_masks[class_name] = np.zeros((height_current, width_current), dtype=np.uint8)
        polygon = np.array(annotation['coordinates'], dtype=np.int32)
        cv2.fillPoly(class_masks[class_name], [polygon], 255)
    
    # 设置patches提取的起始坐标
    x, y = tissue_left, tissue_top

    # 开始提取patches
    while y + patch_height * cox_current_to_max <= tissue_top + tissue_height:
        while x + patch_width * cox_current_to_max <= tissue_left + tissue_width:
            # 计算patch在slide_level下的坐标
            patch_x = int(x / cox_current_to_max)
            patch_y = int(y / cox_current_to_max)
            
            # 计算patch在level_min下的中心点，用于初步筛选
            patch_center_min_x = int(patch_x / cox_min_to_current + (patch_size / cox_min_to_max / 2))
            patch_center_min_y = int(patch_y / cox_min_to_current + (patch_size / cox_min_to_max / 2))
            
            # 仅处理组织区域内的patch
            if tissue_part[patch_center_min_y, patch_center_min_x] > 0:
                # 提取patch图像
                patch = np.array(slide.read_region((x, y), slide_level, (patch_width, patch_height)), dtype=np.uint8)[:, :, :3]
                
                # 定义patch在掩码上的区域
                patch_mask_area = (slice(patch_y, patch_y + patch_height), slice(patch_x, patch_x + patch_width))
                
                # 计算每个类别的像素比例
                total_pixels = patch_width * patch_height
                class_pixel_counts = {}
                for class_name, mask in class_masks.items():
                    class_pixels = np.sum(mask[patch_mask_area] > 0)
                    class_pixel_counts[class_name] = class_pixels / total_pixels
                
                # 确定类别
                classification = "Unknown"
                min_ratio = 0.7 # 最小占比
                for class_name, ratio in class_pixel_counts.items():
                    if ratio > min_ratio:
                        classification = class_name
                        break
                
                # 保存patch
                class_folder = os.path.join(patches_folder, classification)
                patch_path = os.path.join(class_folder, f"{y}_{x}.png")
                cv2.imwrite(patch_path, patch)
            
            x += patch_width * cox_current_to_max
        y += patch_height*cox_current_to_max
        x = tissue_left

    # 打印时间
    print(f"a slide cost Time: {datetime.now() - startTime}")

def seg_patches(slide_fold, slide_files_name, res_fold):
    print("start turn slide to patches...")

    for slide_file_name in slide_files_name:
        # 创建存储patches的文件夹
        patches_folder = os.path.join(res_fold, slide_file_name, "origin-{}".format(patch_size))
        if(not os.path.exists(patches_folder)):
            os.makedirs(patches_folder)

        # 开始切分
        start = datetime.now()
        slide2patches(slide_fold, slide_file_name, patches_folder)
        print("cost time: " + str(datetime.now() - start))

if __name__ == "__main__":
    slide_fold = "/home/zyf/Database/WSI-notation/"
    res_fold = "/home/zyf/Projects/WSI/Patches/slidePatches/"
    slide_files_name = [
        "2001549007_101728"
        # "2004409012_141125"
    ]

    # 开始切分
    seg_patches(slide_fold, slide_files_name, res_fold)