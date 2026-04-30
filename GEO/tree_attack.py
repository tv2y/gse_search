import json
import time
import os
from typing import List, Dict, Tuple, Any
from mutation_test import generate_answer
from geo_method import batch_apply_attacks
from influence_judge import influence_judge

# ==============================================================================
# 外部函数占位符 (External Functions Placeholders)
# 假设这些函数已在别处定义并导入。
# 实际代码运行时需要确保这些函数的导入和可用性。
# ==============================================================================
# def batch_apply_attacks(query: str, clean_content: str, method_names: List[str]) -> Dict[str, str]: ...
# def generate_answer(query: str, content: str, other_content: List[str]) -> Any: ...
# def influence_judge(query: str, answer: Any, content: str) -> Dict[str, Any]: ...

# ==============================================================================
# 配置文件 (Configuration)
# ==============================================================================
GUIDANCE_FILE = "selection.json"
DIMENSION_NAMES = ["CF", "CCR", "AA", "SF", "KIC", "SC", "AD"]

# 用户提供的优化方法映射 (User-provided Optimization Method Mapping)
# 将 selection.json 中的友好名称映射到实际函数调用的内部名称
METHOD_MAPPING = {
    # SEO 方法 (SEO Methods)
    "Keyword Stuffing": "关键词堆砌",  # 关键词堆砌

    # GEO 方法 (GEO Methods)
    "Authoritative Tone": "权威语气增强",  # 权威语气增强
    "Data Support": "数据支撑引入",  # 数据支撑引入
    "Citation Addition": "文献引用增加",  # 文献引用增加
    "Unique Terms": "专有名词添加",  # 专有名词添加

    # 注入攻击方法 (Injection Attacks)
    "Coercive Command": "指令劫持",  # 指令劫持
    "Reputation Attack": "信誉攻击",  # 信誉攻击
    "Emotional Manipulation": "情感操纵"  # 情感操纵
    # 映射文件中的英文/友好名称到内部的 snake_case 名称
}

# 反向映射：用于在日志和输出中显示友好名称
REVERSE_METHOD_MAPPING = {v: k for k, v in METHOD_MAPPING.items()}


