def plot_model_reference_avg_by_content(result_file):
    import json
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    from collections import defaultdict
    from scipy import stats
    
    # 设置输出目录
    output_dir = os.path.join(os.path.dirname(result_file), 'picture')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 初始化数据结构
    # 按模型和content得分分组存储reference得分
    model_content_ref_scores = defaultdict(lambda: defaultdict(list))
    # 存储每个模型的原始数据用于计算相关系数
    model_raw_data = defaultdict(lambda: {'content_scores': [], 'ref_scores': []})
    
    # 遍历数据收集信息
    # 检查data是列表还是字典，并相应地处理
    if isinstance(data, list):
        # 如果data是列表，直接遍历列表项
        items_to_process = data
    else:
        # 如果data是字典，遍历其值
        items_to_process = data.values()
    
    for item_data in items_to_process:
        # 适配新的数据结构：模型结果在'result'列表中
        if 'result' in item_data:
            for model_result in item_data['result']:
                model_name = model_result.get('model')
                
                # 获取content得分
                if isinstance(model_result.get('content'), list) and len(model_result['content']) > 1:
                    content_score = model_result['content'][1]
                    
                    # 获取有效reference得分（排除-1分）
                    references = model_result.get('references', [])
                    valid_ref_scores = [ref[1] for ref in references if isinstance(ref, list) and len(ref) > 1 and ref[1] != -1]
                    
                    if valid_ref_scores:
                        # 计算该项目的reference平均分
                        avg_ref_score = np.mean(valid_ref_scores)
                        # 存储数据
                        model_content_ref_scores[model_name][content_score].append(avg_ref_score)
                        # 同时存储原始数据用于计算相关系数
                        model_raw_data[model_name]['content_scores'].append(content_score)
                        model_raw_data[model_name]['ref_scores'].append(avg_ref_score)
    
    # 检查是否有数据
    if not model_content_ref_scores:
        print("未找到有效的模型数据，请检查输入文件格式")
        return
    
    # 获取所有content得分和模型名称
    content_scores = set()
    model_names = list(model_content_ref_scores.keys())
    for model_data in model_content_ref_scores.values():
        content_scores.update(model_data.keys())
    content_scores = sorted(list(content_scores))
    
    # 计算每个模型在不同content得分下的平均reference得分，以及相关系数
    table_data = []
    for model_name in model_names:
        row = [model_name]
        
        # 计算相关系数
        content_scores_list = model_raw_data[model_name]['content_scores']
        ref_scores_list = model_raw_data[model_name]['ref_scores']
        
        # 确保有足够的数据点计算相关系数（至少需要3个数据点）
        if len(content_scores_list) >= 3:
            # 使用斯皮尔曼秩相关系数，更稳健且对异常值不敏感
            correlation_coef, p_value = stats.spearmanr(content_scores_list, ref_scores_list)
            # 保存相关系数，保留两位小数
            corr_value = f"{correlation_coef:.2f}"
        else:
            corr_value = "N/A"
        
        # 添加各content得分下的平均reference得分
        for content_score in content_scores:
            if content_score in model_content_ref_scores[model_name]:
                # 计算该content得分下的平均reference得分
                avg_score = np.mean(model_content_ref_scores[model_name][content_score])
                # 统计数据点数量
                count = len(model_content_ref_scores[model_name][content_score])
                row.append(f"{avg_score:.2f}\n(n={count})")
            else:
                row.append("N/A")
        
        # 添加相关系数列
        row.append(corr_value)
        table_data.append(row)
    
    # 准备表格列标签
    headers = ['模型'] + [f'Content={score}' for score in content_scores] + ['相关系数']
    
    # 创建表格
    fig, ax = plt.subplots(figsize=(14, max(6, len(model_names) * 0.5)))
    ax.axis('tight')
    ax.axis('off')
    
    # 创建表格并设置样式
    table = ax.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    # 设置表格样式
    for (i, j), cell in table.get_celld().items():
        cell.set_text_props(ha='center', va='center')
        if i == 0:  # 表头
            cell.set_facecolor('#40466e')
            cell.set_text_props(color='white', weight='bold')
        else:
            # 每隔一行设置背景色，提高可读性
            if i % 2 == 0:
                cell.set_facecolor('#f5f5f5')
            # 为相关系数列设置不同的背景色，使其突出显示
            if j == len(headers) - 1:
                cell.set_facecolor('#e6f3ff')
    
    plt.title('不同模型在各Content得分下的Reference平均分及相关系数', fontsize=14, pad=20)
    
    # 保存表格
    output_file = os.path.join(output_dir, 'model_reference_avg_by_content_table.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"表格已保存至: {output_file}")