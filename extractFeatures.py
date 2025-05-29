import os
import torch
import pandas as pd
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
from model.resnet50 import ResNet50
from normalizePatch import normalizePatch
import configparser
import openslide
import cv2

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 获取配置文件内参数
ROOT_PATH = config['DEFAULT']['ROOT_PATH']
model_patch_size = int(config['DEFAULT']['model_patch_size'])
os.environ["CUDA_VISIBLE_DEVICES"] = config['DEFAULT']['CUDA_VISIBLE_DEVICES']
base_magnification = int(config['DEFAULT']['base_magnification'])
patches_base_folder = config['DEFAULT']['patches_base_folder']

# 基本变量
dict_base_path = os.path.join(ROOT_PATH, "algorithm", "dicts")
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model_name = "resnet50-{}".format(model_patch_size)

def get_slide_patch(slide_fold, slide_file_name, patches_dir, patch_list, isNormalized = "notNormalized", model_patch_size=256):
    # 设置工作分辨率级数
    slide_level = 0

    # 打开WSI文件
    slide = openslide.OpenSlide(os.path.join(slide_fold, slide_file_name + ".svs"))

    # 获取放大倍率，默认值为 40X
    magnification = float(slide.properties.get('openslide.objective-power', 40))
    scale = magnification / base_magnification
    extract_size = int(model_patch_size * scale)  # 根据放大倍率调整提取尺寸

    # 缩放到目标尺寸 256x256
    if scale > 1:
        interpolation = cv2.INTER_AREA  # 缩小图像
    else:
        interpolation = cv2.INTER_CUBIC  # 放大图像

    # 提取patch图像
    for patch_name in patch_list:
        y, x = map(int, patch_name.split('_'))
        patch = np.array(slide.read_region((x, y), slide_level, (extract_size, extract_size)), dtype=np.uint8)[:, :, :3]
        patch = cv2.resize(patch, (model_patch_size, model_patch_size), interpolation=interpolation)

        # 保存patch
        class_folder = os.path.join(patches_dir,"Unknown")
        if not os.path.exists(class_folder):
            os.makedirs(class_folder)
        patch_path = os.path.join(class_folder, f"{y}_{x}.png")
        cv2.imwrite(patch_path, patch)
        patch = None

    # 关闭WSI文件
    slide.close()

    # 如果需要归一化patch图像, 则调用normalizePatch函数
    if(isNormalized == "normalized"):
        normalizePatch(patches_dir, patches_dir)
    

# 自定义数据集类，用于加载特定的patch图像
class PatchDataset(Dataset):
    def __init__(self, patches_dir, patch_list, transform=None):
        self.patches_dir = patches_dir
        self.patch_list = patch_list
        self.transform = transform
        
    def __len__(self):
        return len(self.patch_list)
    
    def __getitem__(self, idx):
        patch_name = self.patch_list[idx]
        y, x = patch_name.split('_')
        class_folder = 'Unknown'
        
        # 尝试在类别文件夹中查找图像
        img_path = None
        temp_path = os.path.join(self.patches_dir, class_folder, f"{patch_name}.png")
        if os.path.exists(temp_path):
            img_path = temp_path
        
        if img_path is None:
            raise FileNotFoundError(f"找不到patch: {patch_name}")
            
        img = Image.open(img_path).convert('RGB')    
        if self.transform:
            img = self.transform(img)
            
        return img, patch_name

# 计算置信度的函数
def calculate_confidence(probs):
    # 使用最大概率与第二大概率的差值作为置信度
    sorted_probs = np.sort(probs)[::-1]
    return sorted_probs[0] - sorted_probs[1]


