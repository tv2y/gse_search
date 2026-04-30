import os
import sys
import argparse

# 将当前目录加入 Python 搜索路径，以便导入同目录下的其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入各模块
from query import main as query_main
from web_analysis import main as web_main
from judge import main as judge_main
from sentence_divide import main as divide_main
from sentences_analysis import main as analysis_main
from translate_analysis import main as translate_main


def main():
    # 使用 argparse 处理命令行输入
    parser = argparse.ArgumentParser(description="Rumor Analysis Workflow Entry Point")
    parser.add_argument("input_excel", help="Path to the input Excel file (containing 'rumor' and 'chinese' columns)")
    parser.add_argument("--output_dir", default=os.path.join(current_dir, "results"), help="Directory to save output files")
    parser.add_argument("--cache_dir", default=os.path.join(current_dir, "cache"), help="Directory for cache files")
    
    args = parser.parse_args()
    
    # 确保目录存在
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    if not os.path.exists(args.cache_dir):
        os.makedirs(args.cache_dir)
    
    # 定义中间文件路径
    query_output = os.path.join(args.output_dir, "query_results.json")
    query_cache = os.path.join(args.cache_dir, "query_cache.json")
    judge_output = os.path.join(args.output_dir, "judge_combined_results.json")
    divide_output = os.path.join(args.output_dir, "processed_results.json")
    translate_output_dir = os.path.join(args.output_dir, "figures_similarity")
    
    # 执行流程
    print("=== Step 1: Querying Rumors (query.py) ===")
    query_main(args.input_excel, query_output, query_cache, ['perplexity', 'youchat'])
    
    print("\n=== Step 2: Web Content Analysis & Caching (web_analysis.py) ===")
    web_main(query_output)
    
    print("\n=== Step 3: Combined Content & Reference Judging (judge.py) ===")
    judge_main(query_output, judge_output)
    
    print("\n=== Step 4: Sentence Segmentation (sentence_divide.py) ===")
    divide_main(judge_output, divide_output)
    
    print("\n=== Step 5: Final Sentence Relationship Analysis (sentences_analysis.py) ===")
    analysis_main(divide_output)
    
    print("\n=== Step 6: Translation Similarity Analysis (translate_analysis.py) ===")
    translate_main(args.input_excel, translate_output_dir)
    
    print("\n=== Workflow Completed Successfully! ===")


if __name__ == "__main__":
    main()
