import os
import sys

# 确保可导入本目录下模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from query import main as query_main
from catition_analysis import main as cit_main
from ad_analysis import main as ad_main
from get_html import main as get_html_main
from handel_html import main as handel_main
from result_merge import main as merge_main


def main(input_query_file, model_name="gpt"):
    # 统一中间产物命名（位于 ad 目录下）
    results_file = os.path.join(current_dir, f"results_{model_name}.json")
    citation_analysis_file = os.path.join(current_dir, f"citation_analysis_{model_name}.json")
    analyzed_results_file = os.path.join(current_dir, f"analyzed_results_{model_name}.json")
    web_index_file = os.path.join(current_dir, f"web_index_{model_name}.json")
    final_output_file = os.path.join(current_dir, f"analysis_results_final_{model_name}.json")

    # 爬取与处理目录（按模型名分子目录）
    crawled_base = os.path.join(current_dir, "crawled_content")
    processed_base = os.path.join(current_dir, "processed_content")

    # 1) 调用查询：读取待测文件，调用 LLM，生成结果文件
    query_main(input_query_file, results_file, [model_name])

    # 2) 引用统计分析：生成引用分析文件（包含各模型 ratio）
    cit_main(results_file, citation_analysis_file)

    # 3) 广告产品分析：生成分析结果文件（产品/广告提取结果）
    ad_main(results_file, analyzed_results_file)

    # 4) 基于 ratio>0 的引用链接爬取网页正文（写入 crawled_content/<model>/...）
    get_html_main(citation_analysis_file, results_file, crawled_base)

    # 5) 网页正文清洗与分类（写入 processed_content/<model>/...，索引写入 web_index_<model>.json）
    handel_main([
        {
            "input_dir": os.path.join(crawled_base, model_name),
            "output_dir": os.path.join(processed_base, model_name),
            "query_file": input_query_file,
            "index_file": web_index_file
        }
    ])

    # 6) 结果合并：将网页分类结果合并回最终的分析结果中
    merge_main(web_index_file, results_file, analyzed_results_file, final_output_file)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入参数
    INPUT_QUERY_FILE = os.path.join(os.path.dirname(__file__), "ad_dataset.txt")
    MODEL_NAME = "gpt"  # 可在此处修改模型名称，如 "doubao", "youchat" 等
    main(INPUT_QUERY_FILE, MODEL_NAME)
