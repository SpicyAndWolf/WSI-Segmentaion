import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import math
import openslide
import configparser
from utils.myLogger import setup_logger

# 设置日志记录器
logger = setup_logger()

# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 构造配置文件的绝对路径
config_path = os.path.join(script_dir, '..', '..','config.ini')

# 读取配置文件
config = configparser.ConfigParser()
config.read(config_path)

# 定义基本路径
ROOT_PATH = config['DEFAULT']['ROOT_PATH']
csv_base_folder = os.path.join(ROOT_PATH, "public", "predictRes")

# 基本变量
model_patch_size = int(config['DEFAULT']['model_patch_size'])
model_name = "resnet50-{}".format(model_patch_size)
dict_name = config['DEFAULT']['dict_name']
base_magnification = config['DEFAULT'].getfloat('base_magnification', 40)  # 基础放大倍数

def visualize_hotspot(res_folder, slide_name, grid, best_cy, best_cx, radius_grid):
    """
    可视化网格并标记热点区域。
    
    参数:
        grid (numpy.ndarray): 网格
        best_cy (int): 热点区域中心的y坐标（网格单位）
        best_cx (int): 热点区域中心的x坐标（网格单位）
        radius_grid (float): 热点区域的半径（网格单位）
        slide_name (str): 幻灯片名称
    """
    # 获取网格的形状，创建对应尺寸的RGB图像数组
    height, width = grid.shape
    rgb_grid = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 定义类别与颜色的RGB值映射
    color_rgb = {
        0: [255, 255, 0],  # yellow
        1: [0, 255, 0],    # green
        2: [255, 0, 0]     # red
    }
    
    # 填充RGB网格
    for y in range(height):
        for x in range(width):
            cls = grid[y, x]
            rgb_grid[y, x] = color_rgb.get(cls, [255, 255, 255])  # 白色表示未知类别
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(rgb_grid, interpolation='nearest')
    
    # 绘制热点区域
    circle = mpatches.Circle((best_cx, best_cy), radius_grid, color='blue', fill=False, linewidth=2)
    ax.add_patch(circle)
    
    # 添加图例
    patches = [
        mpatches.Patch(color='yellow', label='Class 0'),
        mpatches.Patch(color='green', label='Class 1'),
        mpatches.Patch(color='red', label='Class 2'),
        mpatches.Patch(color='blue', label='Hotspot Area')
    ]
    ax.legend(handles=patches, loc='upper right')
    ax.set_title(f"Hotspot Area for {slide_name}")
    ax.axis('off')
    
    # 保存图片
    hotspot_file_name = f"hotspot_{slide_name}.png"
    save_path = os.path.join(res_folder, hotspot_file_name)
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return hotspot_file_name