def load_guidance(filepath: str) -> Dict[str, Any]:
    """加载优化指导文件 (Load optimization guidance file)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：未找到指导文件 {filepath}。请确保文件存在。")
        return {}
    except json.JSONDecodeError:
        print(f"错误：指导文件 {filepath} 格式不正确。")
        return {}


# 尝试加载全局配置数据
try:
    GUIDANCE_DATA = load_guidance(GUIDANCE_FILE)
except NameError:
    GUIDANCE_DATA = {}


# ==============================================================================
# 日志辅助函数 (Logging Helpers)
# ==============================================================================

def init_log_file(log_file_path: str, query: str, max_rounds: int, target_scores: List[float]):
    """初始化日志文件，写入元数据和开始标记"""
    with open(log_file_path, 'w', encoding='utf-8') as f:
        metadata = {
            "start_time": time.strftime("%Y%m%d_%H%M%S"),
            "query": query,
            "max_rounds": max_rounds,
            "target_scores": target_scores,
            "dimension_names": DIMENSION_NAMES,
            "method_mapping": METHOD_MAPPING,  # 记录映射关系
            "log_entries": []  # 初始化日志条目列表
        }
        json.dump(metadata, f, ensure_ascii=False, indent=4)


def append_log_entry(log_file_path: str, entry: Dict[str, Any]):
    """
    读取整个文件，更新 log_entries 列表，然后重新写入文件。
    用于确保 JSON 结构的有效性，并实现即时详细记录。
    """
    try:
        with open(log_file_path, 'r+', encoding='utf-8') as f:
            # 1. 读取现有内容
            f.seek(0)
            data = json.load(f)

            # 2. 追加新条目
            data['log_entries'].append(entry)

            # 3. 清空文件并写入新内容
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"警告：日志追加失败：{e}")


def check_success(current_scores: List[float], target_scores: List[float]) -> bool:
    """检查是否所有当前得分都超过了目标得分 (Check if all current scores exceed target scores)"""
    if len(current_scores) != len(target_scores):
        raise ValueError("当前得分数组和目标得分数组长度不匹配。")

    return all(current_scores[i] >= target_scores[i] for i in range(len(current_scores)))


# ==============================================================================
# 核心组件函数 (Core Component Functions) - 使用英文命名
# ==============================================================================

def attacker(
        query: str,
        content: str,
        geo_methods_friendly: List[str]
) -> Dict[str, str]:
    """
    攻击器 (Attacker):
    将友好名称映射到内部名称，并调用外部函数。

    入参: geo_methods_friendly (友好名称列表)
    出参: 包含不同优化方法结果的 content 字典 (Dict[internal_method_name, new_content])
    """

    # 1. 映射友好名称到内部名称
    geo_methods_internal = [METHOD_MAPPING.get(name, name) for name in geo_methods_friendly]

    print(f"Attacker：应用 {len(geo_methods_friendly)} 种方法...")

    # 外部函数调用，返回多个修改后的内容
    # ⚠️ 假设 batch_apply_attacks 接受内部名称
    modified_contents = batch_apply_attacks(query, content, geo_methods_internal)

    return modified_contents


def target(
        query: str,
        content_map: Dict[str, str],
        other_docs: List[str]
) -> List[Dict[str, Any]]:
    """
    被攻击目标 (Target):
    入参: query, content_map (内部优化方法名称到内容的映射), other_docs
    为每个修改后的 content 生成回答。

    出参: 结果列表，每个元素包含:
          {'method': str, 'content': str, 'answer': Any}
    """
    results = []

    for method, content in content_map.items():
        # 显示友好的方法名称（如果存在）
        friendly_name = REVERSE_METHOD_MAPPING.get(method, method)
        print(f" -> 针对方法 {friendly_name} 生成回答...")

        # 1. 回答生成 (Answer Generation)
        try:
            answer = generate_answer(query, content, other_docs)

            results.append({
                'method': method,  # 记录内部名称
                'content': content,
                'answer': answer,
                'evaluation': None,  # 评估结果留待 evaluator 填充
                'scores': []
            })
        except Exception as e:
            print(f"警告：处理方法 {friendly_name} 时生成回答失败：{e}")
            results.append({
                'method': method,
                'content': content,
                'answer': None,
                'evaluation': {'error': str(e)},
                'scores': []
            })

    return results


def evaluator(
        query: str,
        results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    评估器 (Evaluator):
    入参: query, results (包含回答的列表)。调用外部函数influence_judge对回答进行评估。

    出参: 更新了 evaluation 和 scores 的结果列表。
    """
    evaluated_results = []

    for result in results:
        method = result['method']
        answer = result['answer']

        if answer is None:
            # 跳过生成回答失败的条目
            evaluated_results.append(result)
            continue

        friendly_name = REVERSE_METHOD_MAPPING.get(method, method)
        print(f" -> 对方法 {friendly_name} 的回答进行评估...")

        try:
            # 2. 评估器 (Evaluation)
            # ⚠️ influence_judge 接收 content 作为入参，尽管 result 中已经存在
            evaluation_results = influence_judge(query, answer, result['content'])

            result['evaluation'] = evaluation_results.get('analysis', {})
            result['scores'] = evaluation_results.get('scores', [0.0] * len(DIMENSION_NAMES))
            evaluated_results.append(result)

        except Exception as e:
            print(f"警告：处理方法 {friendly_name} 时评估失败：{e}")
            result['evaluation'] = {'error': str(e)}
            result['scores'] = [0.0] * len(DIMENSION_NAMES)
            evaluated_results.append(result)

    return evaluated_results


