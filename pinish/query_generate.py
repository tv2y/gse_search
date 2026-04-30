import sys
import os
import requests
import time
import random
import logging
import json
from bs4 import BeautifulSoup

# 导入所需模块
# 假设这些模块在 PYTHONPATH 中或当前目录下
try:
    from llm_utils import call_llm
    from utils import setup_logging, save_json_file, read_file_lines, generate_id
except ImportError:
    # 如果在 pinish 目录下运行，可能需要处理导入路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from llm_utils import call_llm
    from utils import setup_logging, save_json_file, read_file_lines, generate_id

def load_filter_words(file_path='filterword.txt'):
    """加载过滤词"""
    try:
        return read_file_lines(file_path)
    except Exception as e:
        logging.error(f"加载过滤词失败: {str(e)}")
        return []

def extract_feature_from_html(html_content):
    """从HTML源码中提取feature结构"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取标题
        title = soup.title.string.strip() if soup.title and soup.title.string else ''

        # 提取h1标题
        h1_tags = soup.find_all('h1')
        h1 = [h.get_text(strip=True) for h in h1_tags if h.get_text(strip=True)]

        # 提取h2标题
        h2_tags = soup.find_all('h2')
        h2 = [h.get_text(strip=True) for h in h2_tags if h.get_text(strip=True)]

        # 提取h3标题
        h3_tags = soup.find_all('h3')
        h3 = [h.get_text(strip=True) for h in h3_tags if h.get_text(strip=True)]

        # 提取meta元素
        meta_tags = []
        for meta in soup.find_all('meta'):
            meta_dict = {}
            if meta.get('name'):
                meta_dict['name'] = meta.get('name')
            if meta.get('property'):
                meta_dict['property'] = meta.get('property')
            if meta.get('content'):
                meta_dict['content'] = meta.get('content')
            if meta_dict:
                meta_tags.append(meta_dict)

        # 构建feature结构
        feature = {
            'title': title,
            'h1': h1,
            'h2': h2,
            'h3': h3,
            'meta': meta_tags
        }

        return feature
    except Exception as e:
        logging.error(f"提取feature时发生错误: {str(e)}")
        return {
            'title': '',
            'h1': [],
            'h2': [],
            'h3': [],
            'meta': []
        }

def check_filter_words(feature, filter_words):
    """检查feature是否包含过滤词"""
    # 组合所有需要检查的文本
    texts_to_check = []

    if feature.get('title'):
        texts_to_check.append(feature.get('title').lower())

    for h1 in feature.get('h1', []):
        texts_to_check.append(h1.lower())

    for h2 in feature.get('h2', []):
        texts_to_check.append(h2.lower())

    # 检查是否包含任何过滤词
    for word in filter_words:
        word_lower = word.lower()
        for text in texts_to_check:
            if word_lower in text:
                return True  # 包含过滤词

    return False  # 不包含过滤词

def generate_keywords_from_feature(feature, model_type='gpt-4o'):
    """根据feature生成关键词"""
    try:
        # 准备website_info数据
        website_info = {
            'title': feature.get('title', ''),
            'headings': {
                'h1': feature.get('h1', []),
                'h2': feature.get('h2', []),
                'h3': feature.get('h3', [])
            },
            'meta_tags': feature.get('meta', [])
        }

        # 使用提示词
        prompt = f"""Here is the website information:
Title: {website_info.get('title', '')}
Headings: {json.dumps(website_info.get('headings', {}), ensure_ascii=False)}
Meta Tags: {json.dumps(website_info.get('meta_tags', {}), ensure_ascii=False)}

Please generate five most relevant keywords based on the information above, separated by commas.And only return the keywords to me. Do not add any other statement."""

        # 调用LLM生成关键词
        response = call_llm(model_type, prompt)
        if not response or not response.get('content'):
            return []

        # 解析关键词
        keywords_str = response.get('content', '').strip()
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]

        # 确保返回5个关键词
        return keywords[:5]
    except Exception as e:
        logging.error(f"生成关键词时发生错误: {str(e)}")
        return []

def generate_query(keywords, model_type='gpt-4o'):
    """根据关键词生成查询语句"""
    try:
        keywords_str = ", ".join(keywords)
        # 使用提示词
        prompt = f"Create a natural search query using these five keywords: {keywords_str}. Make it sound like something people typically type into search engines in everyday life.And only return the query to me. Do not add any other statement."

        # 使用统一接口调用指定模型API
        response = call_llm(model_type, prompt)
        return response.get('content', '').strip() if response else ""
    except Exception as e:
        logging.error(f"生成查询语句时发生错误: {str(e)}")
        return ""

def save_html_source(html_content, file_path):
    """保存HTML源码到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"HTML源码已保存到: {file_path}")
        return True
    except Exception as e:
        logging.error(f"保存HTML源码时发生错误: {str(e)}")
        return False

