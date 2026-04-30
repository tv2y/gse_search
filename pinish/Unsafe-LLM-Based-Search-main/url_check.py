import os
import sys
import warnings
import time
import json

# 1. 环境配置
warnings.filterwarnings("ignore")
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.utils import featureExtraction, _MODEL_PATH
    import pickle
    print("✅ [系统] 成功导入检测引擎组件")
except ImportError:
    print("❌ [错误] 找不到 src/utils.py，请确保在项目根目录运行")
    sys.exit(1)


def _normalize_url(url_string):
    if not isinstance(url_string, str):
        return ""
    url = url_string.lower().strip()
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    return url.rstrip("/")


def load_json_array(input_path):
    if not os.path.exists(input_path):
        print(f"❌ 找不到输入文件: {input_path}")
        return None
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("❌ 输入 JSON 顶层必须是数组(list)")
        return None
    return data


def save_json(output_path, data):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def batch_process_json(
    input_path,
    output_path,
    references_field="references",
    output_field="references_labeled",
    replace_inplace=False
):
    data = load_json_array(input_path)
    if data is None:
        return

    # 统计 URL 总数
    all_urls = []
    for item in data:
        refs = item.get(references_field, [])
        if isinstance(refs, list):
            for u in refs:
                if isinstance(u, str) and u.strip():
                    all_urls.append(u)

    total_urls = len(all_urls)

    print(f"📋 已加载样本数: {len(data)}")
    print(f"🔗 references 总 URL 数: {total_urls}")
    print("🚀 开始逐个顺序检测（无进度条）...\n")

    # 只加载一次模型
    try:
        loaded_model = pickle.load(open(_MODEL_PATH, "rb"))
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return

    start_time = time.time()

    url_counter = 0

    for item in data:
        refs = item.get(references_field, [])
        if not isinstance(refs, list):
            continue

        labeled_list = []

        for original_url in refs:
            if not isinstance(original_url, str) or not original_url.strip():
                labeled_list.append({"url": original_url, "label": -1})
                continue

            url_counter += 1
            normalized_url = _normalize_url(original_url)

            print(
                f"[{url_counter}/{total_urls}] 开始处理 URL: {original_url}"
            )

            try:
                features = featureExtraction(normalized_url)
                prediction = loaded_model.predict([features])[0]
                # 约定：1=恶意 → label 0；0=安全 → label 1
                final_label = 0 if prediction == 1 else 1
            except Exception as e:
                print(f"    ⚠️ 处理异常: {e}")
                final_label = -1

            print(
                f"[{url_counter}/{total_urls}] 完成处理 URL: {original_url}  label: {final_label}\n"
            )

            labeled_list.append(
                {"url": original_url, "label": final_label}
            )

        if replace_inplace:
            item[references_field] = labeled_list
        else:
            item[output_field] = labeled_list

    save_json(output_path, data)

    duration = time.time() - start_time
    print("=" * 50)
    print("✨ 检测任务完成")
    print(f"⏱️ 总耗时: {duration:.2f} 秒")
    print(f"📁 输出文件: {os.path.abspath(output_path)}")
    print("=" * 50)


if __name__ == "__main__":
    INPUT_JSON = r"C:\Users\27227\PycharmProjects\ai_search\pinish\answer\answer_perplexity.json"
    OUTPUT_JSON = r"C:\Users\27227\PycharmProjects\ai_search\pinish\answer\answer_perplexity_labeled.json"

    batch_process_json(
        input_path=INPUT_JSON,
        output_path=OUTPUT_JSON,
        references_field="references",
        output_field="references_labeled",
        replace_inplace=False
    )
