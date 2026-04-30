import json
import re
from llm_utils import call_llm  

# 处理每条结果的函数
def process_results(results, output_file_path):
    # 存储最终结果
    processed_results = []

    # 遍历每个谣言结果
    for idx, result in enumerate(results):
        print(f"Processing item {idx + 1}/{len(results)}...")

        for model_result in result['result']:
            # 适配数据结构：content 可能是字符串或列表
            content_raw = model_result.get('content', "")
            if isinstance(content_raw, list) and len(content_raw) > 0:
                content = content_raw[0]
            else:
                content = content_raw
            
            # 使用更新后的提示词
            prompt = f"""
            You are asked to read the following text and perform the following tasks:

            1. **Sentence Segmentation**: Split the provided text into individual sentences. Each sentence should be separated properly, ensuring completeness and accuracy.
            2. **Reference Extraction**: Extract the references associated with each sentence. Each sentence should have its corresponding reference numbers identified.
            3. **Output Format**: The output should be a JSON array, where each element contains the fields `sentence` and `references`.

            - `sentence`: The content of the individual sentence.
            - `references`: An array containing the reference numbers associated with the sentence.

            **IMPORTANT**: Do not add any additional explanation or information. The output must strictly follow the JSON format below, and should only include sentences and references:

            ```json
            [
              {{
                "sentence": "sentence content",
                "references": [reference_number1, reference_number2]
              }},
              {{
                "sentence": "next sentence content",
                "references": [reference_number]
              }}
            ]
            ```

            **Input Text**:
            {content}
            """

            # 调用 LLM 处理句子划分
            llm_response = call_llm("deepseek", prompt).get("content", "")

            # 使用正则表达式提取 JSON 部分
            json_match = re.search(r'\[\s*{.*}\s*\]', llm_response, re.DOTALL)
            if json_match:
                # 提取 JSON 字符串并解析
                json_data = json.loads(json_match.group(0))
                sentences_and_references = json_data  # 已经是解析后的 JSON 数据

                # 输出每个句子
                for sentence_data in sentences_and_references:
                    sentence = sentence_data["sentence"]
                    references = sentence_data["references"]
                    print(f"Processed sentence: {sentence} - References: {references}")
            else:
                print(f"Error: Could not extract JSON from the response: {llm_response}")

            # 存储这条结果
            processed_results.append({
                "rumor": result["rumor"],
                "model": model_result["model"],
                "processed_sentences": sentences_and_references
            })

            print(f"Finished processing model: {model_result['model']}")
        print(f"Finished processing item {idx + 1}/{len(results)}.\n")

    # 将结果保存为 JSON 文件
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        json.dump(processed_results, output_file, ensure_ascii=False, indent=4)
    print(f"Processing complete. Results saved to '{output_file_path}'.")

def main(input_file_path, output_file_path):
    """主函数：规范化结构"""
    with open(input_file_path, 'r', encoding='utf-8') as file:
        final_results = json.load(file)
    process_results(final_results, output_file_path)

if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_FILE = 'final_results.json'
    OUTPUT_FILE = 'processed_results.json'
    main(INPUT_FILE, OUTPUT_FILE)
