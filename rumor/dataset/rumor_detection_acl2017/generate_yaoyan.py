# -*- coding: utf-8 -*-
import csv
import sys
import os

# 配置系统标准输出和错误输出为UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到Python路径，确保能正确导入llm_utils模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from llm_utils import call_llm


# 创建一个安全打印函数来处理可能的编码问题
def safe_print(text):
    """
    安全打印文本，处理可能的编码问题
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # 处理无法编码的字符
        print(text.encode('utf-8', 'replace').decode('utf-8'))


def process_csv_file(input_csv_file, output_csv_file):
    """
    处理CSV文件，根据label列的值，对content列进行处理，每处理一行就写入一次

    Args:
        input_csv_file (str): 输入CSV文件路径
        output_csv_file (str): 输出CSV文件路径（用于保存处理结果）
    """
    try:
        # 打开输入CSV文件进行读取，明确使用UTF-8编码
        with open(input_csv_file, 'r', encoding='utf-8', newline='') as infile:
            # 创建CSV读取器
            reader = csv.DictReader(infile)

            # 获取原始CSV文件的字段名，并添加处理结果的字段名
            fieldnames = reader.fieldnames.copy() if reader.fieldnames else []
            if 'processed_content' not in fieldnames:
                fieldnames.append('processed_content')

            # 打开输出CSV文件进行写入，明确使用UTF-8编码
            # 使用 newline='' 以避免额外的空行
            with open(output_csv_file, 'w', encoding='utf-8', newline='') as outfile:
                # 创建CSV写入器
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                # 写入表头
                writer.writeheader()

                j = 0

                # 处理每一行数据
                for i, row in enumerate(reader, 1):
                    # 为每一行创建一个新的字典，避免修改原始行数据
                    processed_row = row.copy()
                    if j > 100:
                        break

                    # 检查label列是否为'true'（注意大小写和字符串/布尔值类型）
                    if 'label' in processed_row and processed_row['label'].strip().lower() == 'false':
                        # 对于label为true的行，获取content列
                        if 'content' in processed_row:
                            content = processed_row['content']
                            j += 1

                            try:
                                # 调用处理content的函数
                                processed_content = summarize_twitter_post(content)
                                # 添加处理结果到当前行
                                processed_row['processed_content'] = processed_content

                                # 每处理一行就立即写入一次
                                writer.writerow(processed_row)
                                # 刷新缓冲区，确保数据立即写入文件
                                outfile.flush()

                                safe_print(f"第{i}行处理完成")
                                safe_print(f"原始内容: {content}")
                                safe_print(f"处理结果: {processed_content}")
                            except Exception as e:
                                safe_print(f"第{i}行处理内容时出错: {str(e)}")
                                processed_row['processed_content'] = f"处理错误: {str(e)}"
                                writer.writerow(processed_row)
                                outfile.flush()
                        else:
                            safe_print(f"警告: 第{i}行中缺少content列")
                            processed_row['processed_content'] = "缺少content列"
                            writer.writerow(processed_row)
                            outfile.flush()

        print(f"CSV文件处理完成: {input_csv_file}")
        print(f"处理结果已保存至: {output_csv_file}")
    except UnicodeEncodeError as e:
        safe_print(f"编码错误: {str(e)}")
        safe_print("请确保所有文件操作都使用UTF-8编码。")
    except Exception as e:
        safe_print(f"处理CSV文件时出错: {str(e)}")


# 以下代码保持不变
def summarize_twitter_post(content):
    """
    将Twitter帖子转换为简洁、客观、权威的句子

    Args:
        content (str): Twitter帖子内容

    Returns:
        str: 处理后的句子或"can not get useful event"
    """
    # 构建提示词
    prompt = f"""
Try to convert the following Twitter post into a concise, objective, and authoritative sentence that could be used in a news report or encyclopedia entry. Please note:
1. Any URLs in the post have been replaced with "URL".
2. Focus on extracting the event or claim from the Twitter post, and ensure it sounds plausible and formal; use wording commonly found in official news reports or encyclopedia entries.
3. You must not alter the intended meaning of the original Twitter post. If the original content is vague, do your best to clarify the event or factual elements while accurately preserving the core idea.
4. The output should only contain the rewritten "rumor fact" sentence—do not include any additional content.
5. For posts that cannot be effectively summarized, output "can not get useful event".
Twitter post:{content}
"""

    try:
        # 调用call_llm函数，使用deepseek模型
        result = call_llm('deepseek', prompt)

        # 获取并返回结果中的content部分
        if result and 'content' in result and result['content']:
            return result['content']
        else:
            # 如果没有获取到有效内容，返回默认值
            return "can not get useful event"
    except Exception as e:
        # 处理调用过程中可能出现的错误
        safe_print(f"调用语言模型时出错: {str(e)}")
        return "api error"


# 如果需要直接运行此脚本进行测试，可以取消下面的注释

def main(input_file, output_file):
    """主函数：规范化结构"""
    process_csv_file(input_file, output_file)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_FILE = r"/rumor/rumor_detection_acl2017/twitter16/matched_data.csv"
    OUTPUT_FILE = r"/rumor/rumor_detection_acl2017/twitter16/processed_data.csv"
    main(INPUT_FILE, OUTPUT_FILE)