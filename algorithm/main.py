import argparse
import json
import configparser
from utils.segWithoutAnnotation import slide2patches
from utils.predict import predict, mergePatches
from datetime import datetime
import os

# 读取后端传输的配置
def parse_args():
    parser = argparse.ArgumentParser(description="Process slide images to patches.")
    parser.add_argument("--slide_folder", type=str, help="Path to the folder containing slide images")
    parser.add_argument("--slide_file_name", type=str, help="Name of the slide file to process")

    # 解析参数
    args = parser.parse_args()
    return args

def seg_patch(slide_folder, slide_file_name, slide_patches_base_folder, model_patch_size, ROOT_PATH, model_name, dict_name):
    # 打印所有参数
    all_config={
        "slide_fold": slide_folder,
        "slide_files_name": slide_file_name,
        "res_fold": slide_patches_base_folder,
        "model_patch_size": model_patch_size
    }
    print(all_config)

    # 创建存储patches的文件夹
    patches_folder = os.path.join(slide_patches_base_folder, slide_file_name, "origin-{}".format(model_patch_size))
    if(not os.path.exists(patches_folder)):
        os.makedirs(patches_folder)

    # 开始切分
    print("start seg patch：" + slide_file_name)
    slide2patches(slide_folder, slide_file_name, patches_folder, model_patch_size)

    # 预测
    df, patch_size = predict(slide_folder, slide_file_name)
    mergePatches(slide_folder, slide_file_name, df, patch_size)

    # 模拟数据
    tsr = 0.85
    segmentationFileName = f'predictionImg-{model_name}-{dict_name}-{slide_file_name}.png'
    
    # 输出 JSON 格式的结果
    result = {
        "tsr": tsr,
        "resName": segmentationFileName
    }
    print(json.dumps(result))

if __name__ == "__main__":
    # 加载配置文件
    args = parse_args()
    config = configparser.ConfigParser()
    config.read('config.ini')

    # 获取配置文件内参数
    model_patch_size = int(config['DEFAULT']['model_patch_size'])
    slide_patches_base_folder = config['DEFAULT']['slide_patches_base_folder']
    ROOT_PATH = config['DEFAULT']['ROOT_PATH']
    model_name = config['DEFAULT']['model_name']
    dict_name = config['DEFAULT']['dict_name']

    # 获取命令行中的参数
    slide_folder = args.slide_folder
    slide_file_name = os.path.splitext(args.slide_file_name)[0]

    # 切分patch
    seg_patch(slide_folder, slide_file_name, slide_patches_base_folder, model_patch_size, ROOT_PATH, model_name, dict_name)