def extract_and_save_features(slide_folder, slide_file_name, csv_path, patches_dir, isNormalized, num_samples=50):
    # 确定dict_name
    config_type = 'DEFAULT'
    if isNormalized == "normalized":
        config_type = 'NORMALIZED'
    dict_name = config[config_type]['dict_name']
    dict_file_name = dict_name+".pth"

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

    # 读取CSV文件
    df = pd.read_csv(csv_path)
    
    # 添加置信度列
    df['confidence'] = df.apply(lambda row: calculate_confidence([row['prob_0'], row['prob_1'], row['prob_2']]), axis=1)
    
    # 筛选出Tumor类别(class=2)和Stroma类别(class=1)的patch
    tumor_patches = df[df['class'] == 2].sort_values('confidence', ascending=False).head(num_samples)
    stroma_patches = df[df['class'] == 1].sort_values('confidence', ascending=False).head(num_samples)
    
    # 提取patch
    get_slide_patch(
        slide_folder, 
        slide_file_name, 
        patches_dir, 
        tumor_patches['patch'].tolist() + stroma_patches['patch'].tolist(), 
        isNormalized, 
        model_patch_size
    )
    
    
    # 定义图像预处理
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 创建用于保存特征的DataFrame
    features_data = []

    # 定义处理样本的函数
    def process_samples(patches_df, class_label):
        dataset = PatchDataset(patches_dir, patches_df['patch'].tolist(), transform)
        loader = DataLoader(dataset, batch_size=1, shuffle=False)
        
        for img, patch_name in loader:
            # 提取特征
            img = img.to(device)
            with torch.no_grad():
                features = model.extract_features(img)
                
            # 将特征转换为numpy数组
            features_np = features.cpu().numpy()[0]  # 取第一个样本，因为batch_size=1

            # 获取当前patch的置信度
            patch_info = patches_df[patches_df['patch'] == patch_name[0]]
            confidence = patch_info['confidence'].values[0]
            
            # 将特征向量和patch信息添加到数据列表
            row_data = {'patch': patch_name[0], 'class': class_label, 'confidence': confidence}
            
            # 添加特征向量的每个元素
            for i, feature_val in enumerate(features_np):
                row_data[f'feature_{i}'] = feature_val
            
            features_data.append(row_data)
    
    # 处理Tumor和Stroma样本
    process_samples(tumor_patches, 'Tumor')
    process_samples(stroma_patches, 'Stroma')
    
    # 创建DataFrame并保存为CSV
    features_dir = os.path.dirname(csv_path)
    features_df = pd.DataFrame(features_data)
    features_csv_path = os.path.join(features_dir, 'patch-features.csv')
    features_df.to_csv(features_csv_path, index=False)
    return features_csv_path

if __name__ == "__main__":
    # 变量，slide所在目录
    slide_folder = "E:\Downloads\slides"
    slide_folder_name = os.path.basename(slide_folder)

    # 开始处理
    csv_base_folder= os.path.join(ROOT_PATH, "public", "predictRes")
    for root, dirs, files in os.walk(csv_base_folder):
        root_name = os.path.basename(root)
        isNormalized = root_name.split("_")[-1]
        folder_fileName = "_".join(root_name.split("_")[:-1])
        slide_file_name = ""
        isOk = False # 很无奈的一个变量，实在不知道怎么命名了。用于确认当前切片是否在要处理的那个文件夹下

        # 确认当前处理的文件夹是否是指定的文件夹
        for file in files:
            # 找到hotspot文件，获取slide文件名
            file_head_name = file.split("_")[0]
            if(file_head_name == "hotspot"):
                slide_file_name = "_".join(file.split("_")[1:]).split(".")[0]
                current_slide_folder_name = folder_fileName.replace(slide_file_name, '').rstrip('_')
                if(current_slide_folder_name == slide_folder_name):
                    isOk = True
                    break
                else:
                    break
        if not isOk:
            continue

        # 开始处理
        for file in files:
            if file=="predictions-{}-{}.csv".format(model_name, isNormalized):
                csv_path = os.path.join(root, file)
                patches_dir = os.path.join(patches_base_folder, folder_fileName, isNormalized+"-"+str(model_patch_size))
                features_dir = extract_and_save_features(slide_folder, slide_file_name, csv_path, patches_dir, isNormalized)
                print(f"特征已保存到: {features_dir}")