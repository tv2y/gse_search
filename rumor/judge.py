import os
import sys
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入现有的功能函数
from judge_content import judge_content as judge_content
from judge_reference import judge_url

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log.log')),
        logging.StreamHandler()
    ]
)


def judge_combined_results(input_path="query_results.json", output_path="judge_combined_results.json"):
    """
    同时处理内容和引用评估，将结果写入同一个文件

    Args:
        input_path: 输入文件路径，默认为"query_results.json"
        output_path: 输出文件路径，默认为"judge_combined_results.json"
    """

    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        logging.error(f"错误: 输入文件不存在: {input_path}")
        return

    # 加载测试结果
    with open(input_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    # 初始化结果列表
    results = []

    # 处理每个谣言元素
    for item_idx, item in enumerate(test_data):
        logging.info(f"处理第 {item_idx + 1}/{len(test_data)} 个谣言")

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
                    "content_score": -1,  # 初始化内容分数
                    "references": []
                }

                # 评估内容 - 直接调用现有的judge_content功能函数
                try:
                    content_judge_result = judge_content(result_item["rumor"], processed_result["content"])
                    processed_result["content_score"] = content_judge_result["score"]
                except Exception as e:
                    logging.error(f"评估内容时出错: {str(e)}")
                    processed_result["content_score"] = -1

                # 评估引用 - 直接调用现有的judge_single_url功能函数
                if "references" in result_entry and isinstance(result_entry["references"], list):
                    for url in result_entry["references"]:
                        try:
                            # 调用现有的功能函数评估URL
                            url_judge_result = judge_url(url, result_item["rumor"])

                            # 添加URL和得分的二元组
                            processed_result["references"].append([url_judge_result["url"], url_judge_result["score"]])

                            # 根据状态打印适当的消息
                            if url_judge_result["status"] == "success":
                                logging.info(f"  已处理URL: {url}, 得分: {url_judge_result['score']}")
                            elif url_judge_result["status"] == "no_cache":
                                logging.warning(f"  警告: 未找到URL的缓存句子: {url}")
                            elif url_judge_result["status"] == "error":
                                logging.error(
                                    f"  错误: 处理URL时发生异常: {url}, 错误: {url_judge_result.get('error_message', '未知错误')}")
                        except Exception as e:
                            # 额外的错误处理
                            processed_result["references"].append([url, -2])
                            logging.error(f"  严重错误: 调用judge_single_url函数时发生异常: {url}, 错误: {str(e)}")

                # 添加处理后的result到结果中
                result_item["result"].append(processed_result)

        # 将结果添加到结果列表
        results.append(result_item)

        # 每处理一个谣言就立即写入结果文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logging.info(f"  已保存处理结果到: {output_path}")

    logging.info(f"所有谣言处理完成，共处理 {len(results)} 个谣言")


def main(input_path, output_path):
    """主函数：规范化结构"""
    judge_combined_results(input_path=input_path, output_path=output_path)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_PATH = "./query_results_test.json"
    OUTPUT_PATH = "./judge_combined_results_test.json"
    main(INPUT_PATH, OUTPUT_PATH)