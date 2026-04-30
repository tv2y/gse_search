import json
import os
import hashlib
import requests
import time
import logging
import re
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')


# --- 您提供的现有函数 ---

def get_url_hash(url):
    """生成URL的MD5哈希值"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除或替换非法字符，并限制长度。"""
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip()


def record_failed_url(url, log_file="failed_urls.txt"):
    """记录失败的URL"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{url}\n")


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
            response.raise_for_status()
            return response.text
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
    record_failed_url(url)
    return ""


# --- 核心逻辑 ---

def process_and_crawl(analysis_file, results_file, base_output_dir="crawled_content"):
    # 1. 加载数据
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    with open(results_file, 'r', encoding='utf-8') as f:
        results_data = json.load(f)

    # 将不同格式的分析数据统一为 { query: { model_name: [ratio...] } }
    def build_ratio_map(data):
        ratio_map = {}
        for entry in data:
            q = entry.get('query')
            if not q:
                continue
            models_ratio = {}
            # 新格式：{"result":[{"model":..,"ratio":[...]}]}
            if isinstance(entry.get('result'), list):
                for r in entry['result']:
                    m = r.get('model')
                    if m is None:
                        continue
                    models_ratio[m] = r.get('ratio', [])
            # 旧格式：{"models":{"model_name":{"ratio":[...]}}}
            elif isinstance(entry.get('models'), dict):
                for m, info in entry['models'].items():
                    if not isinstance(info, dict):
                        continue
                    models_ratio[m] = info.get('ratio', [])
            if models_ratio:
                ratio_map[q] = models_ratio
        return ratio_map

    ratio_map = build_ratio_map(analysis_data)

    # 将 results_data 转换为映射表，方便通过 query 快速查找
    # 结构: { query: { model_name: [url1, url2...] } }
    results_map = {}
    for item in results_data:
        q = item['query']
        results_map[q] = {res['model']: res.get('citation', []) for res in item.get('result', [])}

    # 预筛选任务清单
    tasks = []
    for query, models_ratios in ratio_map.items():
        if query not in results_map:
            continue

        for model_name, ratios in models_ratios.items():
            urls = results_map[query].get(model_name, [])

            # 只有 ratio > 0 的才加入任务
            for i, ratio in enumerate(ratios):
                if ratio > 0 and i < len(urls):
                    tasks.append({
                        'query': query,
                        'model': model_name,
                        'url': urls[i],
                        'hash': get_url_hash(urls[i])
                    })

    total_tasks = len(tasks)
    if total_tasks == 0:
        print("未发现需要爬取的任务（所有ratio可能均为0或数据不匹配）。")
        return

    print(f"任务初始化完成，共需爬取 {total_tasks} 个有效 URL。")

    # 2. 执行爬取
    crawl_cache = {}  # 缓存记录 {url_hash: local_path}
    processed_count = 0
    current_query = ""

    for task in tasks:
        processed_count += 1

        # 统计当前 Query 剩余
        if task['query'] != current_query:
            current_query = task['query']
            query_remaining = len([t for t in tasks[processed_count - 1:] if t['query'] == current_query])
            print(f"\n[处理查询] {current_query[:60]}...")
        else:
            query_remaining -= 1

        # 准备目录
        model_path = os.path.join(base_output_dir, sanitize_filename(task['model']))
        query_path = os.path.join(model_path, sanitize_filename(task['query']))
        os.makedirs(query_path, exist_ok=True)

        target_file = os.path.join(query_path, f"{task['hash']}.txt")
        total_remaining = total_tasks - processed_count

        print(
            f"  进度: [{processed_count}/{total_tasks}] | 模型: {task['model']} | 本组剩: {query_remaining} | 总剩: {total_remaining}")

        # 3. 缓存检查与爬取
        if task['hash'] in crawl_cache:
            shutil.copy(crawl_cache[task['hash']], target_file)
        else:
            content = get_content(task['url'])
            if content:
                with open(target_file, 'w', encoding='utf-8') as f_out:
                    f_out.write(content)
                crawl_cache[task['hash']] = target_file

    print(f"\n全部任务完成！共处理唯一网页: {len(crawl_cache)} 个。")


def main(analysis_file, results_file, base_output_dir):
    """主函数：规范化结构并执行网页内容爬取。"""
    process_and_crawl(analysis_file, results_file, base_output_dir=base_output_dir)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    ANALYSIS_FILE = 'analysis_results.json'
    RESULTS_FILE = 'results.json'
    BASE_OUTPUT_DIR = 'crawled_content'
    main(ANALYSIS_FILE, RESULTS_FILE, BASE_OUTPUT_DIR)
