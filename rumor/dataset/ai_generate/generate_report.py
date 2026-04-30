import os
import json
import logging
from llm_utils import call_llm
from config import LOG_FILE_PATH, LOG_LEVEL, LOG_FORMAT


# 设置日志配置
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE_PATH,
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT
    )


# 初始化日志
setup_logging()


# 核心函数1：根据主题生成新闻报道内容
def generate_news_report(theme):
    """
    入参为一个字符串，即新闻报道的主题
    出参为一个字符串，即新闻报道的内容
    目的：根据输入的新闻报告主题，构建提示词，使用llm接口，调用llm生成新闻报道的内容
    """
    try:
        prompt = f"""
Please write a detailed and formal news report based on the following theme. The report must include specific information about the time, location, main people involved, the course of events, and the outcome. You should invent additional details as needed, ensuring overall logical consistency and complete information.

**News Theme**
{theme}

**Instructions**
- The final output must be the body text of a news article (do NOT just list elements).
- Do NOT include any explanations or remarks.
- The news format must be as follows:
[News Title]
[Specific Time]
[Specific Location]
[News Report Body]

**Output Format**
Please strictly follow all the above requirements when generating the news report.Do NOT output anything except the news content itself."""

        # 调用LLM生成新闻报道，使用gpt-4o模型
        result = call_llm('deepseek', prompt)

        if result['content']:
            return result['content']
        else:
            logging.error(f"生成新闻报道失败，主题：{theme}")
            return ""
    except Exception as e:
        logging.error(f"生成新闻报道时发生错误：{str(e)}")
        return ""


# 核心函数2：从报道中提取事实
def extract_facts(content):
    """
    入参为新闻报道的内容
    出参为一个数组，即从报道中提取的事实
    """
    try:
        prompt = f"""
Please extract from the given news text all complete, informative factual statements.

**News Text**
{content}

**Instructions**

- Each statement must contain four elements: **time, location, subject, event** forming a standalone senence.
- Exactly reproduce the original wording where possible; do not introduce information not present in the source.
- If any required element (time, location, subject, or event) is missing, use context and pronouns only to resolve into a single clear, self-contained sentence.
- Each statement must not exceed 50 words.
- When some elements are missing, they may be reasonably inferred — for example, one should restore explicit time, location, or person when phrases such as “that,” “this,” or personal pronouns are incomplete.

**Output Format**
Each line should be a single independent factual statement.Do NOT output anything except the factual statements."""

        # 调用LLM提取事实，使用gpt-4o模型
        result = call_llm('deepseek', prompt)

        if result['content']:
            # 将结果按行分割，去除空行
            facts = [line.strip() for line in result['content'].split('\n') if line.strip()]
            return facts
        else:
            logging.error(f"提取事实失败")
            return []
    except Exception as e:
        logging.error(f"提取事实时发生错误：{str(e)}")
        return []


# 整体函数：处理主题并生成最终的json结果
def process_theme(theme):
    """
    入参为新闻报道的主题
    出参为一个json结构
    """
    # 生成新闻报道
    content = generate_news_report(theme)
    if not content:
        return None

    # 提取事实
    facts = extract_facts(content)

    # 构建结果json
    result = {
        "theme": theme,
        "content": content,
        "facts": facts
    }

    return result


# 主函数：读取主题文件并处理所有主题
def main(themes_file, output_json_file, reports_dir):
    """
    读取一个txt文件，文件中每一行是一个新闻报道的主题
    循环处理每一行，调用核心函数1生成新闻报道的内容
    将内容存储到一个文件中，文件名与主题相同，后缀为.txt
    调用核心函数2，从报道的内容中提取事实
    将结果封装为json结构，写入到一个文件中，该文件内为一个json数组，每个元素为一个json对象。每处理完一行就写入一次。
    """
    try:
        # 确保报道保存目录存在
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        # 检查主题文件是否存在
        if not os.path.exists(themes_file):
            logging.error(f"主题文件不存在：{themes_file}")
            # 创建一个示例主题文件
            with open(themes_file, 'w', encoding='utf-8') as f:
                f.write("城市新图书馆开幕庆典\n新能源汽车展览会召开\n科技公司发布新产品\n")
            logging.info(f"已创建示例主题文件：{themes_file}")
            return

        # 读取主题文件
        with open(themes_file, 'r', encoding='utf-8') as f:
            themes = [line.strip() for line in f.readlines() if line.strip()]

        if not themes:
            logging.error(f"主题文件为空：{themes_file}")
            return

        # 加载已有的结果（如果存在）
        existing_results = []
        if os.path.exists(output_json_file):
            try:
                with open(output_json_file, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
            except json.JSONDecodeError:
                existing_results = []

        # 处理每个主题
        for theme in themes:
            # 检查该主题是否已经处理过
            if any(item["theme"] == theme for item in existing_results):
                logging.info(f"主题已处理过，跳过：{theme}")
                continue

            logging.info(f"开始处理主题：{theme}")

            # 处理主题
            result = process_theme(theme)
            if not result:
                logging.error(f"处理主题失败：{theme}")
                continue

            # 保存新闻报道到单独的文件
            # 生成安全的文件名
            safe_filename = "".join(c for c in theme if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')[:50]  # 限制文件名长度
            report_file = os.path.join(reports_dir, f"{safe_filename}.txt")

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(result["content"])

            logging.info(f"新闻报道已保存：{report_file}")

            # 将结果添加到现有结果中
            existing_results.append(result)

            # 写入结果到json文件
            with open(output_json_file, 'w', encoding='utf-8') as f:
                json.dump(existing_results, f, ensure_ascii=False, indent=2)

            logging.info(f"结果已写入：{output_json_file}")

    except Exception as e:
        logging.error(f"主程序执行出错：{str(e)}")


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    THEMES_FILE = os.path.join(CURRENT_DIR, "news_themes.txt")
    OUTPUT_JSON_FILE = os.path.join(CURRENT_DIR, "generated_news_results.json")
    REPORTS_DIR = os.path.join(CURRENT_DIR, "news_reports")
    main(THEMES_FILE, OUTPUT_JSON_FILE, REPORTS_DIR)
