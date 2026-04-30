from datasets import load_dataset

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("GAIR/lima")

# 获取训练集
train_ds = ds["train"]

# 筛选 source 为 "writingprompts" 的数据
filtered_ds = train_ds.filter(lambda x: x["source"] == "writingprompts")

# 提取所有数据的 conversations 中的第一个元素
extracted_data = []
for item in filtered_ds:
    conversation_first = item["conversations"][0] if item["conversations"] else ""
    extracted_data.append(conversation_first)

# 按照第一个元素的长度排序，并取最短的100条
sorted_data = sorted(extracted_data, key=lambda x: len(x))
limited_ds = sorted_data[:100]

# 打印结果示例
print(f"提取了 {len(limited_ds)} 条数据")
print("前5条数据示例:")
for i, conv in enumerate(limited_ds[:5]):
    print(f"{i + 1}: {conv[:100]}...")  # 只显示前100个字符

# 将提取的数据保存到文件中
with open("lima.txt", "w", encoding="utf-8") as f:
    for i, conv in enumerate(limited_ds):
        f.write(f"{conv}\n")

print("数据已保存到 lima.txt 文件中")