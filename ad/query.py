import requests
import sys
import os
import logging
import httpx
import json
from openai import OpenAI

from llm_utils import call_llm


def process_queries(input_file, output_file, model_list):
    """
    处理查询文件，对每个查询使用多个模型进行调用，并将结果保存到JSON文件

    Args:
        input_file (str): 输入的文本文件路径，每行一个查询
        output_file (str): 输出的JSON文件路径
        model_list (list): 要使用的模型列表
    """
    # 如果输出文件不存在，创建一个空的JSON数组
    if not os.path.exists(output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)

    # 读取已有的结果（如果有的话）
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except:
        results = []

    # 读取查询文件
    with open(input_file, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f.readlines() if line.strip()]

    # 处理每个查询
    for i, query in enumerate(queries):
        query = query + "Give me some recommended products and rank them in order."
        print(f"Processing query {i + 1}/{len(queries)}: {query}")

        # 存储当前查询的所有模型结果
        query_result = {
            "query": query,
            "result": []
        }

        # 对每个模型调用LLM
        for model in model_list:
            print(f"  Calling model: {model}")
            try:
                response = call_llm(model, query)
                model_result = {
                    "model": model,
                    "content": response["content"] or "",
                    "citation": response["references"]
                }
                query_result["result"].append(model_result)
            except Exception as e:
                print(f"    Error calling {model}: {str(e)}")
                # 即使出错也记录结果
                model_result = {
                    "model": model,
                    "content": "",
                    "citation": []
                }
                query_result["result"].append(model_result)

        # 将当前查询结果添加到总结果中
        results.append(query_result)

        # 立即写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"  Completed query {i + 1}")


def main(input_file, output_file, model_list):
    """主函数：规范化结构并执行查询处理。"""
    process_queries(input_file, output_file, model_list)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_FILE = "ad_dataset.txt"
    OUTPUT_FILE = "results_exa.json"
    MODEL_LIST = ["exa"]
    main(INPUT_FILE, OUTPUT_FILE, MODEL_LIST)