def process_url(url, filter_keywords, existing_results, html_dir, model_type='gpt-4o'):
    """处理单个URL，提取信息并生成查询语句"""
    try:
        # 1. 生成唯一标识id
        url_id = generate_id(url)

        # 2. 检查是否已经处理过
        for result in existing_results:
            if result.get('id') == url_id:
                logging.info(f"URL {url} 已经处理过，跳过")
                return None

        logging.info(f"处理URL: {url}")

        # 3. 获取URL源码
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text

        # 4. 从URL的HTML源码中提取feature结构
        feature = extract_feature_from_html(html_content)

        # 5. 只有title和h1存在，并且没有命中过滤词，才继续后续操作
        if not feature.get('title') or not feature.get('h1'):
            logging.warning(f"URL {url} 的title或h1不存在，跳过")
            return None

        if check_filter_words(feature, filter_keywords):
            logging.warning(f"URL {url} 包含过滤词，跳过")
            return None

        # 6. 调用 api，根据feature生成关键词
        keywords = generate_keywords_from_feature(feature, model_type)
        if not keywords:
            logging.warning(f"无法为URL {url} 生成关键词，跳过")
            return None

        logging.info(f"生成的关键词: {keywords}")

        # 7. 调用 api，根据关键词生成查询语句
        query = generate_query(keywords, model_type)
        if not query:
            logging.warning(f"无法为URL {url} 生成查询语句，跳过")
            return None

        logging.info(f"生成的查询语句: {query}")

        # 8. 生成url对应的json结构
        result = {
            'type': 'query',
            'id': url_id,
            'url': url,
            'feature': feature,
            'keyword': keywords,
            'query': query
        }

        # 9. 将源码文件存入html_dir，文件名为id
        html_file_path = os.path.join(html_dir, f"{url_id}.html")
        save_html_source(html_content, html_file_path)

        return result
    except requests.RequestException as e:
        logging.error(f"获取URL {url} 内容时发生网络错误: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"处理URL {url} 时发生错误: {str(e)}")
        return None

def run_query_generator(model_type, input_file, output_file, filter_file, log_file, html_dir, max_new_results=120):
    """核心逻辑函数，读取URL列表，处理每个URL，并生成查询语句"""
    # 设置日志
    setup_logging(log_file)
    logging.info(f"开始执行查询生成任务")

    # 加载URL列表
    urls = read_file_lines(input_file)
    if not urls:
        logging.error(f"没有从 {input_file} 中加载到URL")
        return
    logging.info(f"成功加载 {len(urls)} 个URL")

    # 加载过滤词
    filter_keywords = load_filter_words(filter_file)
    logging.info(f"成功加载 {len(filter_keywords)} 个过滤词")

    # 检查是否已经有查询结果文件，如果有则加载
    existing_results = []
    processed_ids = set()  # 用于快速检查URL是否已处理
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
            logging.info(f"已加载现有的查询结果，共 {len(existing_results)} 条")
            # 收集已处理的ID
            processed_ids = {result.get('id') for result in existing_results}
        except Exception as e:
            logging.error(f"加载现有查询结果时发生错误: {str(e)}")
            existing_results = []
    else:
        logging.info(f"输出文件 {output_file} 不存在，将创建新文件")

    # 处理每个URL
    all_results = existing_results.copy()
    new_results_count = 0
    total_urls = len(urls)

    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue

        # 生成唯一标识id
        url_id = generate_id(url)

        # 检查是否已经处理过
        if url_id in processed_ids:
            logging.info(f"跳过URL {i + 1}/{total_urls}: {url} (ID: {url_id})，已处理过")
            continue

        result = process_url(url, filter_keywords, existing_results, html_dir, model_type)
        if result:
            all_results.append(result)
            processed_ids.add(url_id)  # 添加到已处理集合
            new_results_count += 1

            # 每处理一个URL就保存一次，避免数据丢失
            save_json_file(all_results, output_file)
            logging.info(f"已处理URL {i + 1}/{total_urls}: {url}，新增结果总数: {new_results_count}")

        if new_results_count >= max_new_results:
            break

        # 随机延迟，避免请求过于频繁
        time.sleep(random.uniform(1, 3))

    # 最后再保存一次完整结果
    if save_json_file(all_results, output_file):
        logging.info(
            f"查询生成任务完成，共处理 {total_urls} 个URL，新增 {new_results_count} 条查询，输出文件中共有 {len(all_results)} 条结果")
    else:
        logging.error("保存查询结果失败")

def main(model_type, input_file, output_file, filter_file, log_file, html_dir):
    """
    主函数：配置参数并运行生成器。
    """
    # 确保 API KEY 匿名化（此处不涉及直接的 API KEY，由 call_llm 处理）
    run_query_generator(
        model_type=model_type,
        input_file=input_file,
        output_file=output_file,
        filter_file=filter_file,
        log_file=log_file,
        html_dir=html_dir
    )

if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    # 使用相对路径
    MODEL_TYPE = "deepseek"
    INPUT_FILE = 'url.txt'
    OUTPUT_FILE = 'query/query.json'
    FILTER_FILE = 'filterword.txt'
    LOG_FILE = 'log.log'
    HTML_DIR = 'html_files'
    
    main(MODEL_TYPE, INPUT_FILE, OUTPUT_FILE, FILTER_FILE, LOG_FILE, HTML_DIR)
