import json
import os

def extract_english_queries(input_json_path, output_txt_path):
    """
    从 JSON 文件中提取英文查询并保存到 TXT 文件。
    """
    if not os.path.exists(input_json_path):
        print(f"Error: Input file '{input_json_path}' not found.")
        return

    with open(input_json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {str(e)}")
            return

    if not isinstance(data, list):
        print("Error: JSON file top-level structure must be an array.")
        return

    results = []

    for item in data:
        if not isinstance(item, dict):
            continue

        query = item.get("query")
        if not isinstance(query, str):
            continue

        # 去掉首尾引号和空白
        query = query.strip().strip('"').strip("'")
        results.append(query)

    with open(output_txt_path, "w", encoding="utf-8") as f:
        for q in results:
            f.write(q + "\n")

def main(input_json, output_txt):
    """
    主函数：配置输入输出并执行提取。
    """
    extract_english_queries(input_json, output_txt)
    print(f"完成：已将结果保存至 {output_txt}")

if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    # 使用相对路径
    INPUT_JSON = 'query/query_old.json'
    OUTPUT_TXT = 'query_old.txt'
    
    main(INPUT_JSON, OUTPUT_TXT)
