import json
import re
from collections import defaultdict


def analyze_citations(input_file, output_file):
    """
    分析引用情况，确保 nums 和 ratio 数组长度与引用源列表长度一致。
    如果某个引用在正文中未出现，则对应位置填充 0。
    """
    try:
        # 读取输入 JSON 文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: 找不到文件 {input_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: {input_file} 格式不正确")
        return

    results = []

    # 遍历每个 Query 数据
    for query_data in data:
        query = query_data.get('query', '')
        result_entries = []

        # 遍历每个模型的回答内容
        for entry in query_data.get('result', []):
            model = entry.get('model', '')
            content = entry.get('content', '')
            # 获取该回答对应的引用源列表（用于确定数组应有的长度）
            source_citations = entry.get('citation', [])
            citation_count = len(source_citations)

            # 在正文中匹配所有形如 [1], [2], [10] 的引用标记
            citations_found = re.findall(r'\[(\d+)\]', content)

            # 统计正文中每个引用编号出现的频次
            citation_freq = defaultdict(int)
            for cite in citations_found:
                citation_freq[int(cite)] += 1

            total_mentions = len(citations_found)
            nums = []
            ratio = []

            # 核心修改点：基于引用源的总数构建对齐的数组
            if citation_count > 0:
                # 假设引用编号从 1 开始（[1], [2], ...）
                for i in range(1, citation_count + 1):
                    # 获取该编号在正文中出现的次数，若无则为 0
                    count = citation_freq[i]
                    nums.append(count)

                    # 计算该引用次数占正文总引用次数的比例
                    if total_mentions > 0:
                        ratio.append(round(count / total_mentions, 2))
                    else:
                        ratio.append(0.0)
            else:
                # 如果 citation 列表本身为空，保持为空数组
                nums = []
                ratio = []

            # 组装当前模型的分析结果
            result_entries.append({
                "model": model,
                "content": content,
                "nums": nums,
                "ratio": ratio,
                "citation_num": citation_count
            })

        # 将当前 Query 的结果加入总表
        results.append({
            "query": query,
            "result": result_entries
        })

    # 将结果写入输出文件
    # 使用 'w' 模式确保写入的是一个合法的 JSON 数组，避免 'a' 模式导致的 JSON 格式破坏
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def main(input_filename, output_filename):
    """主函数：规范化结构并执行引用分析。"""
    analyze_citations(input_filename, output_filename)
    print(f"分析完成！结果已保存至: {output_filename}")


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_FILENAME = "results.json"
    OUTPUT_FILENAME = "citation_analysis.json"
    main(INPUT_FILENAME, OUTPUT_FILENAME)