def calculate_hotspot_tsr(slide_folder, slide_name, mpp, magnification, delta=1, diameter_mm=2):
    """
    计算指定WSI的热点区域TSR。
    
    参数:
        slide_name (str): WSI的名称
        mpp (float): 每像素微米数 (microns per pixel)
        delta (int): 周边区域的宽度（网格单位），默认为1
        diameter_mm (float): 圆形区域的直径（毫米），默认为2
    """
    # 加载预测结果
    slide_folder_name = os.path.basename(slide_folder)
    csv_folder_name = slide_folder_name+"_"+slide_name
    csv_folder = os.path.join(csv_base_folder, csv_folder_name)
    csv_path = os.path.join(csv_folder, f"predictions-{model_name}-{dict_name}.csv")
    if not os.path.exists(csv_path):
        logger.error(f"Error: Prediction file {csv_path} does not exist.")
        return
    df = pd.read_csv(csv_path, header=0)
    df['class'] = df['class'].astype(int)

    # 提取坐标并构建网格
    df['y'] = df['patch'].apply(lambda p: int(p.split('_')[0]))
    df['x'] = df['patch'].apply(lambda p: int(p.split('_')[1]))
    
    y_unique = sorted(df['y'].unique())
    x_unique = sorted(df['x'].unique())
    y_coords = {y: idx for idx, y in enumerate(y_unique)}
    x_coords = {x: idx for idx, x in enumerate(x_unique)}
    
    grid = np.full((len(y_unique), len(x_unique)), -1)
    for _, row in df.iterrows():
        grid[y_coords[row['y']], x_coords[row['x']]] = row['class']

    # 计算patch_size
    scale = magnification / base_magnification
    patch_size = int(model_patch_size * scale)
    
    # 计算圆形区域的网格半径
    diameter_pixels = (diameter_mm * 1000) / mpp
    radius_grid = (diameter_pixels / 2) / patch_size
    
    # 搜索TSR最大的圆形区域
    max_tsr, best_circle_y, best_circle_x = 0, None, None
    grid_height, grid_width = grid.shape
    
    # 定义搜索步长以提高效率
    step = 5
    for circle_y in range(0, grid_height, step):
        for circle_x in range(0, grid_width, step):
            # 检查周边是否有肿瘤组织
            has_tumor_up = False
            has_tumor_down = False
            has_tumor_left = False
            has_tumor_right = False

            # 上方向
            for px in range(max(0, circle_x - delta), min(grid_width, circle_x + delta + 1)):
                py = int(circle_y - radius_grid - delta)
                if 0 <= py < grid_height and grid[py, px] == 2:
                    has_tumor_up = True
                    break
            
            # 下方向
            for px in range(max(0, circle_x - delta), min(grid_width, circle_x + delta + 1)):
                py = int(circle_y + radius_grid + delta)
                if 0 <= py < grid_height and grid[py, px] == 2:
                    has_tumor_down = True
                    break
            
            # 左方向
            for py in range(max(0, circle_y - delta), min(grid_height, circle_y + delta + 1)):
                px = int(circle_x - radius_grid - delta)
                if 0 <= px < grid_width and grid[py, px] == 2:
                    has_tumor_left = True
                    break

            # 右方向
            for py in range(max(0, circle_y - delta), min(grid_height, circle_y + delta + 1)):
                px = int(circle_x + radius_grid + delta)
                if 0 <= px < grid_width and grid[py, px] == 2:
                    has_tumor_right = True
                    break
            
            # 如果没有，不选择该区域
            if not (has_tumor_up and has_tumor_down and has_tumor_left and has_tumor_right):
                continue
            
            # 获取圆形区域内的patch
            patches_in_circle = []
            for py in range(grid_height):
                for px in range(grid_width):
                    distance = math.sqrt((py - circle_y)**2 + (px - circle_x)**2)
                    if distance <= radius_grid:
                        patches_in_circle.append((py, px))
            
            # 统计间质和肿瘤patch数量
            stroma_count = sum(1 for py, px in patches_in_circle if grid[py, px] == 1)
            tumor_count = sum(1 for py, px in patches_in_circle if grid[py, px] == 2)
            total_count = stroma_count + tumor_count
            if total_count == 0:
                continue
            tsr = (stroma_count / total_count) * 100
            
            # 更新最大TSR和最佳圆心
            if tsr > max_tsr:
                max_tsr, best_circle_y, best_circle_x = tsr, circle_y, circle_x
    
    # 输出结果
    hotspot_file_name= ""
    if best_circle_y is not None and best_circle_x is not None:
        logger.info(f"Slide: {slide_name}")
        logger.info(f"Hotspot center (grid coords): ({best_circle_y}, {best_circle_x})")
        logger.info(f"Hotspot TSR: {max_tsr:.2f}%")
        hotspot_file_name=visualize_hotspot(csv_folder, slide_name, grid, best_circle_y, best_circle_x, radius_grid)
    else:
        logger.warning(f"No suitable hotspot found for {slide_name}.")

    return max_tsr, hotspot_file_name

def calculate_all_tsr(slide_folder, slide_name):
    """
    计算指定 WSI 的肿瘤间质比 (TSR)，直接使用降噪后的 prediction.csv。
    """
    # 加载预测结果
    slide_folder_name = os.path.basename(slide_folder)
    csv_folder_name = slide_folder_name+"_"+slide_name
    csv_folder = os.path.join(csv_base_folder, csv_folder_name)
    csv_path = os.path.join(csv_folder, f"predictions-{model_name}-{dict_name}.csv")
    if not os.path.exists(csv_path):
        logger.error(f"Error: Prediction file {csv_path} does not exist.")
        return
    df = pd.read_csv(csv_path, header=0)

    # 统计各类别patch数量
    df['class'] = df['class'].astype(int)
    stroma_count = (df['class'] == 1).sum()
    tumor_count = (df['class'] == 2).sum()
    total_count = stroma_count + tumor_count
    
    # 计算 TSR
    if total_count == 0:
        logger.warning(f"Warning: No stroma or tumor patches found for {slide_name}. TSR cannot be calculated.")
        tsr = 0.0
    else:
        tsr = (stroma_count / total_count) * 100
    
    logger.info(f"Slide: {slide_name}")
    logger.info(f"Stroma patches: {stroma_count}")
    logger.info(f"Tumor patches: {tumor_count}")
    logger.info(f"TSR: {tsr:.2f}%")
    return tsr

def calculateTSR(slide_folder, slide_name):
    """
    计算指定 WSI 的肿瘤间质比 (TSR)，直接使用降噪后的 prediction.csv。
    """

    tsr = calculate_all_tsr(slide_folder, slide_name)
    slide = openslide.OpenSlide(os.path.join(slide_folder, slide_name + ".svs"))
    mpp = float(slide.properties.get('openslide.mpp-x', 0))
    magnification = float(slide.properties.get('openslide.objective-power', 40))
    tsr_hotspot, hotspot_file_name = calculate_hotspot_tsr(slide_folder, slide_name, mpp, magnification)
    return tsr, tsr_hotspot, hotspot_file_name


if __name__ == "__main__":
    slide_folder = "E:/Downloads/slides"
    slides_name = ["2001549007_101728"]
    
    for slide_name in slides_name:
        calculate_all_tsr(slide_folder, slide_name)
        slide = openslide.OpenSlide(os.path.join(slide_folder, slide_name + ".svs"))
        mpp = float(slide.properties.get('openslide.mpp-x', 0))
        magnification = float(slide.properties.get('openslide.objective-power', 40))
        calculate_hotspot_tsr(slide_folder, slide_name, mpp, magnification)