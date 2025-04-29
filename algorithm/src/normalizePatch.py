import os
from datetime import datetime
import configparser
from utils.myLogger import setup_logger

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 设置日志
logger = setup_logger()

# 定义基本路径
ROOT_PATH = config['DEFAULT']['ROOT_PATH']
fast_stain_base_folder = os.path.join(ROOT_PATH, "algorithm", "fast-stain-normalization")
reference_image_path = os.path.join(fast_stain_base_folder,"reference", "2174779008_170922_43008_56640.png")
main_py_path = os.path.join(fast_stain_base_folder, "source", "__main__.py")


def normalizePatch(input_dir, output_dir, slide_name):
    start = datetime.now()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    command = (
        f"python {main_py_path} "
        f"--ref {reference_image_path} "
        f"--img {input_dir} "
        f"--out {output_dir} "
        f"--wk 8 "
        f"--cpu 0 "
    )
    os.system(command)

    # 打印时间
    logger.info(f"颜色标准化{slide_name}，花费时间: {datetime.now() - start}")

if __name__ == "__main__":
    input_dir = "E:/Code/WSI/slidePatches/slides_2004409012_141125/origin-256"
    output_dir = "E:/Code/WSI/slidePatches/slides_2004409012_141125/normalized-256"
    slide_name = "2004409012_141125"

    normalizePatch(input_dir, output_dir, slide_name)