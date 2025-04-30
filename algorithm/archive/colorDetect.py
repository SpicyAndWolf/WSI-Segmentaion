import openslide
import numpy as np
import os
import cv2
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

def load_lowest_level_image(svs_path):
    slide = openslide.OpenSlide(svs_path)
    level = slide.level_count - 1  # 最低分辨率
    image = slide.read_region((0, 0), level, slide.level_dimensions[level])
    return np.array(image)

def rgb_to_lab(image):
    return cv2.cvtColor(image, cv2.COLOR_RGB2LAB)

def calculate_histogram(image_lab):
    hist_a = cv2.calcHist([image_lab], [1], None, [256], [0, 256])  # A通道
    hist_b = cv2.calcHist([image_lab], [2], None, [256], [0, 256])  # B通道
    hist_a = hist_a / hist_a.sum()  # 归一化
    hist_b = hist_b / hist_b.sum()
    return hist_a, hist_b

def calculate_average_histogram(svs_paths):
    hist_a_sum = np.zeros((256, 1))
    hist_b_sum = np.zeros((256, 1))
    for path in svs_paths:
        image = load_lowest_level_image(path)
        image_lab = rgb_to_lab(image)
        hist_a, hist_b = calculate_histogram(image_lab)
        hist_a_sum += hist_a
        hist_b_sum += hist_b
    avg_hist_a = hist_a_sum / len(svs_paths)
    avg_hist_b = hist_b_sum / len(svs_paths)
    return avg_hist_a, avg_hist_b

def bhattacharyya_distance(hist1, hist2):
    return np.sqrt(1 - np.sum(np.sqrt(hist1 * hist2)))

def save_to_csv(results, output_csv_path):
    df = pd.DataFrame(results, columns=['filename', 'distance_a', 'distance_b', 'avg_distance'])
    
    # 检查文件是否已存在
    file_exists = os.path.exists(output_csv_path)
    
    # 如果文件存在，追加数据（不写入表头）；否则写入表头
    df.to_csv(output_csv_path, mode='a', header=not file_exists, index=False)
    print(f"Results appended to {output_csv_path}")

def visualize_histogram(avg_hist, single_hist, hist_image_path):
    if not os.path.exists(os.path.dirname(hist_image_path)):
        os.makedirs(os.path.dirname(hist_image_path))
    plt.figure(figsize=(8, 5))

    # 绘制重叠的直方图
    plt.plot(avg_hist, color='green', label='Average Histogram', alpha=0.7, linestyle='--')  # 平均直方图
    plt.plot(single_hist, color='blue', label='Single Histogram', alpha=0.7, linestyle='-.')  # 单个直方图

    # 设置标题和标签
    plt.title('Histogram Comparison')
    plt.xlabel('Bin (0-255)')
    plt.ylabel('Normalized Value')
    plt.legend()  # 显示图例
    plt.grid(True, alpha=0.3)  # 添加网格线，便于观察

    plt.tight_layout()
    plt.savefig(hist_image_path)
    plt.close()
    print(f"histogram saved to {hist_image_path}")

def compare_new_image(new_svs_path, avg_hist_a, avg_hist_b, hist_dir):
    # 计算新图像的颜色直方图
    image = load_lowest_level_image(new_svs_path)
    image_lab = rgb_to_lab(image)
    hist_a, hist_b = calculate_histogram(image_lab)

    # 计算Bhattacharyya距离
    distance_a = bhattacharyya_distance(hist_a, avg_hist_a)
    distance_b = bhattacharyya_distance(hist_b, avg_hist_b)
    return distance_a, distance_b, hist_a, hist_b

# 示例用法
if __name__ == "__main__":
    # 基本路径定义
    svs_dir = "/home/zyf/Database/WSI-notation"
    svs_paths = [os.path.join(svs_dir, f) for f in os.listdir(svs_dir) if f.endswith('.svs')]
    new_svs_dir = '/home/zyf/Database/images1718'
    new_svs_paths = [os.path.join(new_svs_dir, f) for f in os.listdir(new_svs_dir) if f.endswith('.svs')]
    hist_dir = "/home/zyf/Projects/WSI/New/predictRes"
    hist_avg_path = os.path.join(hist_dir, "average_histograms.npz")

    # 计算/加载平均直方图
    if os.path.exists(hist_avg_path):
        print(f"Loading saved histograms from {hist_avg_path}")
        data = np.load(hist_avg_path)
        avg_hist_a = data['avg_hist_a']
        avg_hist_b = data['avg_hist_b']
    else:
        print("Calculating average histograms...")
        avg_hist_a, avg_hist_b = calculate_average_histogram(svs_paths)
        # 保存平均直方图
        os.makedirs(os.path.dirname(hist_avg_path), exist_ok=True)
        np.savez(hist_avg_path, avg_hist_a=avg_hist_a, avg_hist_b=avg_hist_b)
        print(f"Average histograms saved to {hist_avg_path}")

    results = []
    for new_svs_path in new_svs_paths:
        # 获取单个图像颜色直方图，计算距离
        new_distance_a, new_distance_b, hist_a, hist_b = compare_new_image(new_svs_path, avg_hist_a, avg_hist_b, hist_dir)
        results.append({
            'filename': Path(new_svs_path).name,
            'distance_a': new_distance_a,
            'distance_b': new_distance_b,
            'avg_distance': (new_distance_a + new_distance_b) / 2
        })

        # 可视化直方图
        file_name =os.path.splitext(os.path.basename(new_svs_path))[0]
        visualize_histogram(avg_hist_a, hist_a, os.path.join(hist_dir, "hist_a", f'{file_name}.png'))
        visualize_histogram(avg_hist_b, hist_b, os.path.join(hist_dir, "hist_b", f'{file_name}.png'))

    # 输出结果
    csv_path = os.path.join(hist_dir, "distances.csv")
    save_to_csv(results, csv_path)

