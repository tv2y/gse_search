import os
import re
import json
from llm_utils import call_llm
from GEO.influence_judge import influence_judge


def get_query_contents(query, dir_path = "lima_clean_content"):
    """
    函数1：获取query对应的文件内容

    Args:
        query: 查询字符串

    Returns:
        tuple: (init_content, other_content, mutation_content)
            - init_content: 1.txt的内容
            - other_content: 2-5.txt的内容列表
            - mutation_content: 突变内容列表，每个元素是{'geo_method': 方法名, 'geo_content': 内容}
    """
    # 清理query得到目录名steamweilan
    query_clean = sanitize_filename(query)
    dir_path = os.path.join(dir_path, query_clean)

    init_content = ""
    other_content = []
    mutation_content = []

    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"目录不存在: {dir_path}")
        return init_content, other_content, mutation_content

    # 读取1.txt (init_content)
    file_1_path = os.path.join(dir_path, "1.txt")
    if os.path.exists(file_1_path):
        try:
            with open(file_1_path, 'r', encoding='utf-8') as f:
                init_content = f.read().strip()
        except Exception as e:
            print(f"读取文件 {file_1_path} 时出错: {e}")
            init_content = ""
    else:
        print(f"文件不存在: {file_1_path}")

    # 读取2-5.txt (other_content)
    for i in range(2, 6):
        file_path = os.path.join(dir_path, f"{i}.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    other_content.append(content)
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {e}")
                other_content.append("")
        else:
            print(f"文件不存在: {file_path}")
            other_content.append("")

    # 读取突变内容文件（除了1-5.txt的其他txt文件）
    try:
        for filename in os.listdir(dir_path):
            if filename.endswith('.txt') and filename not in ['1.txt', '2.txt', '3.txt', '4.txt', '5.txt']:
                file_path = os.path.join(dir_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        # 从文件名提取geo_method（去掉.txt后缀）
                        geo_method = filename[:-4]
                        mutation_content.append({
                            'geo_method': geo_method,
                            'geo_content': content
                        })
                except Exception as e:
                    print(f"读取突变文件 {file_path} 时出错: {e}")
    except Exception as e:
        print(f"读取目录 {dir_path} 时出错: {e}")

    return init_content, other_content, mutation_content


def generate_answer(query, content, other_content):
    """
    函数2：生成答案

    Args:
        query: 查询字符串
        content: 主要内容
        other_content: 其他内容列表 (2-5.txt的内容)

    Returns:
        dict: call_llm的返回结果
    """
    # 构建source_text
    source_text_parts = []

    # 添加主要content作为[1]
    source_text_parts.append(f"[1]:\n{content}")

    # 添加other_content作为[2]-[5]
    for i, other_content_item in enumerate(other_content, 2):
        source_text_parts.append(f"[{i}]:\n{other_content_item}")

    # 拼接所有source_text
    source_text = "\n\n".join(source_text_parts)

    # 构建提示词
    prompt = f"""
Write an accurate and concise answer for the given user question, using _only_ the provided summarized web search results.
The answer should be correct, high-quality, and written by an expert using an unbiased and journalistic tone. The user's language of choice such as English, Francais, Espamol, Deutsch, or should be used. The answer should be informative, interesting, and engaging. The answer's logic and reasoning should be rigorous and defensible. Every sentence in the answer should be _immediately followed_ by an in-line citation to the search result(s). 
The cited search result(s) should fully support _all_ the information in the sentence. Search results need to be cited using [index]. When citing several search results, use [1][2][3] format rather than [1, 2, 3]. You can use multiple search results to respond comprehensively while avoiding irrelevant search results.

Question: {query}

Search Results:
{source_text}
"""

    # 调用call_llm
    return call_llm("deepseek", prompt).get("content", "")


def evaluate_query(query, content, other_content):
    """
    函数3：执行完整的评估流程

    Args:
        query: 查询字符串
        content: 主要内容
        other_content: 其他内容列表

    Returns:
        tuple: (answer, result)
            - answer: LLM生成的答案
            - result: influence_judge的评估结果
    """
    # 执行函数2：生成答案
    llm_result = generate_answer(query, content, other_content)
    answer = llm_result

    print(answer)
    # 调用influence_judge进行评估
    result = influence_judge(query, answer, content)

    return answer, result


def batch_evaluate_query(query, init_content, other_content, mutation_content):
    """
    批量评估函数：评估原始内容和所有突变内容

    Args:
        query: 查询字符串
        init_content: 原始内容
        other_content: 其他内容列表
        mutation_content: 突变内容列表

    Returns:
        dict: 包含所有评估结果的结构
    """
    results = {
        'query': query,
        'scores': {}
    }

    evaluation_details = []

    # 评估原始内容
    print(f"\n=== 评估原始内容 ===")
    try:
        init_answer, init_result = evaluate_query(query, init_content, other_content)
        results['scores']['init'] = init_result['scores']
        evaluation_details.append({
            'type': 'init',
            'content': init_content,
            'answer': init_answer,
            'result': init_result
        })
        print(f"原始内容评估完成")
    except Exception as e:
        print(f"原始内容评估失败: {e}")
        results['scores']['init'] = None

    # 评估每个突变内容
    for mutation in mutation_content:
        geo_method = mutation['geo_method']
        geo_content = mutation['geo_content']

        print(f"\n=== 评估突变内容: {geo_method} ===")
        try:
            mutation_answer, mutation_result = evaluate_query(query, geo_content, other_content)
            results['scores'][geo_method] = mutation_result['scores']
            evaluation_details.append({
                'type': 'mutation',
                'geo_method': geo_method,
                'content': geo_content,
                'answer': mutation_answer,
                'result': mutation_result
            })
            print(f"突变内容 {geo_method} 评估完成")
        except Exception as e:
            print(f"突变内容 {geo_method} 评估失败: {e}")
            results['scores'][geo_method] = None

    # 保存详细评估记录
    save_evaluation_record(query, evaluation_details)

    return results


def save_evaluation_record(query, evaluation_details):
    """
    保存详细评估记录到record目录

    Args:
        query: 查询字符串
        evaluation_details: 评估详情列表
    """
    # 创建record目录
    record_dir = "record"
    os.makedirs(record_dir, exist_ok=True)

    # 使用处理后的query作为文件名
    record_filename = sanitize_filename(query) + ".txt"
    record_path = os.path.join(record_dir, record_filename)

    try:
        with open(record_path, 'w', encoding='utf-8') as f:
            f.write(f"Query: {query}\n")
            f.write("=" * 50 + "\n\n")

            for detail in evaluation_details:
                if detail['type'] == 'init':
                    f.write("【原始内容评估】\n")
                else:
                    f.write(f"【突变内容评估 - {detail['geo_method']}】\n")

                f.write("-" * 30 + "\n")
                f.write("内容:\n")
                f.write(detail['content'] + "\n\n")

                f.write("LLM回答:\n")
                f.write(detail['answer'] + "\n\n")

                f.write("评估结果:\n")
                f.write(json.dumps(detail['result'], indent=2, ensure_ascii=False) + "\n\n")

                f.write("=" * 50 + "\n\n")

        print(f"评估记录已保存到: {record_path}")
    except Exception as e:
        print(f"保存评估记录失败: {e}")


def load_existing_results(results_file):
    """
    加载已存在的结果文件

    Args:
        results_file: 结果文件路径

    Returns:
        list: 已存在的结果列表，如果文件不存在则返回空列表
    """
    if not os.path.exists(results_file):
        return []

    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载结果文件失败: {e}")
        return []


def save_evaluation_results(results_file, all_results):
    """
    保存所有评估结果到JSON文件

    Args:
        results_file: 结果文件路径
        all_results: 所有结果列表
    """
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"评估结果已保存到: {results_file}")
    except Exception as e:
        print(f"保存评估结果失败: {e}")


def is_query_processed(query, existing_results):
    """
    检查query是否已经处理过

    Args:
        query: 查询字符串
        existing_results: 已存在的结果列表

    Returns:
        bool: 如果已处理返回True，否则返回False
    """
    for result in existing_results:
        if result.get('query') == query:
            return True
    return False


def process_queries_from_file(query_file_path, results_file="evaluation_results.json"):
    """
    从文件读取query列表并批量处理

    Args:
        query_file_path: 包含query的文件路径
        results_file: 结果文件路径
    """
    # 读取query列表
    try:
        with open(query_file_path, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"读取query文件失败: {e}")
        return

    if not queries:
        print("没有读取到任何query")
        return

    print(f"读取到 {len(queries)} 个query")

    # 加载已有结果
    existing_results = load_existing_results(results_file)
    print(f"已存在 {len(existing_results)} 个结果")

    # 处理每个query
    processed_count = 0
    skipped_count = 0

    for i, query in enumerate(queries, 1):
        print(f"\n=== 处理第 {i}/{len(queries)} 个query: '{query}' ===")

        # 检查是否已处理
        if is_query_processed(query, existing_results):
            print(f"跳过query '{query}'，已存在结果")
            skipped_count += 1
            continue

        # 获取所有内容
        init_content, other_content, mutation_content = get_query_contents(query)

        if not init_content:
            print(f"跳过query '{query}'，无法获取内容")
            skipped_count += 1
            continue

        print(f"找到 {len(mutation_content)} 个突变内容")
        for mutation in mutation_content:
            print(f"- {mutation['geo_method']}")

        # 批量评估所有内容
        try:
            results = batch_evaluate_query(query, init_content, other_content, mutation_content)

            # 添加到结果列表
            existing_results.append(results)

            # 保存更新后的结果
            save_evaluation_results(results_file, existing_results)

            processed_count += 1
            print(f"完成处理query '{query}'")
        except Exception as e:
            print(f"处理query '{query}'时出错: {e}")
            skipped_count += 1

    print(f"\n=== 处理完成 ===")
    print(f"成功处理: {processed_count} 个query")
    print(f"跳过处理: {skipped_count} 个query")
    print(f"结果文件: {results_file}")


def sanitize_filename(filename):
    """清理文件名，移除或替换非法字符"""
    # 替换Windows和Linux中不允许的字符
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # 限制文件名长度（避免路径过长）
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip()


# 使用示例
if __name__ == "__main__":
    # 指定包含query的文件路径
    query_file_path = "dataset/test.txt"  # 请修改为实际的文件路径
    results_file = "result/lima_evaluation_results.json"  # 结果文件路径

    if not os.path.exists(query_file_path):
        print(f"query文件不存在: {query_file_path}")
        print("请创建一个包含query的文件，每行一个query")
    else:
        process_queries_from_file(query_file_path, results_file)