import argparse
import json
import configparser
from utils.segWithoutAnnotation import slide2patches
from utils.predict import predict, mergePatches
from utils.calculateTSR import calculateTSR
from datetime import datetime
import os
from utils.myLogger import setup_logger

# 设置日志记录器
logger = setup_logger()

# 读取后端传输的配置
def parse_args():
    parser = argparse.ArgumentParser(description="Process slide images to patches.")
    parser.add_argument("--slide_folder", type=str, help="Path to the folder containing slide images")
    parser.add_argument("--slide_file_name", type=str, help="Name of the slide file to process")
    parser.add_argument("--isSegmented", type=bool, default=False, help="Whether the slide is already segmented")

    # 解析参数
    args = parser.parse_args()
    return args

def seg_patch(slide_folder, slide_file_name, slide_patches_base_folder, model_patch_size, model_name, dict_name, isSegmented):
    # 打印所有参数
    all_config={
        "slide_fold": slide_folder,
        "slide_files_name": slide_file_name,
        "res_fold": slide_patches_base_folder,
        "model_patch_size": model_patch_size
    }
    logger.info(f"请求处理patch: {all_config}")

    # 创建存储patches的文件夹
    patches_folder = os.path.join(slide_patches_base_folder, slide_file_name, "origin-{}".format(model_patch_size))
    if(not os.path.exists(patches_folder)):
        os.makedirs(patches_folder)

    # 开始切分
    if not isSegmented:
        logger.info("开始分割 patch：" + slide_file_name)
        slide2patches(slide_folder, slide_file_name, patches_folder, model_patch_size)

    # 预测
    df, patch_size, res_dir = predict(slide_folder, slide_file_name)
    segmentationFileName = mergePatches(slide_folder, slide_file_name, df, patch_size, res_dir)

    # 计算TSR
    logger.info("开始计算TSR：" + slide_file_name)
    tsr, tsr_hotspot, hotspot_file_name = calculateTSR(slide_folder, slide_file_name)
    
    # 输出 JSON 格式的结果
    result = {
        "slideFileName": slide_file_name,
        "slideFolder": slide_folder,
        "modelPatchSize": model_patch_size,
        "dictName": dict_name,
        "modelName": model_name,
        "tsr": tsr,
        "tsr_hotspot": tsr_hotspot,
        "hotspot_file_name": hotspot_file_name,
        "segmentationFileName": segmentationFileName
    }
    res_json_path = os.path.join(res_dir, f"{segmentationFileName}_result.json")
    with open(res_json_path, 'w') as f:
        json.dump(result, f)

    # 返回 JSON 文件路径
    logger.info(f"完成处理patch: {slide_file_name}")
    print(json.dumps({"res_json_path": res_json_path}))

if __name__ == "__main__":
    # 加载配置文件
    args = parse_args()
    config = configparser.ConfigParser()
    config.read('config.ini')

    # 获取配置文件内参数
    model_patch_size = int(config['DEFAULT']['model_patch_size'])
    slide_patches_base_folder = config['DEFAULT']['slide_patches_base_folder']
    ROOT_PATH = config['DEFAULT']['ROOT_PATH']
    model_name = "resnet50-{}".format(model_patch_size)
    dict_name = config['DEFAULT']['dict_name']

    # 获取命令行中的参数
    slide_folder = args.slide_folder
    slide_file_name = os.path.splitext(args.slide_file_name)[0]
    isSegmented = args.isSegmented

    # 切分patch
    seg_patch(slide_folder, slide_file_name, slide_patches_base_folder, model_patch_size, model_name, dict_name, isSegmented)