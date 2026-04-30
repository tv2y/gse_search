# -*- coding: utf-8 -*-
import sys
import os
import logging

from llm_utils import call_llm
from utils import setup_logging, load_json_file, save_json_file


def load_queries_from_txt(txt_file):
    queries = []
    with open(txt_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            query = line.strip()
            if not query:
                continue
            queries.append({
                "id": f"txt_{idx}",
                "query": query
            })
    return queries


def process_query(query_data, model_type='perplexity'):
    try:
        query_id = query_data.get('id', '')
        query_text = query_data.get('query', '')

        if not query_id or not query_text:
            logging.warning(f"无效的查询数据: {query_data}")
            return None

        logging.info(f"处理查询，ID: {query_id}")

        response = call_llm(model_type, query_text)

        return {
            'id': query_id,
            'query': query_text,
            'answer': response.get('content', ''),
            'references': response.get('references', []),
            'model_type': model_type
        }
    except Exception as e:
        logging.error(f"处理查询时发生错误: {str(e)}")
        return None


def run_query_tool(model_type, input_file, output_file, log_file):
    try:
        setup_logging(log_file)

        if not os.path.exists(input_file):
            logging.error(f"输入文件 {input_file} 不存在")
            return

        queries = load_queries_from_txt(input_file)
        if not queries:
            logging.error("TXT 中未读取到任何 query")
            return

        # 🔹 读取已有结果，构建 (id, model_type) → result 的映射
        result_map = {}

        if os.path.exists(output_file):
            existing_results = load_json_file(output_file) or []
            if not isinstance(existing_results, list):
                existing_results = [existing_results]

            for item in existing_results:
                key = (item.get("id"), item.get("model_type"))
                result_map[key] = item

        total_queries = len(queries)
        new_or_updated = 0

        for i, query_data in enumerate(queries):
            key = (query_data.get("id"), model_type)
            existing = result_map.get(key)

            # ✅ 已有有效结果 → 跳过
            if existing and existing.get("answer"):
                logging.info(f"跳过已有有效结果 {i + 1}/{total_queries}: {key[0]}")
                continue

            logging.info(f"处理查询 {i + 1}/{total_queries}: {key[0]}")
            new_result = process_query(query_data, model_type)
            if not new_result:
                continue

            # ✅ 新结果覆盖旧空结果 / 或新增
            result_map[key] = new_result
            new_or_updated += 1

        # 🔹 写回最终结果
        final_results = list(result_map.values())
        save_json_file(final_results, output_file)

        logging.info(
            f"处理完成：新增/更新 {new_or_updated} 条，总结果 {len(final_results)} 条"
        )

    except Exception as e:
        logging.error(f"运行查询工具时发生错误: {str(e)}")



if __name__ == "__main__":
    run_query_tool(
        model_type="perplexity",
        input_file="./pinish/query.txt",
        output_file="./pinish/answer/answer_gpt.json",
        log_file="./pinish/log.log"
    )
