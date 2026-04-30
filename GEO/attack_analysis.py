import json
import os
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import math

# --- 配置常量 ---
# 硬编码的目标得分：用于判断对照组（非迭代方法）的成功
TARGET_SCORES = [0.322, 0.09, 0.96, 0.96, 0.84, 0.87, 0.82]
METRIC_NAMES = ['CF', 'CCR', 'AA', 'SF', 'KIC', 'SC', 'AD']
ITERATIVE_METHOD_NAME = 'User_Iterative_Optimization'

# --- 攻击方法名称映射 ---
# 将原始方法名称映射到更友好或更规范的中文/英文名称
METHOD_NAME_MAPPING = {
    'init': 'Baseline',
    'User_Iterative_Optimization': 'Our Method',
    'authoritative_optimization': 'Authoritative Tone',
    'citing_sources_optimization': 'Citation Addition',
    'coercive_command_attack': 'Command Hijacking',
    'competitor_denigration_attack': 'Reputation Attack',
    'keyword_stuffing_attack': 'Keyword Stuffing',
    'stats_add_optimization': 'Data Support',
    'unique_words_optimization': 'Unique Terms',
    'value_alignment_manipulation_attack': 'Emotional Manipulation'
}


# 您提供的映射关系 - 如果需要使用这些名称，可以取消注释并替换上面的映射
# METHOD_NAME_MAPPING = {
#     'keyword_stuffing_attack': 'Keyword Stuffing',
#     'authoritative_optimization': 'Authoritative Tone',
#     'stats_add_optimization': 'Data Support',
#     'citing_sources_optimization': 'Citation Addition',
#     'unique_words_optimization': 'Unique Terms',
#     'coercive_command_attack': 'Command Hijacking',
#     'competitor_denigration_attack': 'Reputation Attack',
#     'value_alignment_manipulation_attack': 'Emotional Manipulation',
#     'init': 'Baseline',
#     'User_Iterative_Optimization': 'User Iterative Optimization'
# }


def map_method_name(original_name: str) -> str:
    """
    将原始方法名称映射到更友好的名称。
    """
    return METHOD_NAME_MAPPING.get(original_name, original_name)


def reverse_method_name(mapped_name: str) -> str:
    """
    将映射后的名称反向映射回原始名称。
    """
    reverse_mapping = {v: k for k, v in METHOD_NAME_MAPPING.items()}
    return reverse_mapping.get(mapped_name, mapped_name)


def is_success(scores: List[float], target_scores: List[float]) -> bool:
    """
    用于判断非迭代方法（如 init, authoritative_optimization）是否成功：
    所有指标都严格高于 TARGET_SCORES。
    """
    if len(scores) != len(target_scores):
        return False
    return all(scores[i] > target_scores[i] for i in range(len(target_scores)))


def is_single_metric_success(score: float, target_score: float) -> bool:
    """
    判断单个指标是否成功：得分高于目标分数。
    """
    return score > target_score


