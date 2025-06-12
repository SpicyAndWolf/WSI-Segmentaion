import os
import json
import csv
import configparser

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 定义基本路径
ROOT_PATH = config['DEFAULT']['ROOT_PATH']

# 定义目录路径
base_dir = os.path.join(ROOT_PATH, "public","predictRes")

# 定义输出CSV文件路径
output_csv = r"./tsr_stats.csv"

# 定义要提取的字段
fields = ['slideFileName', 'isNormalized', 'tsr', 'tsr_hotspot']

# 创建结果列表
results = []

# 遍历目录
for root, dirs, files in os.walk(base_dir):
    for file in files:
        # 只处理JSON文件
        if file.endswith('.json'):
            file_path = os.path.join(root, file)
            try:
                # 读取JSON文件
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # 提取所需字段
                row = []
                for field in fields:
                    if field in data:
                        row.append(data[field])
                    else:
                        row.append('')  # 如果字段不存在，添加空值
                
                # 添加到结果列表
                if len(row) == len(fields):
                    results.append(row)
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")

# 写入CSV文件
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    # 写入表头
    writer.writerow(fields)
    # 写入数据行
    writer.writerows(results)

print(f"统计完成，结果已保存到 {output_csv}")