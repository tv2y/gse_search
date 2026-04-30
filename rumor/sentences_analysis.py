import json
from llm_utils import call_llm

def test_llm_response(results):
    for idx, result in enumerate(results):
        print(f"Testing rumor {idx + 1}/{len(results)}...")

        rumor = result['rumor']

        sentence_group = result['processed_sentences']

        sentence_group_text = "\n".join([f"{i + 1}. {sentence['sentence']}" for i, sentence in enumerate(sentence_group)])

        prompt = f"""
        You are given a **fact statement** and a set of sentences. Your task is to classify each sentence based on its relationship to the fact statement.

        ### Classification Categories:
        1. **Supports the Fact**: The sentence directly supports or affirms the fact statement.
        2. **Opposes the Fact**: The sentence denies, refutes, or contradicts the fact statement.
        3. **Doubtful**: The sentence expresses doubt, uncertainty, or a lack of conviction about the fact statement.
        4. **Background/Introductory**: The sentence provides background information, context, or scientific information related to the fact, but does not directly support or oppose it.

        ### Task Requirements:
        - Carefully read the fact statement and each sentence.
        - Use the fact statement to evaluate whether each sentence supports, opposes, expresses doubt, or provides background information.
        - Consider the meaning and context of the fact statement and classify the sentences accordingly.

        ### Output Format:
        For each sentence, provide the following output:
        - **sentence**: The content of the sentence.
        - **category**: The classification of the sentence (Supports the Fact, Opposes the Fact, Doubtful, Background/Introductory).

        **Input Format**:
        - **Fact Statement**: {rumor}
        - **Sentences**: {sentence_group_text}
        """

        llm_response = call_llm("deepseek", prompt).get("content", "")

        print(f"LLM Response for Model {result['model']}:\n{llm_response}\n")

def main(input_file):
    """主函数：规范化结构"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    test_llm_response(data)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入参数
    INPUT_FILE = 'processed_results.json'
    main(INPUT_FILE)
