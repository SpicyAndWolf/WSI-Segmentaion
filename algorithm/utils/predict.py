import os
import configparser
import torch
import torchvision.transforms as transforms
from datetime import datetime
import pandas as pd
import numpy as np
import openslide
import matplotlib.pyplot as plt
from utils.model.resnet50 import ResNet50
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from torchvision.datasets.folder import default_loader
import math
from scipy.ndimage import label
from collections import Counter
from utils.myLogger import setup_logger

# 设置日志记录器
logger = setup_logger()

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 获取配置文件内参数
ROOT_PATH = config['DEFAULT']['ROOT_PATH']
model_patch_size = int(config['DEFAULT']['model_patch_size'])
os.environ["CUDA_VISIBLE_DEVICES"] = config['DEFAULT']['CUDA_VISIBLE_DEVICES']
dict_name = config['DEFAULT']['dict_name']
base_magnification = int(config['DEFAULT']['base_magnification'])
slide_patches_base_folder = config['DEFAULT']['slide_patches_base_folder'].strip('"')

# 基本变量
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model_name = "resnet50-{}".format(model_patch_size)
dict_base_path = os.path.join(ROOT_PATH, "algorithm", "dicts")
dict_file_name = dict_name + ".pth"


# 判断图像是否几乎为白色
def is_almost_white(image, threshold=240):
    gray_image = image.convert('L')
    avg_pixel_value = sum(gray_image.getdata()) / len(gray_image.getdata())
    return avg_pixel_value > threshold

# 自定义数据集类
class PatchImageFolder(ImageFolder):
    def __init__(self, root, transform=None, target_transform=None, loader=default_loader, is_valid_file=None):
        self.root = root
        self.transform = transform
        self.target_transform = target_transform
        self.loader = loader
        self.is_valid_file = is_valid_file

        # 定义固定的类别列表和标签映射
        self.classes = ['Other', 'Stroma', 'Tumor', 'Unknown']
        self.class_to_idx = {cls_name: idx for idx, cls_name in enumerate(self.classes)}

        # 初始化样本列表
        self.samples = []
        self.targets = []
        self._load_samples()

    def _load_samples(self):
        """
        加载样本，处理可能缺失的类别。
        """
        for cls_name in self.classes:
            class_dir = os.path.join(self.root, cls_name)
            if not os.path.isdir(class_dir):
                logger.warning(f"Warning: Directory {class_dir} does not exist. Skipping.")
                continue
            for root, _, fnames in sorted(os.walk(class_dir, followlinks=True)):
                for fname in sorted(fnames):
                    path = os.path.join(root, fname)
                    if self.is_valid_file is None or self.is_valid_file(path):
                        self.samples.append((path, self.class_to_idx[cls_name]))
                        self.targets.append(self.class_to_idx[cls_name])

    def __getitem__(self, index):
        path, target = self.samples[index]
        img = self.loader(path)
        fileName = os.path.splitext(os.path.basename(path))[0]

        # 判断是否为几乎白色的 patch
        if is_almost_white(img):
            return self.transform(img), -1, fileName
        
        # 应用预处理
        if self.transform is not None:
            img = self.transform(img)
        if self.target_transform is not None:
            target = self.target_transform(target)
        return img, target, fileName

    def __len__(self):
        return len(self.samples)

# 降噪函数
def denoise(df, step=256):
    """对预测结果进行降噪，基于邻居调整分类"""
    coord_to_class = {(row['y'], row['x']): row['class'] for _, row in df.iterrows()}
    new_class = {}
    for _, row in df.iterrows():
        y, x = row['y'], row['x']
        current_class = row['class']
        neighbors = [
            (y - step, x - step), (y - step, x), (y - step, x + step),
            (y, x - step),                     (y, x + step),
            (y + step, x - step), (y + step, x), (y + step, x + step)
        ]
        neighbor_classes = [coord_to_class.get(neigh, None) for neigh in neighbors if neigh in coord_to_class]
        if neighbor_classes and all(cls != current_class for cls in neighbor_classes):
            class_counts = {}
            for cls in neighbor_classes:
                class_counts[cls] = class_counts.get(cls, 0) + 1
            max_count = max(class_counts.values())
            most_common_classes = [cls for cls, count in class_counts.items() if count == max_count]
            new_class[(y, x)] = min(most_common_classes)  # 选择最小的类别号作为默认规则
        else:
            new_class[(y, x)] = current_class
    df['class'] = df.apply(lambda row: new_class[(row['y'], row['x'])], axis=1)
    return df