def select_metric_to_improve(
        scores: List[float],
        target_scores: List[float],
        guidance: Dict[str, Any]
) -> str:
    """
    根据得分 (scores) 和目标 (target_scores)，使用动态权重逻辑选择下一个需要优化的指标。
    优先级分数 P_i = 差距百分比 G_i * 动态权重 W_i。

    入参: scores, target_scores, guidance (GUIDANCE_DATA)
    出参: 下一轮优化的指标名称 (str) 或 None
    """
    # 动态权重定义：Bottom 33% = 3.0 (最高)，Middle 34% = 2.0，Top 33% = 1.0 (最低)
    WEIGHTS = {"Bottom 33%": 3.0, "Middle 34%": 2.0, "Top 33%": 1.0}
    metric_to_improve = None
    max_priority_score = -float('inf')

    for i, dim_name in enumerate(DIMENSION_NAMES):
        target = target_scores[i]
        score = scores[i]

        # 1. 指标过滤：只考虑未达标指标 (score < target)
        if score < target:

            # 2. 计算百分比差距 G_i: G_i = (target - score) / target
            if target > 0:
                G_i = (target - score) / target
            else:
                continue

                # 3. 确定动态权重 W_i
            W_i = 1.0  # 默认权重
            try:
                if guidance and 'score_thresholds' in guidance and dim_name in guidance['score_thresholds']:
                    thresholds = guidance['score_thresholds'][dim_name]

                    # 确定得分区间
                    if score <= thresholds['bottom_threshold']:
                        category = "Bottom 33%"
                    elif score <= thresholds['middle_threshold']:
                        category = "Middle 34%"
                    else:
                        category = "Top 33%"

                    # 查表获取权重
                    W_i = WEIGHTS.get(category, 1.0)

            except KeyError:
                # 配置文件中缺少阈值配置，使用默认权重
                W_i = 1.0

            # 4. 计算优先级分数 P_i: P_i = G_i * W_i
            P_i = G_i * W_i

            # 5. 选择最高优先级分数
            if P_i > max_priority_score:
                max_priority_score = P_i
                metric_to_improve = dim_name
            # 平局决胜：如果优先级分数相等，选择差距百分比 G_i 更大的指标
            elif P_i == max_priority_score and metric_to_improve is not None:
                current_best_i = DIMENSION_NAMES.index(metric_to_improve)
                # 计算当前最佳指标的 G_i
                current_best_G_i = (target_scores[current_best_i] - scores[current_best_i]) / target_scores[
                    current_best_i]
                if G_i > current_best_G_i:
                    max_priority_score = P_i
                    metric_to_improve = dim_name

    if metric_to_improve is not None:
        print(f" -> 选定下一轮优化指标: {metric_to_improve} (优先级得分: {max_priority_score:.4f})")

    return metric_to_improve


