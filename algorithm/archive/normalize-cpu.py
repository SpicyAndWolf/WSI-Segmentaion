import os
from PIL import Image
from datetime import datetime
import numpy as np
import staintools
from concurrent.futures import ThreadPoolExecutor

def process_image(img_path, input_dir, output_dir, normalizer):
    img = Image.open(img_path)
    img_np = np.array(img)
    try:
        normalized_img_np = normalizer.transform(img_np)
        normalized_img = Image.fromarray(normalized_img_np)
        rel_path = os.path.relpath(img_path, input_dir)
        save_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        normalized_img.save(save_path)
    except Exception as e:
        print(f"Error processing {img_path}: {e}")


def preprocess_and_save_images_parallel(input_dir, output_dir, normalizer, num_workers=4):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    all_files = [os.path.join(root, fname) for root, _, files in os.walk(input_dir) for fname in files]
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        executor.map(lambda p: process_image(p, input_dir, output_dir, normalizer), all_files)

def main(input_dir, output_dir):
    start=datetime.now()
    print(f"start processing ...")

    # 初始化 Macenko 颜色标准化器
    reference_image_path = "/home/zyf/Projects/WSI/Datasets/WSI/train/1/2174779008_170922_43008_56640.png"
    reference_image = Image.open(reference_image_path)
    reference_image_np = np.array(reference_image)
    normalizer = staintools.StainNormalizer(method='macenko')
    normalizer.fit(reference_image_np)
    preprocess_and_save_images_parallel(input_dir, output_dir, normalizer, num_workers=8)
    print(f"all cost time: {datetime.now() - start}")

if __name__ == "__main__":
    slide_name = "1726363012"
    input_dir = f"/home/zyf/Projects/WSI/Patches/slidePatches/{slide_name}/origin-256"
    output_dir = f"/home/zyf/Projects/WSI/Patches/slidePatches/{slide_name}/normalized-slow-256"
    main(input_dir, output_dir)