def denoise_plus(df, step=256, threshold=5):
    """
    对预测结果进行降噪，将小于等于3个patch的联通区域更改为周围占比最大的类别
    """
    # 将DataFrame转换为坐标-类别字典
    coord_to_class = {(row['y'], row['x']): row['class'] for _, row in df.iterrows()}
    
    # 确定数据范围
    y_coords = df['y'].unique()
    x_coords = df['x'].unique()
    y_min, y_max = min(y_coords), max(y_coords)
    x_min, x_max = min(x_coords), max(x_coords)
    
    # 计算网格大小
    rows = int((y_max - y_min) / step) + 1
    cols = int((x_max - x_min) / step) + 1
    
    # 创建类别矩阵
    class_matrix = np.full((rows, cols), -1)  # 默认值-1表示无数据
    
    # 填充类别矩阵
    for (y, x), class_val in coord_to_class.items():
        i = int((y - y_min) / step)
        j = int((x - x_min) / step)
        if 0 <= i < rows and 0 <= j < cols:
            class_matrix[i, j] = class_val
    
    # 为每个类别创建二值掩码并找到连通区域
    all_changes = {}
    for class_val in range(3):  # 3个类别：0,1,2
        binary_mask = (class_matrix == class_val).astype(np.int32)
        labeled_array, num_features = label(binary_mask, structure=np.ones((3,3)))  # structure=np.ones((3,3))表示包括斜对角的8连通性
        
        # 检查每个连通区域
        for region_id in range(1, num_features + 1):
            region_points = np.where(labeled_array == region_id)
            region_size = len(region_points[0])
            
            # 如果连通区域的patch数量小于等于3
            if region_size <= threshold:
                # 收集这个区域的坐标
                small_region_coords = []
                for idx in range(len(region_points[0])):
                    i, j = region_points[0][idx], region_points[1][idx]
                    y = y_min + i * step
                    x = x_min + j * step
                    small_region_coords.append((y, x))
                
                # 收集周围的类别
                neighbor_classes = []
                for y, x in small_region_coords:
                    # 检查8个邻居
                    neighbors = [
                        (y - step, x - step), (y - step, x), (y - step, x + step),
                        (y, x - step),                      (y, x + step),
                        (y + step, x - step), (y + step, x), (y + step, x + step)
                    ]
                    for ny, nx in neighbors:
                        if (ny, nx) in coord_to_class and (ny, nx) not in small_region_coords:
                            neighbor_classes.append(coord_to_class[(ny, nx)])
                
                # 如果有邻居，确定主要类别
                if neighbor_classes:
                    counter = Counter(neighbor_classes)
                    surrounding_class = counter.most_common(1)[0][0]
                    
                    # 保存需要改变的坐标及其新类别
                    for y, x in small_region_coords:
                        all_changes[(y, x)] = surrounding_class
    
    # 应用所有变更
    for (y, x), new_class in all_changes.items():
        df.loc[(df['y'] == y) & (df['x'] == x), 'class'] = new_class
    
    return df