def extract_iterative_log_data(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    严格按照用户要求从单个攻击日志数据中提取数据。
    """
    query = log_data.get('query', 'UNKNOWN_QUERY')
    log_entries = log_data.get('log_entries', [])

    final_scores = []
    attack_success = False
    max_round = 0  # 查询次数 (round字段的最大值)

    for entry in log_entries:
        current_round = entry.get('round', 0)
        # 1. 查询次数：round 字段的最大值
        max_round = max(max_round, current_round)

        if entry.get('step') == 'Final Status':
            # 2. 攻击是否成功 (Final Status 中的 success 字段)
            attack_success = entry.get('success', False)
            # 3. 最终得分 (Final Status 中的 final_scores 字段)
            scores = entry.get('final_scores')
            if scores and len(scores) == len(METRIC_NAMES):
                final_scores = scores

    return {
        'query': query,
        'final_scores': final_scores,
        'attack_success': attack_success,
        'query_count': max_round,
    }


def get_iterative_method_results_from_dir(log_dir_path: str) -> Dict[str, Dict[str, Any]]:
    """
    根据目录找到文件夹下所有文件，并提取所需数据。
    """
    print(f"--- 正在从迭代攻击日志目录中提取数据: {log_dir_path} ---")

    iterative_method_results = {}

    try:
        # ！！！ 这里的 os.listdir 将读取您本地 LOGS_DIR 的内容 ！！！
        for filename in os.listdir(log_dir_path):
            if filename.endswith('.json'):
                filepath = os.path.join(log_dir_path, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)

                    extracted_data = extract_iterative_log_data(log_data)

                    if extracted_data['final_scores']:
                        query = extracted_data['query']
                        if query in iterative_method_results:
                            print(f"警告：查询 '{query}' 在多个文件中重复，已覆盖。")

                        iterative_method_results[query] = extracted_data

                except json.JSONDecodeError:
                    print(f"警告：文件 {filename} 解析失败，已跳过。")
                except Exception as e:
                    print(f"警告：处理文件 {filename} 时发生错误: {e}，已跳过。")

        print(f"成功提取 {len(iterative_method_results)} 个查询的迭代数据。")

    except FileNotFoundError:
        print(f"错误：日志目录 {log_dir_path} 未找到或无法访问。请检查路径是否正确。")
    except Exception as e:
        print(f"发生未知错误: {e}")

    return iterative_method_results


def analyze_optimization_results(eval_file_path: str, log_dir_path: str) -> Dict[str, Any]:
    """
    执行所有计算并返回分析结果，同时输出JSON文件。
    """
    # 1. 加载对照组数据
    try:
        with open(eval_file_path, 'r', encoding='utf-8') as f:
            eval_data_list = json.load(f)
        # 将对照组数据转换为以 query 为键的字典，方便查找
        eval_data_map = {item['query']: item['scores'] for item in eval_data_list}

    except Exception as e:
        print(f"错误：评估结果文件 {eval_file_path} 加载失败。{e}")
        return {}

    # 2. 加载迭代方法的结果 (确定基准查询集 $Q_{exp}$)
    iterative_results = get_iterative_method_results_from_dir(log_dir_path)

    # 3. 确定用于比较的基准查询集 $Q_{exp}$
    # 集合 $Q_{exp}$ 必须是那些既在迭代结果中，也在对照组结果中找到的查询。
    comparison_queries = [q for q in iterative_results.keys() if q in eval_data_map]
    total_comparison_queries = len(comparison_queries)

    if total_comparison_queries == 0:
        print("警告：迭代方法实验结果中没有找到与对照组结果匹配的查询。无法进行比较分析。")
        print(f"请检查迭代日志文件中的 'query' 字段是否与 '{eval_file_path}' 中的一致。")
        return {}

    # 4. 初始化汇总数据结构
    all_methods = set([ITERATIVE_METHOD_NAME])
    for query in comparison_queries:
        for method_name in eval_data_map[query]:
            all_methods.add(method_name)

    total_scores: Dict[str, List[float]] = defaultdict(lambda: [0.0] * len(METRIC_NAMES))
    success_counts: Dict[str, int] = defaultdict(int)

    # 新增：单一维度攻击成功率统计
    # 结构: method_name -> metric_index -> count
    single_metric_success_counts: Dict[str, List[int]] = defaultdict(lambda: [0] * len(METRIC_NAMES))

    iter_success_rounds_sum = 0
    iter_success_queries_count = 0

    # 5. 遍历基准查询集 $Q_{exp}$，进行累加计算
    for query in comparison_queries:
        # A. 迭代方法 (实验组) 的结果
        data = iterative_results[query]
        final_scores = data['final_scores']

        # 累加最终得分
        for i in range(len(TARGET_SCORES)):
            total_scores[ITERATIVE_METHOD_NAME][i] += final_scores[i]

            # 统计单一维度攻击成功率
            if is_single_metric_success(final_scores[i], TARGET_SCORES[i]):
                single_metric_success_counts[ITERATIVE_METHOD_NAME][i] += 1

        # 记录最终成功率 (来自 Final Status 中的 success 字段)
        if data['attack_success']:
            success_counts[ITERATIVE_METHOD_NAME] += 1

            # 核心逻辑：计算攻击成功的平均迭代次数 (使用 max_round)
            iter_success_rounds_sum += data['query_count']
            iter_success_queries_count += 1

        # B. 其他攻击方法 (对照组) 的结果
        scores_by_method = eval_data_map[query]

        for method_name, scores in scores_by_method.items():
            if len(scores) != len(TARGET_SCORES):
                continue

            # 累加得分
            for i in range(len(TARGET_SCORES)):
                total_scores[method_name][i] += scores[i]

                # 统计单一维度攻击成功率
                if is_single_metric_success(scores[i], TARGET_SCORES[i]):
                    single_metric_success_counts[method_name][i] += 1

            # 成功率计算：基于硬编码 TARGET_SCORES
            if is_success(scores, TARGET_SCORES):
                success_counts[method_name] += 1

    # 6. 生成结果数据

    # 攻击成功的平均迭代次数
    avg_rounds_to_success = iter_success_rounds_sum / iter_success_queries_count if iter_success_queries_count > 0 else 0.0

    # 将方法 'init' (Baseline) 放在最前面
    sorted_methods = sorted(list(all_methods), key=lambda x: (x != 'init', x))

    # 创建映射后的方法名列表（用于显示）
    mapped_methods = [map_method_name(method) for method in sorted_methods]

    table_data = []

    # 计算单一维度攻击成功率（百分比）
    single_metric_success_rates = {}
    for method_name in sorted_methods:
        if method_name in single_metric_success_counts:
            single_metric_success_rates[method_name] = [
                (count / total_comparison_queries) * 100 for count in single_metric_success_counts[method_name]
            ]
        else:
            single_metric_success_rates[method_name] = [0.0] * len(METRIC_NAMES)

    # 分母统一使用 total_comparison_queries
    for method_name in sorted_methods:
        if method_name not in total_scores:
            continue

        avg_scores = [score / total_comparison_queries for score in total_scores[method_name]]
        success_rate = (success_counts[method_name] / total_comparison_queries) * 100

        row = {
            'Method': map_method_name(method_name),  # 使用映射后的方法名
            'Original_Method': method_name,  # 保留原始方法名供内部使用
            **{f'Avg_{name}': avg_scores[i] for i, name in enumerate(METRIC_NAMES)},
            'Success_Rate_percent': success_rate,
            'Avg_Iterations_to_Success': avg_rounds_to_success if method_name == ITERATIVE_METHOD_NAME else None
        }
        table_data.append(row)

    # 7. 构建热力图数据
    heatmap_data = []
    for method_name in sorted_methods:
        if method_name in single_metric_success_rates:
            row_data = {
                'method': map_method_name(method_name),  # 使用映射后的方法名
                'original_method': method_name,  # 保留原始方法名
                'metric_success_rates': {
                    metric: single_metric_success_rates[method_name][i]
                    for i, metric in enumerate(METRIC_NAMES)
                }
            }
            heatmap_data.append(row_data)

    # 8. 构建返回结果
    result = {
        'metadata': {
            'comparison_queries_count': total_comparison_queries,
            'success_definition': {
                'iterative_method': "Log 文件中 'Final Status' 的 success 字段为 True",
                'other_methods': f"所有指标都高于目标分数 ({', '.join(METRIC_NAMES)})",
                'single_metric': "单个指标得分高于对应的目标分数"
            },
            'target_scores': TARGET_SCORES,
            'metric_names': METRIC_NAMES,
            'iterative_method_name': ITERATIVE_METHOD_NAME,
            'iterative_method_name_mapped': map_method_name(ITERATIVE_METHOD_NAME),
            'avg_iterations_to_success': avg_rounds_to_success,
            'method_name_mapping': METHOD_NAME_MAPPING  # 包含映射关系
        },
        'data': table_data,
        'heatmap_data': {
            'description': '单一维度攻击成功率热力图数据（行为攻击方法，列为指标，值为在该指标上的攻击成功率百分比）',
            'methods': mapped_methods,  # 使用映射后的方法名
            'original_methods': sorted_methods,  # 保留原始方法名
            'metrics': METRIC_NAMES,
            'matrix': [
                [single_metric_success_rates[method][i] for i in range(len(METRIC_NAMES))]
                for method in sorted_methods if method in single_metric_success_rates
            ]
        }
    }

    return result


def save_results_to_json(results: Dict[str, Any], output_path: str = 'attack_analysis_results.json'):
    """
    将分析结果保存为JSON文件。
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"分析结果已保存到: {output_path}")
    except Exception as e:
        print(f"保存结果到JSON文件时出错: {e}")


