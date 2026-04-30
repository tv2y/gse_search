from sentence_transformers import util
from llm_utils import call_llm
import re
import time
import json
import os
import hashlib
from sentence_transformers import SentenceTransformer

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_cache")
SENTENCES_DIR = os.path.join(CACHE_DIR, "sentences")
Model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

def check_rumor_similarity(rumor, sentences):
    # 加载预训练模型
    model = Model

    # 生成嵌入向量
    rumor_emb = model.encode(rumor, convert_to_tensor=True)
    sent_embs = model.encode(sentences, convert_to_tensor=True)

    # 计算语义相似度
    cosine_scores = util.cos_sim(rumor_emb, sent_embs)[0]

    # 只输出相似度大于0.6的句子
    similar_sentences = []
    for i, score in enumerate(cosine_scores):
        if score > 0.6:
            similar_sentences.append((sentences[i], score.item()))

    return similar_sentences


def check_relevance(rumor, similar_sentences, max_retries=3, retry_delay=2):
    try:
        # 格式化提示词
        prompt = f"""
        You are a language model evaluation expert skilled in fact-checking and text analysis.
        Your task is to strictly evaluate the provided "rumor" and "webpage sentence set"
        to determine the relationship between the webpage content and the rumor.

        The evaluation MUST be performed in two logical stages:
        (1) Entity/Event Matching
        (2) Stance Assessment

        ## Scoring Rules

        0 → The webpage sentences clearly support, affirm, or spread the rumor content.

        1 → The webpage sentences are unrelated to the rumor.
        This includes:
        - Completely different topics.
        - Topic-level similarity but referring to a DIFFERENT real-world entity or event
          (e.g., a similar incident in another location or time, a different person with the same name,
           or a different but related event).

        2 → The webpage sentences clearly refer to the SAME entity or real-world event as the rumor,
        but their stance toward the rumor cannot be determined or is ambiguous.

        3 → The webpage sentences refer to the rumor, but the stance is unclear or cannot be determined.

        4 → The webpage sentences clearly deny, clarify, or refute the rumor content.

        ## Evaluation Constraints

        1. Entity / Event Matching Requirement  
        Before assigning any score other than 1, you MUST verify that the webpage sentences
        refer to the SAME entity or the SAME real-world event described in the rumor.

        - Topic similarity alone does NOT imply relevance.
        - If the webpage discusses a similar topic but a different instance
          (e.g., different location, different time, different person, or different event),
          the correct score is 1.
        - If you cannot confidently determine that the same entity or event is being discussed
          using ONLY the provided sentences, output 1.

        2. Evidence Scope  
        Only use the provided webpage sentence set for evaluation.
        Do NOT use external knowledge, assumptions, or background information.

        3. Stance Assessment  
        Only AFTER confirming the same entity/event, assess whether the webpage:
        - supports the rumor (0),
        - is ambiguous or indeterminate (2),
        - contradicts the rumor via authoritative sources (3),
        - or directly refutes or clarifies the rumor (4).

        4. Output Format  
        Your output MUST consist of a single digit from 0 to 4.
        Do NOT include any explanation, punctuation, or additional text.

        ## Input
        Rumor: {rumor}
        Webpage Sentences: {similar_sentences}
        """

        # 添加重试机制
        retries = 0
        while retries <= max_retries:
            try:
                # 调用DeepSeek模型
                result = call_llm('deepseek', prompt)

                # 获取返回内容
                content = result.get('content', '')

                if not content:
                    raise ValueError("DeepSeek API返回空内容")

                # 提取数字打分（只取第一个数字）
                match = re.search(r'\d', content)
                if match:
                    score = int(match.group())
                    # 确保分数在0-4范围内
                    if 0 <= score <= 4:
                        return score
                    else:
                        raise ValueError(f"返回的分数{score}不在0-4范围内")
                else:
                    raise ValueError(f"无法从返回内容中提取数字分数: {content}")
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    print(f"错误: 调用DeepSeek模型时发生异常且已达到最大重试次数: {str(e)}")
                    return -1  # 达到最大重试次数后返回无关
                else:
                    print(f"警告: 第{retries}次尝试失败: {str(e)}，{retry_delay}秒后重试...")
                    time.sleep(retry_delay)  # 等待一段时间后重试

        return -1  # 默认返回无关
    except Exception as e:
        print(f"错误: 发生未知异常: {str(e)}")
        return -1  # 发生异常时返回无关