def predict(slide_folder, slide_name):
    # 加载模型权重
    model_path = os.path.join(dict_base_path, dict_file_name)
    state_dict = torch.load(model_path, map_location=device, weights_only=True)
    state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
    num_classes = 3
    use_cos = True
    cos_temp = 8
    model = ResNet50(num_classes=num_classes, use_cos=use_cos, cos_temp=cos_temp)
    model.load_state_dict(state_dict, strict=True)
    model = model.to(device)
    model.eval()

    # 定义图像预处理
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 设置patch路径
    image_dir = os.path.join(slide_patches_base_folder, slide_name, "origin-{}".format(model_patch_size))

    # 设置结果路径
    slide_folder_name = os.path.basename(slide_folder)
    res_dir_name= slide_folder_name+"_"+slide_name
    res_dir = os.path.join(ROOT_PATH, "public", "predictRes", res_dir_name)
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)

    # 创建 DataLoader
    batch_size = 64
    num_workers = 4
    dataset = PatchImageFolder(root=image_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    logger.info(f"start prediction for {slide_name}...")
    start = datetime.now()

    # 收集所有预测结果
    all_data = []
    for batch_images, batch_labels, batch_fileNames in dataloader:
        batch_images = batch_images.to(device)
        with torch.no_grad():
            outputs = model(batch_images)
            probabilities = torch.softmax(outputs, dim=1)
            predicted_classes = torch.argmax(probabilities, dim=1).cpu().numpy()
            probs = probabilities.cpu().numpy()
        for file_name, pred_class, true_label, prob in zip(batch_fileNames, predicted_classes, batch_labels, probs):
            if true_label == -1:  # 跳过几乎白色的patch
                continue
            all_data.append({
                'patch': file_name,
                'class': pred_class,
                'true_label': true_label.item(),
                'prob_0': prob[0],
                'prob_1': prob[1],
                'prob_2': prob[2]
            })

    # 打开WSI文件, 获取放大倍率，默认值为 40X。因为分类模型是在40倍下训练的
    slide = openslide.OpenSlide(os.path.join(slide_folder, slide_name + ".svs"))
    magnification = float(slide.properties.get('openslide.objective-power', 40))
    scale = magnification / base_magnification
    patch_size = int(model_patch_size * scale)

    # 创建 DataFrame 并进行降噪
    df = pd.DataFrame(all_data)
    df['y'] = df['patch'].apply(lambda p: int(p.split('_')[0]))
    df['x'] = df['patch'].apply(lambda p: int(p.split('_')[1]))
    df = denoise_plus(df, patch_size)
    # df =denoise(df, patch_size)

    # 保存降噪后的结果到 CSV
    output_file = os.path.join(res_dir, f"predictions-{model_name}-{dict_name}.csv")
    df.to_csv(output_file, index=False, columns=['patch', 'class', 'true_label', 'prob_0', 'prob_1', 'prob_2'])

    logger.info(f"predict for {slide_name} cost time: " + str(datetime.now() - start))
    return df, patch_size, res_dir

# 合并 patch 并生成带半透明掩码的图像
def mergePatches(slide_folder, slide_name, df, patch_size, res_dir):
    # 计时
    start = datetime.now()
    logger.info(f"start merging {slide_name}...")

    # 打开切片图像
    slide_path = os.path.join(slide_folder, slide_name + ".svs")
    slide = openslide.OpenSlide(slide_path)
    level = 2
    width, height = slide.level_dimensions[level]
    downsample = slide.level_downsamples[level]
    slide_image = slide.read_region((0, 0), level, (width, height))
    slide_image = np.array(slide_image)[:, :, :3]  # 转换为RGB数组

    # 创建掩码
    mask = np.zeros((height, width, 4), dtype=np.uint8)
    colors = {
        0: (255, 255, 0, 128),  # 黄色，半透明
        1: (0, 255, 0, 128),    # 绿色，半透明
        2: (255, 0, 0, 128)     # 红色，半透明
    }

    # 填充掩码
    for _, row in df.iterrows():
        y, x = row['y'], row['x']
        cls = row['class']
        patch_x = math.ceil(x / downsample)
        patch_y = math.ceil(y / downsample)
        patch_w = math.ceil(patch_size / downsample)
        patch_h = math.ceil(patch_size / downsample)
        if patch_x + patch_w > width or patch_y + patch_h > height:
            continue
        mask[patch_y:patch_y + patch_h, patch_x:patch_x + patch_w] = colors[cls]

    # 应用半透明掩码
    alpha = mask[:, :, 3] / 255.0
    for c in range(3):
        slide_image[:, :, c] = (1 - alpha) * slide_image[:, :, c] + alpha * mask[:, :, c]

    # 保存结果图像
    res_img_name = f'predictionImg-{model_name}-{dict_name}-{slide_name}.png'
    output_path = os.path.join(res_dir, res_img_name)
    plt.figure(figsize=(12, 12))
    plt.imshow(slide_image)
    plt.axis('off')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    # 打印合并时间
    logger.info(f"merge for {slide_name} cost time: " + str(datetime.now() - start))
    return res_img_name

def predict_slides(slide_folder, slide_files_name):
    for slide_file_name in slide_files_name:
        df, patch_size, res_dir = predict(slide_folder, slide_file_name)
        mergePatches(slide_folder, slide_file_name, df, patch_size, res_dir)


if __name__ == "__main__":
    slide_folder = "E:\Downloads\slides"
    slide_names = [
        # "TCGA-BR-4253-11A-01-TS1.f9945942-7ec0-4b94-a3d6-663a04ce72ee"
        # "TCGA-D7-6524-01Z-00-DX1.ec1248f6-7d22-49c5-8300-673d25819e1d"
        # "2001549007_101728"
        "1726363012"
    ]
    for slide_name in slide_names:
        df, patch_size, res_dir = predict(slide_folder, slide_name)
        mergePatches(slide_folder, slide_name, df, patch_size, res_dir)