import json
import hashlib


# 严格使用你提供的 MD5 计算方法
def get_url_hash(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def main(web_index_file, results_file, analysis_results_file, output_file):
    """主函数：规范化结构并执行最终数据合并。"""
    # 修改 final_fix 以接收参数
    def final_fix_with_params(web_idx, res_file, ana_res, out_file):
        # 1. 加载文件
        with open(web_idx, 'r', encoding='utf-8') as f:
            web_index_data = json.load(f)
        with open(res_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
        with open(ana_res, 'r', encoding='utf-8') as f:
            analysis_results_data = json.load(f)

        # 2. 建立 web_index 映射 (处理 .txt 后缀)
        # 强制将 key 转为小写，确保匹配稳定性
        web_map = {item['md5'].replace('.txt', '').lower(): item['category'] for item in web_index_data}

        # 3. 建立 results 索引 (query -> model -> citations)
        b_map = {}
        for entry in results_data:
            q = entry.get("query")
            if q:
                model_info = {}
                for res in entry.get("result", []):
                    m = res.get("model")
                    if m:
                        model_info[m] = res.get("citation", [])
                b_map[q] = model_info

        # 4. 遍历并匹配
        url_total = 0
        url_success = 0
        fail_samples = []

        for item_a in analysis_results_data:
            query_a = item_a.get("query")
            models_a = item_a.get("models", {})

            # 获取来自 results.json 的数据
            query_data_b = b_map.get(query_a, {})

            for model_name, model_content in models_a.items():
                citations = query_data_b.get(model_name, [])

                cat_list = []
                for url in citations:
                    url_total += 1
                    # 处理常见的 JSON 转义反斜杠问题 (将 \/ 还原为 /)
                    clean_url = url.replace('\\/', '/')

                    u_hash = get_url_hash(clean_url).lower()

                    category = web_map.get(u_hash)

                    if category:
                        cat_list.append(category)
                        url_success += 1
                    else:
                        cat_list.append("")
                        if len(fail_samples) < 3:  # 记录前几个失败案例供分析
                            fail_samples.append((clean_url, u_hash))

                model_content['citation_categories'] = cat_list

        # 5. 保存结果
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results_data, f, ensure_ascii=False, indent=2)

        # 6. 输出结果
        print("\n" + "=" * 40)
        print(f"URL 匹配统计：")
        print(f"总处理 URL 数: {url_total}")
        print(f"成功匹配类别数: {url_success}")
        if url_total > 0:
            print(f"匹配成功率: {(url_success / url_total) * 100:.2f}%")

        if url_success == 0 and url_total > 0:
            print("\n❌ 警告：所有 URL 均未匹配成功！")
            print("请对比以下计算出的 Hash 是否在 web_index.json 中出现过：")
            for f_url, f_hash in fail_samples:
                print(f"- URL: {f_url}")
                print(f"  Hash: {f_hash}")
        print("=" * 40)

    final_fix_with_params(web_index_file, results_file, analysis_results_file, output_file)


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    WEB_INDEX_FILE = 'web_index.json'
    RESULTS_FILE = 'results.json'
    ANALYSIS_RESULTS_FILE = 'analysis_results.json'
    OUTPUT_FILE = 'analysis_results_final.json'
    main(WEB_INDEX_FILE, RESULTS_FILE, ANALYSIS_RESULTS_FILE, OUTPUT_FILE)