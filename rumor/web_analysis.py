import re
import requests
import hashlib
import csv
import os
import time
import logging
import json
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_analysis")

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_cache")
URL_CACHE_FILE = os.path.join(CACHE_DIR, "url_cache.csv")
CONTENT_DIR = os.path.join(CACHE_DIR, "content")
SENTENCES_DIR = os.path.join(CACHE_DIR, "sentences")
FAILED_URL_FILE = os.path.join(CACHE_DIR, "failed_url.csv")


# 确保缓存目录和文件存在
def ensure_directories():
    """确保缓存目录结构和文件存在"""
    for dir_path in [CACHE_DIR, CONTENT_DIR, SENTENCES_DIR]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"创建目录: {dir_path}")

    # 确保URL缓存CSV文件存在并写入表头（如果不存在）
    if not os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['url', 'url_hash'])
            logger.info(f"创建URL缓存文件: {URL_CACHE_FILE}")

    # 确保失败URL记录文件存在并写入表头（如果不存在）
    if not os.path.exists(FAILED_URL_FILE):
        with open(FAILED_URL_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['url', 'url_hash'])
            logger.info(f"创建失败URL记录文件: {FAILED_URL_FILE}")


# 生成URL的哈希值
def get_url_hash(url):
    """生成URL的MD5哈希值"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


# 检查URL是否已缓存
def is_url_cached(url):
    """检查URL是否已在缓存中"""
    url_hash = get_url_hash(url)

    if not os.path.exists(URL_CACHE_FILE):
        return False, url_hash

    with open(URL_CACHE_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # 跳过表头
        next(reader, None)
        for row in reader:
            if len(row) >= 2 and row[1] == url_hash:
                return True, url_hash

    return False, url_hash


# 添加URL到缓存
def add_url_to_cache(url):
    """将URL及其哈希值添加到CSV缓存文件"""
    url_hash = get_url_hash(url)

    # 检查是否已存在
    with open(URL_CACHE_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1] == url_hash:
                return url_hash  # 已存在，直接返回

    # 添加新记录
    with open(URL_CACHE_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([url, url_hash])
        logger.info(f"URL已添加到缓存: {url}")

    return url_hash


# 记录失败的URL
def record_failed_url(url):
    """将失败的URL及其哈希值记录到CSV文件"""
    url_hash = get_url_hash(url)

    # 确保目录和文件存在
    ensure_directories()

    # 检查是否已存在
    if os.path.exists(FAILED_URL_FILE):
        with open(FAILED_URL_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1] == url_hash:
                    return  # 已存在，不重复记录

    # 添加新记录
    with open(FAILED_URL_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([url, url_hash])
        logger.info(f"失败URL已记录: {url}")


# 使用重试机制获取网页内容
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


# 智能英文分句
def smart_english_split(text: str):
    # 保护常见英文缩写（防止被误认为句号结尾）
    abbreviations = r"(Mr|Ms|Mrs|Dr|Prof|Sr|Jr|St|Mt|Inc|Ltd|Co|U\.S|U\.K|Ga|N\.Y|Calif|e\.g|i\.e|etc)\."
    text = re.sub(abbreviations, lambda m: m.group(0).replace('.', '<DOT>'), text)

    # 数字小数保护
    text = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", text)

    # 主断句逻辑：句号、问号、叹号后跟空格及首字母大写时视为新句
    pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(pattern, text)

    # 恢复替换符号
    sentences = [s.replace('<DOT>', '.') for s in sentences]

    # 清理与过滤
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
    return sentences


# 混合中英文分句
def hybrid_sentence_split(line: str):
    # 扩充分隔符集合，添加中文逗号、冒号等符号
    # 检测中文存在
    if re.search(r"[\u4e00-\u9fff]", line):
        # 添加更多中文标点符号作为分隔符：，:；""''“”‘’
        sentences = re.split(r'(?<=[。.!？?!，:；""\'\'“”‘’])\s*', line)
    else:
        sentences = smart_english_split(line)
    return [s.strip() for s in sentences if len(s.strip()) > 0]


# 按行处理文本的主函数
def process_text_by_line(text: str):
    lines = text.splitlines()
    all_sentences = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 不再简单地跳过没有结尾符号的行
        # 而是尝试从所有行中提取句子
        sentences = hybrid_sentence_split(line)
        
        for s in sentences:
            min_length = 10 if re.search(r'[。.!？?!，:；""\'\'“”‘’]$', s) else 15
            
            if len(s) >= min_length:
                all_sentences.append(s)
    
    return all_sentences


# 获取句子（带缓存）
def get_sentences(url):
    """获取URL的句子，优先从缓存读取"""
    ensure_directories()

    # 检查缓存
    is_cached, url_hash = is_url_cached(url)

    # 检查内容缓存文件
    content_file = os.path.join(CONTENT_DIR, f"{url_hash}.txt")
    sentences_file = os.path.join(SENTENCES_DIR, f"{url_hash}.json")

    if is_cached and os.path.exists(sentences_file):
        try:
            with open(sentences_file, 'r', encoding='utf-8') as f:
                sentences = json.load(f)
            logger.info(f"从缓存加载URL的句子: {url}")
            return sentences
        except Exception as e:
            logger.error(f"读取缓存句子文件失败: {e}")

    # 缓存未命中，获取内容
    content = get_content(url)
    if not content:
        # 内容获取失败，已在get_content中记录
        return []

    # 处理句子
    sentences = process_text_by_line(content)

    # 保存到缓存
    try:
        # 保存内容
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # 保存句子
        with open(sentences_file, 'w', encoding='utf-8') as f:
            json.dump(sentences, f, ensure_ascii=False, indent=2)

        # 添加到URL缓存
        add_url_to_cache(url)

        logger.info(f"已缓存URL的内容和句子: {url}")
    except Exception as e:
        logger.error(f"保存缓存失败: {e}")

    return sentences


# 处理JSON文件中的URL
def process_json_urls(json_file_path):
    """处理JSON文件中result.references数组中的URL"""
    if not os.path.exists(json_file_path):
        logger.error(f"JSON文件不存在: {json_file_path}")
        return

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查数据结构 - 适配test_results.json的实际结构
        if not isinstance(data, list):
            logger.error(f"JSON数据不是列表格式")
            return

        logger.info(f"找到 {len(data)} 个条目需要处理")

        # 处理列表中的每个条目
        for item_idx, item in enumerate(data):
            logger.info(f"处理第 {item_idx + 1}/{len(data)} 个条目")

            # 检查item是否为字典以及是否包含result字段
            if not isinstance(item, dict) or 'result' not in item:
                logger.warning(f"跳过无result字段的条目: {item_idx + 1}")
                continue

            # 获取result列表
            results = item['result']
            if not isinstance(results, list):
                logger.warning(f"跳过result不是列表格式的条目: {item_idx + 1}")
                continue

            # 处理每个result条目
            for result_idx, result_item in enumerate(results):
                # 检查references字段
                if not isinstance(result_item, dict) or 'references' not in result_item or not isinstance(
                        result_item['references'], list):
                    logger.warning(f"跳过无有效references字段的result条目: {result_idx + 1}")
                    continue

                # 处理每个URL
                references = result_item['references']
                for url_idx, url in enumerate(references):
                    try:
                        logger.info(f"处理URL {url_idx + 1}/{len(references)}: {url}")
                        sentences = get_sentences(url)
                        logger.info(f"URL处理完成，获取到 {len(sentences)} 个句子")
                    except Exception as e:
                        logger.error(f"处理URL失败: {url}, 错误: {e}")
                        # 记录处理失败的URL
                        record_failed_url(url)
                        continue
    except Exception as e:
        logger.error(f"处理JSON文件失败: {e}")


def main(input_file):
    """主函数：处理 JSON 文件中的 URL"""
    if os.path.exists(input_file):
        process_json_urls(input_file)
    else:
        logger.error(f"输入文件不存在: {input_file}")

    # 标记完成
    CHECK_FILE_PATH = r"flag.txt"
    with open(CHECK_FILE_PATH, "w") as f:
        f.write("done")


if __name__ == "__main__":
    # 在 main 函数中硬编码输入参数
    INPUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "query_results_perplexity.json")
    main(INPUT_JSON)