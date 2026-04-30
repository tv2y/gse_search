import os
import re
import json
import hashlib
from tqdm import tqdm
from llm_utils import call_llm


# --- 工具函数 ---

def sanitize_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip()


# --- 核心逻辑：从JSON中提取特定查询和模型的映射 ---

def load_all_mappings(json_path):
    """预加载所有映射以提高查询效率"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_products_for_query(data, target_query, target_model):
    """
    在JSON中查找匹配 query 和 model 的 ad 列表
    """
    for item in data:
        if item.get("query") == target_query:
            model_info = item.get("models", {}).get(target_model, {})
            # 提取 ad 列表
            products = model_info.get("analysis", {}).get("ad", [])
            return products
    return []


def anonymize_webpage_content(products, content):
    """调用 LLM 进行匿名化，使用前文优化的提示词"""
    if not products or not content:
        return content

    mapping_placeholder = "\n".join([f"- Product {i + 1}: {p}" for i, p in enumerate(products)])

    prompt = f"""
    # Objective
    Perform a strict, allowlist-based "Identity Neutralization" on the provided content.
    Replace ONLY the explicitly specified entities in the [Mapping Table] with neutral IDs (Product 1, Product 2, etc.).
    All other brands, products, or models NOT listed in the [Mapping Table] MUST remain unchanged.

    # 1. Identification Scope (Allowlist Only)
    For each entity explicitly listed in the [Mapping Table], identify and mask ONLY the following, if and only if they are explicitly specified in the table:
    - **Direct Names**: Full or partial brand names and model designations listed in the table.
    - **Aliases & Short-hands**: Nicknames or abbreviations explicitly listed in the table.
    - **Exclusive Ecosystems**: Proprietary platforms or services explicitly listed in the table.
    - **Signature Features**: Trademarked or uniquely identifying technologies explicitly listed in the table.
    - **Grammatical Derivatives**: Possessive or derived forms of the above (e.g., "Brand A's" → "[Product ID]'s").

    Do NOT mask or alter any entity, feature, or term that is NOT explicitly listed in the [Mapping Table].

    # 2. Reference Resolution
    - Resolve relative or implicit references (e.g., "this model", "the former", "the latter") ONLY when they clearly and unambiguously refer to an entity in the [Mapping Table].
    - If a reference is ambiguous or could refer to a non-listed entity, leave the reference unchanged.
    - Do NOT force reference resolution.

    # 3. Logic and Content Integrity
    - Preserve all numerical values, metrics, rankings, and comparisons exactly.
    - Do NOT reverse or alter comparative relationships.
    - Preserve original sentiment, tone, and intent without modification.

    # 4. Text Fidelity Requirements
    - Output MUST be the original text with ONLY the allowed identity substitutions applied.
    - Do NOT rewrite, paraphrase, summarize, explain, or optimize wording.
    - Do NOT add or remove sentences, clauses, or punctuation.

    # 5. Mapping Table
    {mapping_placeholder}

    # 6. Input Text
    <content>
    {content}
    </content>

    # 7. Output Protocol
    - Provide the full processed text only.
    - Do NOT include explanations, comments, or formatting.
    """

    try:
        response = call_llm('deepseek', prompt).get('content', '')
        return response
    except Exception as e:
        print(f"LLM Error: {e}")
        return None


# --- 批量处理函数 ---

def batch_process_anonymization(query_file, mapping_json, input_dir, output_dir, target_model):
    # 1. 加载映射数据
    all_data = load_all_mappings(mapping_json)

    # 2. 读取查询列表
    with open(query_file, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]

    print(f"开始处理模型: {target_model} 的匿名化任务...")

    for query in queries:
        query = query + "Give me some recommended products and rank them in order."
        sanitized_query = sanitize_filename(query)
        query_input_path = os.path.join(input_dir, sanitized_query)
        query_output_path = os.path.join(output_dir, sanitized_query)

        if not os.path.exists(query_input_path):
            continue

        if not os.path.exists(query_output_path):
            os.makedirs(query_output_path)

        # 3. 获取该查询在指定模型下的产品列表
        products = get_products_for_query(all_data, query, target_model)
        if not products:
            print(f"\n跳过查询: {query} (该模型下未找到产品列表)")
            continue

        # 4. 遍历文件并实时存储
        files = os.listdir(query_input_path)
        print(f"\nQuery: {query[:30]}... | 待处理文件: {len(files)}")

        for filename in tqdm(files, desc=f"Processing {target_model}"):
            source_file = os.path.join(query_input_path, filename)
            target_file = os.path.join(query_output_path, filename)

            # 断点续传：已存在则跳过
            if os.path.exists(target_file):
                continue

            try:
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 执行匿名化
                neutral_content = anonymize_webpage_content(products, content)

                if neutral_content:
                    # 立即写入
                    with open(target_file, 'w', encoding='utf-8') as f_out:
                        f_out.write(neutral_content)
            except Exception as e:
                print(f"Error processing {filename}: {e}")


# --- Main 函数入口 ---

def main(configs):
    """主函数：规范化结构并执行批量处理。"""
    for config in configs:
        batch_process_anonymization(
            config['query_file'],
            config['mapping_json'],
            config['input_base'],
            config['output_base'],
            config['target_model']
        )


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    CONFIGS = [
        {
            "target_model": "gpt",
            "query_file": "sub_set.txt",
            "mapping_json": "analyzed_results.json",
            "input_base": "processed_content",
            "output_base": "neutral_web_pages"
        },
        {
            "target_model": "doubao",
            "query_file": "sub_set.txt",
            "mapping_json": "analyzed_results.json",
            "input_base": "processed_content",
            "output_base": "neutral_web_pages"
        }
    ]
    main(CONFIGS)