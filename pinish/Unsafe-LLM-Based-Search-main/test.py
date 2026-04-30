import os
import sys
import pandas as pd
import warnings
import time
from tqdm import tqdm

# 1. 环境配置
warnings.filterwarnings("ignore")
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    # 导入底层特征提取和预测所需的模型路径
    from src.utils import featureExtraction, _MODEL_PATH
    import pickle

    print("✅ [系统] 成功导入检测引擎组件")
except ImportError:
    print("❌ [错误] 找不到 src/utils.py，请确保在项目根目录运行")
    sys.exit(1)


# 2. URL 规范化函数
def _normalize_url(url_string):
    if not isinstance(url_string, str):
        return ""
    url = url_string.lower().strip()
    if not url:
        return ""
    # 补全协议头，确保 urlparse 能正常工作
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    return url.rstrip("/")


def batch_process(input_path, output_path):
    # 3. 加载数据
    if not os.path.exists(input_path):
        print(f"❌ 找不到输入文件: {input_path}")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_urls = [line.strip() for line in f if line.strip()]

    num_urls = len(raw_urls)
    print(f"📋 已加载 {num_urls} 个 URL，开始逐个顺序检测 (无并发)...")

    # 4. 加载模型 (只需加载一次)
    try:
        loaded_model = pickle.load(open(_MODEL_PATH, "rb"))
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return

    results_list = []
    start_time = time.time()

    # 5. 顺序循环检测
    for original_url in tqdm(raw_urls, desc="🔍 正在检测"):
        normalized_url = _normalize_url(original_url)

        try:
            # 直接调用单线程特征提取，不使用 utils.py 里的并发包装器
            # 这样如果某个 URL 慢，程序会在这里等待，而不会出现日志冲突
            features = featureExtraction(normalized_url)

            # 模型预测 (传入单条特征)
            # predict 期望输入是二维数组
            prediction = loaded_model.predict([features])[0]

            # 6. 标签转换逻辑 (根据要求：0=恶意, 1=安全)
            # 原始模型中：1 为恶意，0 为安全
            final_label = 0 if prediction == 1 else 1

        except Exception as e:
            # 如果某一行出错（如域名无法解析且没被 utils 捕获），标记为 -1
            print(f"\n⚠️ URL [{original_url}] 检测异常: {e}")
            final_label = -1

        results_list.append({
            'url': original_url,
            'label': final_label
        })

    # 7. 导出结果
    df = pd.DataFrame(results_list)
    df.to_csv(output_path, index=False, encoding='utf-8')

    duration = time.time() - start_time
    print("\n" + "=" * 40)
    print(f"✨ 检测任务完成！")
    print(f"⏱️  总耗时: {duration:.2f} 秒")
    print(f"🔴 恶意 (1): {sum(1 for x in results_list if x['label'] == 1)}")
    print(f"🟢 安全 (0): {sum(1 for x in results_list if x['label'] == 0)}")
    print(f"⚪ 失败 (-1): {sum(1 for x in results_list if x['label'] == -1)}")
    print(f"📁 结果保存至: {os.path.abspath(output_path)}")
    print("=" * 40)


if __name__ == "__main__":
    # 配置
    INPUT_FILE = "testdataset.txt"
    OUTPUT_FILE = "results.csv"
    batch_process(INPUT_FILE, OUTPUT_FILE)