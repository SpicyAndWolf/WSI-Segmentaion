import pandas as pd
import os
import configparser
from pathlib import Path

def merge_csv_files():
    """
    整合所有patch-features.csv文件到一个CSV文件中
    """
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('config.ini')
    ROOT_PATH = config['DEFAULT']['ROOT_PATH']
    
    # CSV文件所在的基础目录
    csv_base_folder = os.path.join(ROOT_PATH, "public", "predictRes")
    
    # 存储所有数据的列表
    all_data = []
    processed_files = []
    
    print(f"开始搜索CSV文件，基础目录: {csv_base_folder}")
    
    # 遍历所有子目录寻找patch-features.csv文件
    for root, dirs, files in os.walk(csv_base_folder):
        for file in files:
            if file == "patch-features.csv":
                csv_path = os.path.join(root, file)
                print(f"找到文件: {csv_path}")
                
                try:
                    # 读取CSV文件
                    df = pd.read_csv(csv_path)
                    
                    # 添加来源信息
                    relative_path = os.path.relpath(root, csv_base_folder)
                    df['source_folder'] = relative_path
                    df['source_file'] = csv_path
                    
                    # 解析文件夹名称获取更多信息
                    folder_parts = relative_path.split(os.sep)
                    if len(folder_parts) > 0:
                        folder_name = folder_parts[-1]  # 最后一级文件夹名
                        # 通常格式为: slideFileName_normalized 或 slideFileName_notNormalized
                        if '_' in folder_name:
                            parts = folder_name.split('_')
                            df['slide_name'] = '_'.join(parts[:-1])
                            df['normalization_type'] = parts[-1]
                        else:
                            df['slide_name'] = folder_name
                            df['normalization_type'] = 'unknown'
                    
                    all_data.append(df)
                    processed_files.append(csv_path)
                    print(f"成功读取文件，包含 {len(df)} 行数据")
                    
                except Exception as e:
                    print(f"读取文件 {csv_path} 时出错: {str(e)}")
    
    if not all_data:
        print("未找到任何patch-features.csv文件")
        return None
    
    # 合并所有数据
    print(f"\n开始合并 {len(all_data)} 个文件的数据...")
    merged_df = pd.concat(all_data, ignore_index=True)
    
    # 重新排列列的顺序，将元数据列放在前面
    metadata_cols = ['source_folder', 'slide_name', 'normalization_type', 'patch', 'class', 'confidence']
    feature_cols = [col for col in merged_df.columns if col.startswith('feature_')]
    other_cols = [col for col in merged_df.columns if col not in metadata_cols + feature_cols + ['source_file']]
    
    # 重新排序列
    new_column_order = metadata_cols + other_cols + feature_cols + ['source_file']
    merged_df = merged_df[[col for col in new_column_order if col in merged_df.columns]]
    
    # 保存合并后的文件
    output_path = os.path.join(os.getcwd(), 'merged_patch_features.csv')
    merged_df.to_csv(output_path, index=False)
    
    print(f"\n合并完成！")
    print(f"总共处理了 {len(processed_files)} 个文件")
    print(f"合并后的数据包含 {len(merged_df)} 行，{len(merged_df.columns)} 列")
    print(f"输出文件: {output_path}")
    
    # 显示统计信息
    print("\n数据统计:")
    if 'slide_name' in merged_df.columns:
        print(f"包含的切片数量: {merged_df['slide_name'].nunique()}")
        print(f"切片列表: {list(merged_df['slide_name'].unique())}")
    
    if 'normalization_type' in merged_df.columns:
        print(f"归一化类型分布:")
        print(merged_df['normalization_type'].value_counts())
    
    if 'class' in merged_df.columns:
        print(f"类别分布:")
        print(merged_df['class'].value_counts())
    
    # 显示处理的文件列表
    print("\n处理的文件列表:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"{i}. {file_path}")
    
    return output_path

def analyze_merged_data(csv_path):
    """
    分析合并后的数据
    """
    if not os.path.exists(csv_path):
        print(f"文件不存在: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    
    print(f"\n=== 合并数据分析 ===")
    print(f"数据形状: {df.shape}")
    print(f"\n列名:")
    for i, col in enumerate(df.columns):
        print(f"{i+1}. {col}")
    
    # 特征列统计
    feature_cols = [col for col in df.columns if col.startswith('feature_')]
    print(f"\n特征维度: {len(feature_cols)}")
    
    # 缺失值检查
    missing_data = df.isnull().sum()
    if missing_data.sum() > 0:
        print(f"\n缺失值统计:")
        print(missing_data[missing_data > 0])
    else:
        print(f"\n无缺失值")

if __name__ == "__main__":
    print("开始整合patch-features.csv文件...")
    
    # 执行合并
    output_file = merge_csv_files()
    
    if output_file:
        # 分析合并后的数据
        analyze_merged_data(output_file)
        print(f"\n整合完成！合并后的文件保存在: {output_file}")
    else:
        print("整合失败，请检查文件路径和权限。")