def get_url_hash(url):
    """生成URL的MD5哈希值"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def load_sentences_from_cache(url):
    """从缓存中加载URL对应的句子"""
    url_hash = get_url_hash(url)
    sentences_file = os.path.join(SENTENCES_DIR, f"{url_hash}.json")

    if os.path.exists(sentences_file):
        try:
            with open(sentences_file, 'r', encoding='utf-8') as f:
                sentences = json.load(f)
            return sentences
        except Exception as e:
            print(f"警告: 读取缓存句子文件失败: {e}")
    return []


# 新增功能函数：只接受url，返回json结构
def judge_url(url, rumor):
    """
    评估单个URL与谣言的相关性

    Args:
        url: 要评估的URL
        rumor: 谣言内容（作为上下文）

    Returns:
        dict: 包含评估结果的JSON结构
    """
    try:
        # 从缓存加载句子
        sentences = load_sentences_from_cache(url)

        if sentences:
            # 获取相似度高的句子
            similar_sentences = check_rumor_similarity(rumor, sentences)

            # 提取句子文本
            similar_texts = [sent for sent, _ in similar_sentences]

            # 评估相关性
            relevance_score = check_relevance(rumor, similar_texts)

            # 返回JSON结构的结果
            return {
                "url": url,
                "score": relevance_score,
                "status": "success",
                "has_similar_sentences": len(similar_sentences) > 0
            }
        else:
            # 没有找到缓存的句子
            return {
                "url": url,
                "score": -1,
                "status": "no_cache",
                "has_similar_sentences": False
            }
    except Exception as e:
        # 出错时返回错误信息
        print(f"错误: 处理URL时发生异常: {url}, 错误: {str(e)}")
        return {
            "url": url,
            "score": -2,
            "status": "error",
            "error_message": str(e),
            "has_similar_sentences": False
        }

# 重构整体框架函数
def judge_results(input_path="query_results.json", output_path="judge_reference_results.json"):
    """
    处理测试结果文件，对每个谣言及其相关网页进行评估
    每处理完一个谣言就立即写入结果文件
    """

    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        return

    # 加载测试结果
    with open(input_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    # 初始化结果列表
    results = []

    # 处理每个谣言元素
    for item_idx, item in enumerate(test_data):
        print(f"处理第 {item_idx + 1}/{len(test_data)} 个谣言")

        # 创建结果条目
        result_item = {
            "rumor": item.get("rumor", ""),
            "chinese": item.get("chinese", ""),
            "result": []
        }

        # 处理result字段
        if "result" in item and isinstance(item["result"], list):
            for result_idx, result_entry in enumerate(item["result"]):
                # 创建处理后的result条目
                processed_result = {
                    "model": result_entry.get("model", ""),
                    "content": result_entry.get("content", ""),
                    "references": []
                }

                # 处理references
                if "references" in result_entry and isinstance(result_entry["references"], list):
                    for url in result_entry["references"]:
                        try:
                            # 调用新的功能函数评估URL
                            judge_result = judge_url(url, result_item["rumor"])

                            # 添加URL和得分的二元组
                            processed_result["references"].append([judge_result["url"], judge_result["score"]])

                            # 根据状态打印适当的消息
                            if judge_result["status"] == "success":
                                print(f"  已处理URL: {url}, 得分: {judge_result['score']}")
                            elif judge_result["status"] == "no_cache":
                                print(f"  警告: 未找到URL的缓存句子: {url}")
                            elif judge_result["status"] == "error":
                                print(f"  错误: 处理URL时发生异常: {url}, 错误: {judge_result.get('error_message', '未知错误')}")
                        except Exception as e:
                            # 额外的错误处理
                            processed_result["references"].append([url, -2])
                            print(f"  严重错误: 调用judge_single_url函数时发生异常: {url}, 错误: {str(e)}")

                # 添加处理后的result到结果中
                result_item["result"].append(processed_result)

        # 将结果添加到结果列表
        results.append(result_item)

        # 每处理一个谣言就立即写入结果文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"  已保存处理结果到: {output_path}")

    print(f"所有谣言处理完成，共处理 {len(results)} 个谣言")

def wait_for_file(file_path, check_interval=100):
    """
    每check_interval秒检查一次文件是否存在，直到文件存在为止
    """
    print(f"开始检查文件是否存在: {file_path}")
    while not os.path.exists(file_path):
        print(f"文件不存在，{check_interval}秒后再次检查...")
        time.sleep(check_interval)
    print(f"文件已找到: {file_path}")

def main(input_path, output_path, flag_path):
    """主函数：规范化结构"""
    wait_for_file(flag_path)
    judge_results(input_path=input_path, output_path=output_path)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_PATH = "./query_results_perplexity.json"
    OUTPUT_PATH = "./judge_reference_results_perplexity.json"
    CHECK_FILE_PATH = r"flag.txt"
    main(INPUT_PATH, OUTPUT_PATH, CHECK_FILE_PATH)