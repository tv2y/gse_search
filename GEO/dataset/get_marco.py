from datasets import load_dataset
import pandas as pd  # 导入pandas用于数据处理

ds = load_dataset("microsoft/ms_marco", "v1.1")

# 获取训练集并转换为DataFrame以便处理
train_df = ds['train'].to_pandas()

# 统计各query_type的分布比例
type_counts = train_df['query_type'].value_counts()
total_samples = len(train_df)
type_ratios = type_counts / total_samples

# 计算每个类型应抽取的样本数（共100条）
target_total = 100
type_sample_counts = (type_ratios * target_total).round().astype(int)

# 调整样本数确保总和为100
if type_sample_counts.sum() != target_total:
    diff = target_total - type_sample_counts.sum()
    # 将差异分配给比例最大的类型
    type_sample_counts[type_sample_counts.idxmax()] += diff

# 按比例采样各类型数据
sampled_data = []
for type_name, count in type_sample_counts.items():
    if count <= 0:
        continue
    # 筛选当前类型数据并采样
    type_data = train_df[train_df['query_type'] == type_name]
    sampled = type_data.sample(n=count, random_state=42)  # 设置随机种子确保可复现
    sampled_data.append(sampled)

# 合并采样结果并提取所需字段
result_df = pd.concat(sampled_data)[['query', 'query_type']].reset_index(drop=True)

# 只保存问题到txt文件
queries = result_df['query'].tolist()
with open('msmarco.txt', 'w', encoding='utf-8') as f:
    for query in queries:
        f.write(query + '\n')