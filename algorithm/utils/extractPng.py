import openslide
from PIL import Image
import argparse
import os
import configparser
from myLogger import setup_logger

# 设置日志记录器
logger = setup_logger()

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

def extract_lowest_resolution_image(svs_path, output_path):
    # 打开 SVS 文件
    slide = openslide.OpenSlide(svs_path)
    
    # 获取 level 数量
    level_count = slide.level_count
    
    # 最大 level（分辨率最低）是 level_count - 1
    lowest_level = level_count - 1
    
    # 获取该 level 的图像尺寸
    level_dimensions = slide.level_dimensions[lowest_level]
    
    # 读取最低分辨率的图像
    img = slide.read_region((0, 0), lowest_level, level_dimensions)
    
    # 转换为 PIL 图像并保存
    img_rgb = img.convert("RGB")  # 转换为 RGB（去除 alpha 通道）
    img_rgb.save(output_path, "PNG")
    
    # 关闭文件
    slide.close()
    logger.info(f"Extracted lowest resolution image from {svs_path} and saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract lowest resolution image from SVS file.")
    parser.add_argument("--slide_file_name", type=str, help="Path to the SVS file.")
    parser.add_argument("--slide_folder", type=str, help="Path to save the output image.")
    args = parser.parse_args()

    # 获取输入参数
    slide_file_name = args.slide_file_name
    slide_folder = args.slide_folder

    # 获取配置文件中的参数
    ROOT_PATH = config['DEFAULT']['ROOT_PATH']
    origin_image_folder = config['DEFAULT']['origin_image_folder']

    # 拼接输出路径
    slide_name = slide_file_name.split(".")[0]
    slide_folder_name = os.path.basename(slide_folder)
    svs_path = os.path.join(slide_folder, slide_file_name)
    output_folder = os.path.join(ROOT_PATH, origin_image_folder)
    output_path = os.path.join(output_folder, f"{slide_folder_name}_{slide_name}.png")
    
    extract_lowest_resolution_image(svs_path, output_path)