def print_results_table(results: Dict[str, Any]):
    """
    打印格式化的表格结果。
    """
    if not results:
        print("没有可显示的结果。")
        return

    table_data = results['data']
    total_comparison_queries = results['metadata']['comparison_queries_count']
    TARGET_SCORES = results['metadata']['target_scores']
    METRIC_NAMES = results['metadata']['metric_names']
    METHOD_MAPPING = results['metadata']['method_name_mapping']

    print(f"\n--- 优化方法性能汇总 ({total_comparison_queries} 个查询) ---")
    print(f"**基准查询数:** {total_comparison_queries} (所有方法均基于这 {total_comparison_queries} 个查询进行比较)")
    print(f"**方法名称映射:**")
    for original, mapped in METHOD_MAPPING.items():
        print(f"  {original} -> {mapped}")
    print(f"\n成功定义:")
    print(f"  - 迭代优化方法: Log 文件中 'Final Status' 的 success 字段为 True。")
    print(f"  - 其他方法: 所有指标都 **高于** 目标分数 ({','.join(METRIC_NAMES)})。")
    print(f"目标分数: {TARGET_SCORES}\n")

    # 重新生成表头
    headers = ["Method"] + [f"Avg {name}" for name in METRIC_NAMES] + ["Success Rate (%)", "Avg Iterations to Success"]

    # 确定每列的最大宽度
    col_widths = {header: len(header) for header in headers}
    for row in table_data:
        col_widths['Method'] = max(col_widths['Method'], len(row['Method']))
        for i, name in enumerate(METRIC_NAMES):
            key = f'Avg_{name}'
            col_widths[f'Avg {name}'] = max(col_widths[f'Avg {name}'], len(f"{row[key]:.3f}"))
        col_widths['Success Rate (%)'] = max(col_widths['Success Rate (%)'], len(f"{row['Success_Rate_percent']:.2f}"))

        rounds_val = f"{row['Avg_Iterations_to_Success']:.2f}" if row['Avg_Iterations_to_Success'] is not None else '-'
        col_widths['Avg Iterations to Success'] = max(col_widths['Avg Iterations to Success'], len(rounds_val))

    header_line = "| " + " | ".join(
        h.ljust(col_widths[h]) for h in headers
    ) + " |"
    print(header_line)
    print("|" + "-".join("-" * col_widths[h] for h in headers) + "--|")

    for row in table_data:
        row_str = "| "
        row_str += row['Method'].ljust(col_widths['Method']) + " | "

        for i, name in enumerate(METRIC_NAMES):
            key = f'Avg_{name}'
            row_str += f"{row[key]:.3f}".ljust(col_widths[f'Avg {name}']) + " | "

        row_str += f"{row['Success_Rate_percent']:.2f}".ljust(col_widths['Success Rate (%)']) + " | "

        rounds_val = f"{row['Avg_Iterations_to_Success']:.2f}" if row['Avg_Iterations_to_Success'] is not None else '-'
        row_str += rounds_val.ljust(col_widths['Avg Iterations to Success']) + " |"

        print(row_str)

    # 打印热力图数据说明
    print("\n--- Success Rate on Single Metric ---")
    print("说明: 行为攻击方法，列为指标，值为在该指标上的攻击成功率百分比")
    print(f"目标分数: {TARGET_SCORES}")