def optimizer(
        evaluation_results: List[Dict[str, Any]],
        current_best_scores: List[float],
        target_scores: List[float]
) -> Tuple[str, List[float], str]:
    """
    优化器 (Optimizer):
    入参: 评估结果数组，当前最佳得分，目标得分。
    选择最优 content 和得分 (基于未达标指标的平均百分比提升)，并确定下一轮应该优化的指标。

    出参: 最优 content (str), 最优 content 的得分 (List[float]), 下一轮优化的指标名称 (str)
    """
    print("\nOptimizer：正在选择下一轮最优内容和优化指标...")

    # --- 1. 寻找最佳内容 (Maximize Average Percentage Improvement - API) ---
    max_api = -float('inf')
    best_result = None

    # 将当前的 current_best_scores 视为本轮的基线得分
    baseline_scores = current_best_scores

    for result in evaluation_results:
        # 确保有得分数据且回答生成成功
        if not result['scores'] or result['answer'] is None:
            continue

        new_scores = result['scores']
        total_improvement = 0.0
        failing_metric_count = 0

        for i in range(len(DIMENSION_NAMES)):
            target = target_scores[i]
            prev_best = baseline_scores[i]
            new_score = new_scores[i]

            # 1.1 指标过滤：只考虑当前结果仍未达标的指标 (new_score < target)
            if prev_best < target:

                # 1.2 百分比提升计算：相对于上一轮最佳得分的提升，以目标得分为基准
                improvement = new_score - prev_best

                if target > 0:
                    percentage_improvement = improvement / target
                    total_improvement += percentage_improvement
                    failing_metric_count += 1

        # 1.3 平均提升 (API)
        api = total_improvement / failing_metric_count if failing_metric_count > 0 else 0.0  # 设为 0.0 以避免在所有指标都达标时出现 -inf

        # 1.4 选择标准：最大化 API
        if api > max_api:
            max_api = api
            best_result = result
        # 平局决胜：如果 API 相等，选择总得分更高的内容（次要标准）
        elif api == max_api and best_result is not None:
            current_total_score = sum(best_result['scores'])
            new_total_score = sum(new_scores)
            if new_total_score > current_total_score:
                best_result = result

    # 确定新内容和得分
    if best_result is None:
        # 应该总能选出 Baseline_Unmodified 作为保底
        print("警告：未能选定任何有效内容，维持当前最佳内容。")
        # 尝试从评估结果中找到 Baseline_Unmodified 的原始内容
        baseline_result = next((r for r in evaluation_results if r['method'] == 'Baseline_Unmodified'), None)
        new_content = baseline_result['content'] if baseline_result else ""
        new_scores = current_best_scores
    else:
        friendly_name = REVERSE_METHOD_MAPPING.get(best_result['method'], best_result['method'])
        print(f" -> 选定最佳内容（平均百分比提升 API: {max_api:.4f}）优化方法: {friendly_name} ({best_result['method']})")
        new_content = best_result['content']
        new_scores = best_result['scores']

    # --- 2. 确定下一个要优化的指标 (使用辅助函数 select_metric_to_improve) ---
    metric_to_improve = select_metric_to_improve(
        scores=new_scores,
        target_scores=target_scores,
        guidance=GUIDANCE_DATA
    )

    # 如果所有指标都达标，则返回 None (select_metric_to_improve 会处理这种情况)
    if metric_to_improve is None:
        print(" -> 所有指标均已达标或无指标需优化。")

    return new_content, new_scores, metric_to_improve


def selector(
        current_content: str,
        current_scores: List[float],
        metric_to_improve: str,
        guidance: Dict[str, Any]
) -> List[str]:
    """
    选择器 (Selector):
    入参: 评估结果和需要继续优化的指标，并依据指导文件选择三种优化方法并返回content,geo_methods。

    出参: 友好优化方法列表 (List[str])
    """

    if not guidance or not metric_to_improve:
        print("警告：缺少指导数据或无需优化指标，返回空优化方法。")
        return []

    try:
        dim_index = DIMENSION_NAMES.index(metric_to_improve)
        current_score = current_scores[dim_index]

        thresholds = guidance['score_thresholds'][metric_to_improve]
        recommendations = guidance['recommendations'][metric_to_improve]

        category = ""
        if current_score <= thresholds['bottom_threshold']:
            category = "Bottom 33%"
        elif current_score <= thresholds['middle_threshold']:
            category = "Middle 34%"
        else:
            category = "Top 33%"

        # 返回 selection.json 中定义的友好名称
        selected_methods = recommendations.get(category, [])

        print(f"\nSelector：针对指标 {metric_to_improve} (当前得分: {current_score:.3f})，选择了 {category} 的推荐方法。")
        return selected_methods

    except KeyError as e:
        print(f"错误：指导文件中缺少 {metric_to_improve} 的数据。{e}")
        return []
    except ValueError as e:
        print(f"错误：指标名称 {metric_to_improve} 无效。{e}")
        return []


