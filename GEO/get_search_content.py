from tavily import TavilyClient
import json
import os
import hashlib
import requests
import time
import logging
from llm_utils import call_llm
import re

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tavily_client = TavilyClient(api_key="")


def get_content(url, max_retries=2, retry_interval=2):
    """使用重试机制获取网页内容"""
    final_url = 'https://r.jina.ai/' + url
    headers = {
        "X-Md-Link-Style": "discarded",
        "X-Retain-Images": "none"
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(final_url, headers=headers, timeout=30)
            response.raise_for_status()  # 检查响应状态
            logger.info(f"成功获取URL内容: {url}")
            return response.text
        except Exception as e:
            logger.warning(f"获取URL内容失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"{retry_interval}秒后重试...")
                time.sleep(retry_interval)

    logger.error(f"达到最大重试次数，获取URL内容失败: {url}")
    # 记录失败的URL
    record_failed_url(url)
    return ""  # 返回空字符串表示失败


def record_failed_url(url):
    """记录失败的URL到文件中"""
    with open("failed_urls.txt", "a", encoding="utf-8") as f:
        f.write(url + "\n")


def sanitize_filename(filename):
    """清理文件名，移除或替换非法字符"""
    # 替换Windows和Linux中不允许的字符
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # 限制文件名长度（避免路径过长）
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip()


# 函数1：输入 query，调用tavily search api并返回一个url数组
def get_urls_from_query(query):
    """
    输入 query，调用tavily search api并返回一个url数组，
    数组中的元素是api返回结果的"result"字段中每个元素的"url"字段。
    """
    try:
        response = tavily_client.search(query, include_raw_content=True)
        results = response.get("results", [])
        urls = [item.get("url") for item in results if item.get("url")]
        return urls
    except Exception as e:
        print(f"Error searching for query '{query}': {e}")
        return []


# 函数3：输入 query和url, 获取网页正文并保存到指定位置
def save_content_from_query_and_url(query, url, index):
    """
    输入 query和url, 调用函数get_content(url），获取url对应的网页正文，
    在content文件夹下的以query为名的文件夹下，创建以数字(1-5)命名的txt文件并存储content的内容。
    注意，函数最开始进行判断，如果query对应的文件夹已经存在，则直接跳过
    """
    # 清理query作为文件夹名
    folder_name = sanitize_filename(query)

    # 创建文件夹路径
    folder_path = os.path.join("lima_content", folder_name)

    # 如果文件夹已存在且文件数量达到5个，则跳过
    if os.path.exists(folder_path) and len(os.listdir(folder_path)) >= 5:
        return False

    # 获取网页内容
    content = get_content(url)
    if not content:
        return False

    os.makedirs(folder_path, exist_ok=True)

    # 使用数字作为文件名 (1.txt, 2.txt, ..., 5.txt)
    file_path = os.path.join(folder_path, f"{index}.txt")

    # 检查是否已存在相同编号的文件
    if os.path.exists(file_path):
        return False

    # 保存内容到文件
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Content saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save content to {file_path}: {e}")
        return False


def clean(content):
    """使用DeepSeek模型清洗内容，只保留主要文本"""
    prompt = f"""
You are a helpful research assistant. You are tasked with get the main information from all text content on a scraped web page.
Only keep the main useful information about the web theme.
Return ONLY the main text whitout any other thing in you answer.
Here is the original document:
{content}
"""
    response = call_llm('deepseek', prompt)
    clean_content = response.get('content', '')
    return clean_content


def save_clean_content(query, url, index):
    """
    输入 query和url, 从content文件夹中读取对应的内容文件，
    在clean_content文件夹下的以query为名的文件夹下，创建以数字(1-5)命名的txt文件并存储清洗后的内容。
    """
    # 清理query作为文件夹名
    folder_name = sanitize_filename(query)

    # 创建文件夹路径
    folder_path = os.path.join("lima_clean_content", folder_name)
    content_folder_path = os.path.join("lima_content", folder_name)

    # 使用相同的数字作为文件名
    file_path = os.path.join(folder_path, f"{index}.txt")
    content_path = os.path.join(content_folder_path, f"{index}.txt")

    # 检查原始内容文件是否存在
    if not os.path.exists(content_path):
        logger.error(f"Content file does not exist: {content_path}")
        return False

    # 从文件读取内容
    try:
        with open(content_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read content from {content_path}: {e}")
        return False

    clean_content = clean(content)
    if not clean_content:
        return False

    os.makedirs(folder_path, exist_ok=True)

    # 保存清洗后的内容到文件
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_content)
        logger.info(f"Clean content saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save clean content to {file_path}: {e}")
        return False


# main函数
def main(input_file):
    """
    从指定文件（每一行是一个query）,处理每一行内容，
    对于每一个query，使用函数1获取url数组，对于数组中的每个url，
    使用函数3获取url对应的网页正文并存储到指定文件中。
    """
    # 确保content文件夹存在
    os.makedirs("lima_content", exist_ok=True)
    os.makedirs("lima_clean_content", exist_ok=True)

    # 读取查询文件并逐行处理
    with open(input_file, 'r', encoding='utf-8') as f:
        queries = f.readlines()

    for query in queries:
        query = query.strip()
        if not query:  # 跳过空行
            continue

        print(f"Processing query: {query}")

        # 清理query作为文件夹名
        folder_name = sanitize_filename(query)
        folder_path = os.path.join("lima_content", folder_name)

        # 检查query对应的文件夹是否已存在且已有5个文件，如果存在则跳过整个query
        if os.path.exists(folder_path):
            print(f"Query folder already exists, skipping query: {query}")
            continue

        # 使用函数1获取url数组
        urls = get_urls_from_query(query)
        print(f"Found {len(urls)} URLs for query: {query}")

        # 限制最多处理5个URL
        urls = urls[:5]

        # 对于数组中的每个url，使用函数3获取内容并保存
        for i, url in enumerate(urls, 1):
            try:
                success = save_content_from_query_and_url(query, url, i)
                if success:
                    print(f"Successfully processed URL {i}: {url}")
                else:
                    print(f"Failed to process URL {i}: {url}")
            except Exception as e:
                print(f"Error processing URL '{url}' for query '{query}': {e}")

        # 处理清洗内容
        for i, url in enumerate(urls, 1):
            try:
                success = save_clean_content(query, url, i)
                if success:
                    print(f"Successfully clean_content {i}: {url}")
                else:
                    print(f"Failed to clean_content {i}: {url}")
            except Exception as e:
                print(f"Error clean_content '{url}' for query '{query}': {e}")


if __name__ == "__main__":
    # 处理测试文件
    main("./dataset/test.txt")