def print_single_metric_success_rates(results: Dict[str, Any]):
    """
    打印单一维度攻击成功率表格。
    """
    if not results or 'heatmap_data' not in results:
        print("没有热力图数据可显示。")
        return

    heatmap_data = results['heatmap_data']
    methods = heatmap_data['methods']
    metrics = heatmap_data['metrics']
    matrix = heatmap_data['matrix']

    print(f"\n--- 单一维度攻击成功率热力图（百分比）---")
    print(f"说明: 每个单元格表示对应方法在对应指标上的攻击成功率")

    # 创建表头
    headers = ["Method"] + metrics

    # 确定每列的最大宽度
    col_widths = {header: len(header) for header in headers}
    for method_idx, method in enumerate(methods):
        col_widths['Method'] = max(col_widths['Method'], len(method))
        for metric_idx, metric in enumerate(metrics):
            if method_idx < len(matrix) and metric_idx < len(matrix[method_idx]):
                value = f"{matrix[method_idx][metric_idx]:.2f}%"
                col_widths[metric] = max(col_widths[metric], len(value))

    # 打印表头
    header_line = "| " + " | ".join(
        h.ljust(col_widths[h]) for h in headers
    ) + " |"
    print(header_line)
    print("|" + "-".join("-" * col_widths[h] for h in headers) + "--|")

    # 打印数据行
    for method_idx, method in enumerate(methods):
        if method_idx < len(matrix):
            row_str = "| "
            row_str += method.ljust(col_widths['Method']) + " | "

            for metric_idx, metric in enumerate(metrics):
                value = f"{matrix[method_idx][metric_idx]:.2f}%"
                row_str += value.ljust(col_widths[metric]) + " | "

            print(row_str)


