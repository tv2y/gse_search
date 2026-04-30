import json
import re
import hashlib
import os
from tqdm import tqdm
from llm_utils import call_llm


def get_url_hash(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def sanitize_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip()


def process_webpage_content(context):
    """
    输入原始网页文本，通过 LLM 提取清洗后的正文并分类。
    """

    # 1. 定义提示词模板 (整合了之前优化的逻辑)
    prompt = f"""
# Role
You are a Senior Data Engineer specializing in Web Content Extraction for Academic Research. You excel at distinguishing core semantic content from structural noise in raw HTML/Scraped text.

# Task
Analyze the provided scraped text to:
1. **Classify** the webpage into one of the predefined categories.
2. **Extract** the verbatim main body text related to products, recommendations, and shopping insights.

# Step-by-Step Logic (Follow this internally)
1. **Structural Scan**: Identify blocks of text that repeat across pages (menus, footers) and mark them for deletion.
2. **Intent Analysis**: Determine if the page's primary goal is to sell (E-commerce), review (Editorial), or share personal experience (UGC).
3. **Extraction**: Locate segments containing product names, specifications, pros/cons, or expert opinions.
4. **Verification**: Ensure every word in the output exists in the source text without modification.

# Classification Schema
- **[Official Website]**: Brand-owned pages. High authority on specs; marketing-heavy.
- **[Editorial/Review]**: Professional third-party analysis (e.g., "Best 10...", "X vs Y"). Look for author names and detailed testing methodologies.
- **[E-commerce Product Page]**: Direct shopping pages. Contains "Add to Cart", SKU options, and transactional data.
- **[Aggregator/Shopping Guide]**: Price comparison tables or lists of links with minimal original description.
- **[UGC/Forum]**: Community-driven content (Reddit, personal blogs). Informal tone, first-person perspective ("I bought...", "In my opinion...").

# Strict Extraction Rules
- **ZERO Paraphrasing**: Output must be 100% literal. If the source says "Battery: 5000mAh", do not write "It has a 5000mAh battery."
- **Noise Blacklist**: 
    * Navigation: Home, About Us, Cart, Menu icons.
    * Metatags: CSS classes, JavaScript snippets, or style definitions.
    * Promotion: "You may also like", "Subscribe to our newsletter", "Follow us on Twitter".
    * Legal: Copyright ©, Privacy Policy, Terms of Service.
- **Context Preservation**: Keep the relationship between a product name and its corresponding description. Use newlines to separate distinct product blocks.

# Output Format
Return ONLY a strictly valid JSON object. 
*CRITICAL*: Ensure all quotes (`"`) and newlines (`\n`) within the `cleaned_text` are properly escaped to prevent JSON parsing errors.

```json
{{
  "category": "[Insert Category Name]",
  "cleaned_text": "[The verbatim extracted text with JSON escaping]",
}}
```
# Input Document
<text>
{context}
</text>
"""

    try:
        raw_response_dict = call_llm('deepseek', prompt)
        # 兼容处理：有些 call_llm 直接返回字符串，有些返回字典
        raw_response = raw_response_dict.get('content', '') if isinstance(raw_response_dict,
                                                                          dict) else raw_response_dict

        if not raw_response:
            return {"error": "Empty response"}

        # 正则提取：尽量抓取最外层的大括号
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not json_match:
            return {"error": "No JSON braces found", "raw": raw_response[:100]}

        json_str = json_match.group(0)

        # 核心改进：预处理非法的控制字符
        # 很多网页文本抓取后带控制字符，会导致 json.loads 失败
        json_str = json_str.replace('\x00-\x1f', '')  # 移除控制字符

        try:
            data = json.loads(json_str)
            # 清洗 category 字段，去掉首尾的 [ 和 ]
            if "category" in data and isinstance(data["category"], str):
                data["category"] = data["category"].strip('[]')
            return data
        except json.JSONDecodeError:
            # 进阶尝试：修复常见的未转义引号（仅限简单情况）
            # 这种方法如果还是失败，建议在 Prompt 里极度强调 "Double Escape"
            return {"error": "JSON structure broken", "raw": raw_response[:200]}

    except Exception as e:
        return {"error": str(e)}


def batch_process(queries_file, input_base_dir, output_base_dir, index_json_path):
    # 1. 初始化索引
    processed_index = []
    processed_md5s = set()

    if os.path.exists(index_json_path):
        try:
            with open(index_json_path, 'r', encoding='utf-8') as f:
                processed_index = json.load(f)
                processed_md5s = {item['md5'] for item in processed_index}
        except:
            print("Warning: Index file corrupted, starting fresh.")

    # 2. 读取查询
    if not os.path.exists(queries_file):
        print(f"Error: {queries_file} not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]

    # 3. 循环处理
    for query in queries:
        query = query + "Give me some recommended products and rank them in order."
        clean_query = sanitize_filename(query)
        query_input_dir = os.path.join(input_base_dir, clean_query)
        query_output_dir = os.path.join(output_base_dir, clean_query)

        if not os.path.exists(query_input_dir):
            print(f"未找到查询目录: {query_input_dir}")
            continue

        if not os.path.exists(query_output_dir):
            os.makedirs(query_output_dir)

        files = os.listdir(query_input_dir)
        print(f"\nQuery: {query} | Files: {len(files)}")

        # 使用修正后的 tqdm
        for filename in tqdm(files, desc="Processing", leave=False):
            md5_val = filename

            if md5_val in processed_md5s:
                continue

            file_path = os.path.join(query_input_dir, filename)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_content = f.read()

                res = process_webpage_content(raw_content)

                if res and "category" in res:
                    # 立即存储清洗后的文本
                    with open(os.path.join(query_output_dir, md5_val), 'w', encoding='utf-8') as f_out:
                        f_out.write(res.get("cleaned_text", ""))

                    # 立即更新索引并写入磁盘
                    new_entry = {
                        "md5": md5_val,
                        "category": res.get("category"),
                        "query": query
                    }
                    processed_index.append(new_entry)
                    processed_md5s.add(md5_val)

                    with open(index_json_path, 'w', encoding='utf-8') as f_idx:
                        json.dump(processed_index, f_idx, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"\nSkip {md5_val} due to error: {e}")

def main(configs):
    """主函数：规范化结构并执行批量网页内容处理。"""
    for config in configs:
        batch_process(
            config['query_file'],
            config['input_dir'],
            config['output_dir'],
            config['index_file']
        )


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    CONFIGS = [
        {
            "input_dir": "crawled_content",
            "output_dir": "processed_content",
            "query_file": "ad_dataset.txt",
            "index_file": "web_index.json"
        },
        {
            "input_dir": "crawled_content",
            "output_dir": "processed_content",
            "query_file": "ad_dataset.txt",
            "index_file": "web_index.json"
        }
    ]
    main(CONFIGS)
