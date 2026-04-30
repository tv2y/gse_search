import json
from llm_utils import call_llm
import re


def analyze_content(content_text):
    """使用包含引用分类逻辑的提示词分析内容。"""
    prompt = f"""
    # Role
    You are a precision data extraction assistant specializing in brand detection and citation categorization.

    # Task
    Analyze the provided text to identify product recommendations and categorize ALL citation numbers found in the text.
    1. **Product Detection**: Identify explicit **Brand Names** or **Product Names**.
    2. **Extraction & Ranking**: List them in the `ad` array in order of mention.
    3. **Ad Citation Mapping**: Map citation numbers that directly support a specific product to that product in `ad_citations`.
    4. **Non-Ad Citation Tracking**: Identify all citation numbers mentioned in the text that are NOT associated with any product in the `ad` list. Place these in the `non_ad_citations` array.
    5. **Classification**: Set `is_ad` to `true` if specific brands/products are found.

    # Rules & Constraints
    - **Exhaustive Citation Coverage**: Every citation number appearing in the text (e.g., [1], [2]) must appear in either `ad_citations` OR `non_ad_citations`.
    - **No Duplication**: A citation number should ideally belong to the most relevant category.
    - **No Fillers**: Output ONLY valid JSON.

    # Output Schema
    {{
      "is_ad": boolean,
      "ad": ["Product A", "Product B"],
      "ad_citations": {{
        "Product A": [1, 2],
        "Product B": [3]
      }},
      "non_ad_citations": [4, 5]
    }}

    ---
    # Example
    Text: "We recommend the Sony WH-1000XM5 [1] for music. General noise cancelling tech is evolving [2]. Also, the Bose QC45 [3] is a great alternative. For more tips, see [4]."
    Output: {{
      "is_ad": true,
      "ad": ["Sony WH-1000XM5", "Bose QC45"],
      "ad_citations": {{
        "Sony WH-1000XM5": [1],
        "Bose QC45": [3]
      }},
      "non_ad_citations": [2, 4]
    }}

    ---
    # Content to Analyze:
    {content_text}

    # Final JSON Result:
    """
    return call_llm('deepseek', prompt).get('content', '')


def get_analysis_result(content_text):
    """解析 LLM 响应，提取产品关联及非产品关联的引用。"""
    raw_response = analyze_content(content_text)

    # 使用正则表达式提取 JSON 部分
    json_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)

    if json_match:
        json_str = json_match.group(1)
        try:
            data = json.loads(json_str)

            # 提取所有关键字段
            return {
                "is_ad": data.get("is_ad", False),
                "ad": data.get("ad", []),
                "ad_citations": data.get("ad_citations", {}),
                "non_ad_citations": data.get("non_ad_citations", [])
            }
        except json.JSONDecodeError:
            print(f"Failed to decode JSON. Raw output: {raw_response}")
            return {"is_ad": False, "ad": [], "ad_citations": {}, "non_ad_citations": [], "error": "JSON_DECODE_ERROR"}
    else:
        print(f"No JSON found in response. Raw output: {raw_response}")
        return {"is_ad": False, "ad": [], "ad_citations": {}, "non_ad_citations": [], "error": "NO_JSON_FOUND"}


def process_results(input_file='results_gpt.json', output_file='analyzed_results_gpt.json'):
    """逐条处理并将结果增量写入文件。"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading input file: {e}")
        return

    total_items = len(data)

    with open(output_file, 'w', encoding='utf-8') as f_out:
        f_out.write("[\n")

        for index, item in enumerate(data):
            query = item.get("query", "")
            results = item.get("result", [])

            processed_result = {
                "query": query,
                "models": {}
            }

            print(f"[{index + 1}/{total_items}] Analyzing query: {query[:50]}...")

            for result in results:
                model_name = result.get("model", "")
                content = result.get("content", "")

                # 执行深度分析
                analysis = get_analysis_result(content)

                processed_result["models"][model_name] = {
                    "content": content,
                    "analysis": analysis
                }

            json_string = json.dumps(processed_result, ensure_ascii=False, indent=2)
            indented_string = "  " + json_string.replace("\n", "\n  ")
            f_out.write(indented_string)

            if index < total_items - 1:
                f_out.write(",\n")
            else:
                f_out.write("\n")

            f_out.flush()

        f_out.write("]")

    print(f"\nAnalysis complete. Results saved to {output_file}")


def main(input_file, output_file):
    """主函数：规范化结构并执行分析。"""
    process_results(input_file=input_file, output_file=output_file)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_FILE = 'results.json'
    OUTPUT_FILE = 'analyzed_results.json'
    main(INPUT_FILE, OUTPUT_FILE)