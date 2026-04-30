import json

# 初始化计数器和结果列表
count = 0
results = []

# 打开并逐行读取 JSONL 文件
with open('processed_simulated_conversation_single_pass_930.jsonl', 'r', encoding='utf-8') as file:
    for line in file:
        if count >= 100:
            break
        # 解析每一行为 JSON 对象
        data = json.loads(line)
        full_conversation = data.get('full_conversation', '')
        
        # 检查是否以 "customer:" 开头
        if full_conversation.startswith('customer:'):
            # 提取 "customer:" 后的内容直到遇到 \n（转义字符）
            content = full_conversation[len('customer:'):]
            end_index = content.find('seller:')
            if end_index != -1:
                content = content[:end_index]
            results.append(content)
            count += 1

# 输出结果到文件或直接打印
with open('wizard.txt', 'w', encoding='utf-8') as output_file:
    for item in results:
        output_file.write(item + '\n')

print(f"已成功提取 {len(results)} 条记录并保存至 wizard.txt")
