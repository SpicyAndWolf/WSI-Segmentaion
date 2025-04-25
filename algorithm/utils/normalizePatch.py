import os
from datetime import datetime

# 定义目录
reference_image = "/home/zyf/Projects/WSI/Datasets/WSI/train/1/2174779008_170922_43008_56640.png"
base_dir = "/home/zyf/Projects/WSI/Patches/slidePatches"
subdirs = ["1726363012"]

# 开始处理
start = datetime.now()
print(f"start processing ...")

# 创建输出目录并执行命令
for subdir in subdirs:
    input_dir = os.path.join(base_dir, subdir,"origin-256")
    output_dir = os.path.join(base_dir, subdir,"normalized-fast-256")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    command = (
        f"python /home/zyf/Projects/WSI/New/fast-stain-normalization/source/__main__.py "
        f"--ref {reference_image} "
        f"--img {input_dir} "
        f"--out {output_dir} "
        f"--wk 8 "
        f"--cpu 0 "
    )
    os.system(command)

# 打印时间
print(f"all cost time: {datetime.now() - start}")


# python __main__.py \
# --ref /home/zyf/Projects/WSI/Datasets/WSI/train/1/2174779008_170922_43008_56640.png \
# --img /home/zyf/Projects/WSI/Patches/slidePatches/2001549007_101728/origin-256 \
# --out /home/zyf/Projects/WSI/Patches/slidePatches/2001549007_101728/normalized-256 \
# --wk 8 \
# --cpu 0