def run_optimization_framework(
        query: str,
        initial_content: str,
        other_docs: List[str],
        max_rounds: int,
        target_scores: List[float],
        log_folder: str = "optimization_logs"
) -> Tuple[bool, str, List[float]]:
    """
    迭代内容优化主框架 (Main Iterative Content Optimization Framework)

    入参:
      query: 用户查询
      initial_content: 初始主要文档内容
      other_docs: 其它参考文档数组
      max_rounds: 最大迭代轮次
      target_scores: 目标得分数组
      log_folder: 日志文件存储路径

    出参:
      Tuple[bool, str, List[float]]: (优化是否成功, 最终内容, 最终得分)
    """

    # 1. 初始化和日志设置
    os.makedirs(log_folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(log_folder, f"attack_log_{timestamp}.json")

    current_content = initial_content
    current_scores = [0.0] * len(DIMENSION_NAMES)
    success = False

    # 关键：初始化下一轮要优化的指标，初始设为 None
    metric_to_improve = None

    init_log_file(log_file_path, query, max_rounds, target_scores)

    print("=============================================")
    print(f"启动攻击框架 (Start Attack Framework)")
    print(f"目标得分：{list(zip(DIMENSION_NAMES, target_scores))}")
    print(f"日志路径：{log_file_path}")
    print("=============================================")

    # 2. 初始评估 (Round 0: Initial Evaluation)
    print("\n--- Round 0: Initial Content Evaluation ---")

    # 2.1 Target - 生成初始回答
    initial_content_map = {'Initial': initial_content}
    initial_answers = target(query, initial_content_map, other_docs)

    append_log_entry(log_file_path, {
        "step": "Round 0 - Target",
        "details": [{k: v for k, v in item.items() if k != 'content'} for item in initial_answers]
    })

    # 2.2 Evaluator - 评估初始回答
    initial_eval_results = evaluator(query, initial_answers)

    append_log_entry(log_file_path, {
        "step": "Round 0 - Evaluator",
        "details": [{k: v for k, v in item.items() if k != 'content'} for item in initial_eval_results]
    })

    if not initial_eval_results:
        print("框架初始化失败：无法对初始内容进行评估。")
        return False, initial_content, current_scores

    initial_result = initial_eval_results[0]
    current_content = initial_content
    current_scores = initial_result['scores']

    print(f"初始得分：{list(zip(DIMENSION_NAMES, current_scores))}")

    # *** 新增逻辑: 确定 Round 1 的优化指标 ***
    # 使用动态优先级逻辑确定初始优化指标
    metric_to_improve = select_metric_to_improve(
        scores=current_scores,
        target_scores=target_scores,
        guidance=GUIDANCE_DATA
    )

    # 3. 迭代优化循环
    for r in range(1, max_rounds + 1):
        print(f"\n=============================================")
        print(f"--- Round {r}: Iterative Attack ---")
        print(f"当前最佳得分：{list(zip(DIMENSION_NAMES, current_scores))}")

        # A. 检查成功条件
        if check_success(current_scores, target_scores):
            print("\n🎉 Attack Success: All metrics achieved!")
            success = True
            break

        # B. 使用上一轮优化器确定的指标
        print(f"本轮优化指标：{metric_to_improve}")

        if metric_to_improve is None:
            print("\n✅ Attack Terminated: No further metrics to improve.")
            success = True
            break

        # *** 关键改动 #1: 保存本轮的基线内容和得分 (上一轮的胜出者) ***
        baseline_content = current_content
        baseline_scores = current_scores

        # C. Selector
        # 返回的是友好名称列表
        improvement_methods_friendly = selector(
            current_content,
            current_scores,
            metric_to_improve,
            GUIDANCE_DATA
        )

        append_log_entry(log_file_path, {
            "round": r,
            "step": "Selector",
            "metric_chosen": metric_to_improve,
            "methods_applied": improvement_methods_friendly  # 记录友好名称
        })

        if not improvement_methods_friendly:
            print(f"警告：针对指标 {metric_to_improve} 没有推荐的方法，提前终止。")
            break

        # D. Attacker
        # 攻击器内部会将友好名称映射到内部名称并调用外部函数。
        modified_content_map = attacker(
            query,
            current_content,
            improvement_methods_friendly
        )

        # 记录内部方法名称和完整内容
        loggable_contents = {REVERSE_METHOD_MAPPING.get(k, k): v for k, v in modified_content_map.items()}

        append_log_entry(log_file_path, {
            "round": r,
            "step": "Attacker",
            "modified_contents": loggable_contents  # 记录完整内容
        })

        # E. Target - 生成回答
        # 只生成修改后的内容的回答
        all_answers = target(
            query,
            modified_content_map,
            other_docs
        )

        # 仅记录非 content 部分
        loggable_answers = []
        for item in all_answers:
            log_item = {k: v for k, v in item.items() if k != 'content'}
            log_item['method_friendly'] = REVERSE_METHOD_MAPPING.get(item['method'], item['method'])
            loggable_answers.append(log_item)

        append_log_entry(log_file_path, {
            "round": r,
            "step": "Target",
            "results_with_answers": loggable_answers
        })

        # F. Evaluator - 评估回答
        # 只评估修改后的内容的回答。 evaluator 内部会跳过 'Baseline_Unmodified'
        all_eval_results = evaluator(query, all_answers)

        # *** 关键改动 #2: 手动注入 Baseline_Unmodified 结果 (上一轮的得分) ***
        # 使用上一轮的胜出者及其评估结果作为本轮的基线，避免重复评估。
        baseline_entry = {
            'method': 'Baseline_Unmodified',
            'content': baseline_content,
            'answer': {'note': 'Previous round winner content, score reused.'},
            'evaluation': {'note': 'Score reused from previous round.'},
            'scores': baseline_scores
        }
        all_eval_results.append(baseline_entry)

        # 仅记录非 content 部分
        loggable_evals = []
        for item in all_eval_results:
            log_item = {k: v for k, v in item.items() if k != 'content'}
            log_item['method_friendly'] = REVERSE_METHOD_MAPPING.get(item['method'], item['method'])
            loggable_evals.append(log_item)

        append_log_entry(log_file_path, {
            "round": r,
            "step": "Evaluator",
            "details": loggable_evals
        })

        # G. Optimizer
        # optimizer 返回下一轮的 content, score, 以及 metric_to_improve
        new_content, new_scores, next_metric_to_improve = optimizer(
            all_eval_results,
            current_scores,
            target_scores
        )

        # H. 更新状态
        current_content = new_content
        current_scores = new_scores
        # 更新下一轮要优化的指标
        metric_to_improve = next_metric_to_improve

        append_log_entry(log_file_path, {
            "round": r,
            "step": "Optimizer - Status Update",
            "new_best_scores": current_scores,
            "new_best_content": current_content,  # 完整内容
            "next_metric_to_improve": metric_to_improve,
            "is_success": check_success(current_scores, target_scores)
        })

        if check_success(current_scores, target_scores):
            print("\n🎉 Attack Success: All metrics achieved!")
            success = True
            break

    # 4. 结束和清理

    # 最终状态记录（虽然每步都记录了，但做最终标记）
    append_log_entry(log_file_path, {
        "step": "Final Status",
        "success": success,
        "final_scores": current_scores,
        "final_content": current_content  # 记录最终完整内容
    })

    print("=============================================")
    print("攻击框架运行结束。")
    print(f"最终结果：成功状态={success}")
    print(f"日志文件已保存至：{log_file_path}")

    return success, current_content, current_scores


# ==============================================================================
# 示例运行 (Example Usage - Requires external functions defined below)
# ==============================================================================

if __name__ == '__main__':
    # 运行配置
    sample_query = "什么是黑洞以及它如何影响空间时间？"
    sample_initial_content = "黑洞是宇宙中引力极强的区域，光线也无法逃脱。它们由大质量恒星的引力坍塌形成。根据爱因斯坦的理论，黑洞通过扭曲周围的时空来影响空间时间。"
    sample_other_docs = [
        "爱因斯坦的广义相对论预言了黑洞的存在。",
        "黑洞周围的区域被称为事件视界。事件视界是光线逃逸的临界点。",
    ]
    sample_max_rounds = 2
    # 目标得分 (CF, CCR, AA, SF, KIC, SC, AD)
    sample_target_scores = [0.10, 0.10, 0.5, 0.5, 0.50, 0.50, 1]

    run_optimization_framework(
        query=sample_query,
        initial_content=sample_initial_content,
        other_docs=sample_other_docs,
        max_rounds=sample_max_rounds,
        target_scores=sample_target_scores
    )