def plot_heatmap_from_results(results: Dict[str, Any], save_path: str = 'heatmap.png', use_mapped_names: bool = True):
    """
    从分析结果中绘制热力图并保存为图片。
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        if 'heatmap_data' not in results:
            print("错误: 分析结果中没有热力图数据。")
            return False

        heatmap_data = results['heatmap_data']

        # 选择使用映射后的名称还是原始名称
        if use_mapped_names:
            methods = heatmap_data['methods']
            title_suffix = "（映射后名称）"
        else:
            methods = heatmap_data['original_methods']
            title_suffix = "（原始名称）"

        metrics = heatmap_data['metrics']
        matrix = heatmap_data['matrix']

        # 转换数据为numpy数组
        data_array = np.array(matrix)

        # 创建图形
        fig, ax = plt.subplots(figsize=(14, 10))

        # 创建热力图
        im = ax.imshow(data_array, cmap='YlOrRd', aspect='auto')

        # 设置坐标轴
        ax.set_xticks(np.arange(len(metrics)))
        ax.set_yticks(np.arange(len(methods)))
        ax.set_xticklabels(metrics)
        ax.set_yticklabels(methods)

        # 旋转x轴标签
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # 添加颜色条
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Success Rate (%)", rotation=-90, va="bottom")

        # 在每个单元格中添加文本
        for i in range(len(methods)):
            for j in range(len(metrics)):
                text = ax.text(j, i, f"{matrix[i][j]:.1f}%",
                               ha="center", va="center",
                               color="white" if matrix[i][j] > 50 else "black",
                               fontsize=9)

        # 设置标题
        ax.set_title(f"Success Rate on Single Metric", fontsize=16, fontweight='bold', pad=20)

        # 添加网格线
        ax.set_xticks(np.arange(len(metrics) + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(methods) + 1) - 0.5, minor=True)
        ax.grid(which="minor", color="gray", linestyle='-', linewidth=0.5)
        ax.tick_params(which="minor", size=0)

        # 调整布局
        fig.tight_layout()

        # 保存图片
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"热力图已保存为: {save_path}")

        # 显示图片
        plt.show()

        return True

    except ImportError as e:
        print(f"错误: 无法导入matplotlib，请先安装: pip install matplotlib")
        return False
    except Exception as e:
        print(f"绘制热力图时出错: {e}")
        return False


# --- 主程序调用 ---

if __name__ == '__main__':
    # -----------------------------------------------------------------------
    # ！！！ 运行时，请修改以下变量为您本地的实际路径 ！！！
    # -----------------------------------------------------------------------

    # 评估结果文件 (基线和对照组) 路径
    EVAL_FILE = 'evaluation_results_temp.json'

    # 您的迭代攻击日志文件夹路径 (请替换为您实际的目录)
    LOGS_DIR = 'tree_attack_record'

    print(f"准备开始分析...")
    print(f"评估文件: {EVAL_FILE}")
    print(f"日志目录: {LOGS_DIR}")

    # 调用函数执行分析
    results = analyze_optimization_results(
        eval_file_path=EVAL_FILE,
        log_dir_path=LOGS_DIR
    )

    if results:
        # 保存结果到JSON文件
        save_results_to_json(results, 'attack_analysis_results.json')

        # 打印表格结果
        print_results_table(results)

        # 打印单一维度攻击成功率热力图数据
        print_single_metric_success_rates(results)

        # 询问是否绘制热力图
        plot_choice = input("\n是否绘制热力图？(y/n): ").strip().lower()
        if plot_choice == 'y' or plot_choice == 'yes':
            # 询问使用哪个名称版本
            name_choice = input("使用映射后的名称还是原始名称？(mapped/original/both): ").strip().lower()

            if name_choice == 'mapped' or name_choice == 'm':
                # 绘制使用映射后名称的热力图
                plot_heatmap_from_results(results, 'attack_success_heatmap_mapped.png', use_mapped_names=True)
            elif name_choice == 'original' or name_choice == 'o':
                # 绘制使用原始名称的热力图
                plot_heatmap_from_results(results, 'attack_success_heatmap_original.png', use_mapped_names=False)
            elif name_choice == 'both' or name_choice == 'b':
                # 绘制两个版本的热力图
                plot_heatmap_from_results(results, 'attack_success_heatmap_mapped.png', use_mapped_names=True)
                plot_heatmap_from_results(results, 'attack_success_heatmap_original.png', use_mapped_names=False)
            else:
                print("无效选择，将使用映射后的名称。")
                plot_heatmap_from_results(results, 'attack_success_heatmap.png', use_mapped_names=True)
    else:
        print("分析失败，无法生成结果。")