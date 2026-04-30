import json
import os
import sys
from datetime import datetime

import openpyxl
from llm_utils import call_llm


def verify_rumors(input_path, output_path, cache_path, search_models=None):
    """
    验证Excel文件中的谣言内容，并将结果存储为JSON数组格式
    """
    # 设置默认搜索模型
    if search_models is None:
        search_models = ['perplexity']

    # 加载缓存
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            print(f"警告：缓存文件 {cache_path} 格式无效，将创建新缓存")

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 确保缓存目录存在
    cache_dir = os.path.dirname(cache_path)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 检查输出文件是否已存在并包含有效JSON数组
    output_exists = os.path.exists(output_path)
    existing_results = []

    if output_exists:
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
                if not isinstance(existing_results, list):
                    print(f"警告：输出文件 {output_path} 不是有效的JSON数组，将重新创建")
                    existing_results = []
        except json.JSONDecodeError:
            print(f"警告：输出文件 {output_path} 格式无效，将重新创建")
            existing_results = []

    try:
        # 读取Excel文件
        workbook = openpyxl.load_workbook(input_path)
        sheet = workbook.active

        # 获取表头行
        header_row = sheet[1]
        headers = [cell.value for cell in header_row]

        # 打印实际读取的列名，用于调试
        print(f"Excel文件实际包含的列名: {headers}")

        # 检查是否有'rumor'列
        if not headers or 'rumor' not in headers:
            print("错误：Excel文件中没有找到'rumor'列")
            # 尝试使用第一列作为谣言内容
            if headers:
                print(f"将使用第一列 '{headers[0]}' 作为谣言内容")
                rumor_column_index = 0
            else:
                print("无法识别Excel文件的列名，程序将退出")
                return
        else:
            rumor_column_index = headers.index('rumor')

        # 检查是否有'chinese'列
        if not headers or 'chinese' not in headers:
            print("警告：Excel文件中没有找到'chinese'列")
            chinese_column_index = None
        else:
            chinese_column_index = headers.index('chinese')

        total_rows = 0
        processed_rows = 0

        # 从第二行开始遍历数据行（第一行是表头）
        for row in sheet.iter_rows(min_row=2, values_only=True):
            try:
                total_rows += 1

                # 获取谣言内容
                if rumor_column_index >= len(row) or row[rumor_column_index] is None:
                    print(f"警告：行 {total_rows} 中没有找到谣言数据")
                    continue

                rumor = str(row[rumor_column_index]).strip()
                if not rumor:
                    continue  # 跳过空谣言

                # 获取中文翻译
                chinese = ""
                if chinese_column_index is not None and chinese_column_index < len(row) and row[
                    chinese_column_index] is not None:
                    chinese = str(row[chinese_column_index]).strip()

                # 构建提示词
                prompt = f'It is said that "{rumor}",is it true or false?'

                # 检查缓存是否存在
                cache_key = f"{rumor}"
                result = []

                if cache_key in cache:
                    print(f"命中缓存: {rumor}")
                    # 首先获取完整的缓存结果
                    full_cached_result = cache[cache_key]
                    # 根据search_models过滤结果，只保留本次运行需要的模型
                    result = [item for item in full_cached_result if item.get('model') in search_models]
                    
                    # 检查是否包含所有请求模型的结果
                    cached_models = {item['model'] for item in result}
                    missing_models = [model for model in search_models if model not in cached_models]
                    
                    if missing_models:
                        print(f"缓存中缺少以下模型的结果: {', '.join(missing_models)}")
                        for model in missing_models:
                            try:
                                # 调用llm_utils中的call_llm函数
                                response = call_llm(model, prompt)

                                # 构建结果对象
                                model_result = {
                                    "model": model,
                                    "content": response.get("content", ""),
                                    "references": response.get("references", [])
                                }
                                result.append(model_result)
                                print(f"补充获取模型 {model} 的结果")
                            except Exception as e:
                                print(f"调用模型 {model} 时出错: {str(e)}")
                                # 添加错误信息到结果
                                result.append({
                                    "model": model,
                                    "content": f"调用失败: {str(e)}",
                                    "references": []
                                })
                        
                        # 更新缓存 - 这里我们需要保留完整的缓存结果
                        # 先复制原始缓存结果
                        updated_cache_result = [item for item in full_cached_result if item.get('model') not in search_models]
                        # 添加新的或更新的结果
                        updated_cache_result.extend(result)
                        # 更新缓存
                        cache[cache_key] = updated_cache_result
                        with open(cache_path, 'w', encoding='utf-8') as cache_file:
                            json.dump(cache, cache_file, ensure_ascii=False, indent=2)
                    
                    # 检查缓存中是否有content为null的结果，如果有则重新获取并更新缓存
                    # 这里需要只检查search_models中存在的模型
                    null_content_models = []
                    for model in search_models:
                        # 查找当前模型在result中的项
                        model_items = [item for item in result if item.get('model') == model]
                        if model_items:
                            # 检查content是否为null
                            if model_items[0].get('content') is None:
                                null_content_models.append(model_items[0])
                    
                    if null_content_models:
                        print(f"缓存中以下模型的content为null: {', '.join([item['model'] for item in null_content_models])}")
                        for item in null_content_models:
                            model = item['model']
                            try:
                                # 调用llm_utils中的call_llm函数
                                response = call_llm(model, prompt)

                                # 更新结果对象
                                item['content'] = response.get("content", "")
                                item['references'] = response.get("references", [])
                                print(f"重新获取模型 {model} 的结果")
                            except Exception as e:
                                print(f"调用模型 {model} 时出错: {str(e)}")
                                # 更新错误信息
                                item['content'] = f"调用失败: {str(e)}"
                                item['references'] = []
                        
                        # 更新缓存 - 保留完整的缓存结果
                        updated_cache_result = [item for item in full_cached_result if item.get('model') not in search_models]
                        updated_cache_result.extend(result)
                        cache[cache_key] = updated_cache_result
                        with open(cache_path, 'w', encoding='utf-8') as cache_file:
                            json.dump(cache, cache_file, ensure_ascii=False, indent=2)
                else:
                    # 调用搜索AI
                    print(f"处理: {rumor}")
                    for model in search_models:
                        try:
                            # 调用llm_utils中的call_llm函数
                            response = call_llm(model, prompt)

                            # 构建结果对象
                            model_result = {
                                "model": model,
                                "content": response.get("content", ""),
                                "references": response.get("references", [])
                            }
                            result.append(model_result)

                        except Exception as e:
                            print(f"调用模型 {model} 时出错: {str(e)}")
                            # 添加错误信息到结果
                            result.append({
                                "model": model,
                                "content": f"调用失败: {str(e)}",
                                "references": []
                            })

                    # 存储到缓存
                    cache[cache_key] = result
                    # 保存缓存
                    with open(cache_path, 'w', encoding='utf-8') as cache_file:
                        json.dump(cache, cache_file, ensure_ascii=False, indent=2)

                # 构建输出结果
                output_data = {
                    "rumor": rumor,
                    "chinese": chinese,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }

                # 添加到现有结果中
                existing_results.append(output_data)
                processed_rows += 1

                # 每处理一行就写入一次完整的JSON数组
                with open(output_path, 'w', encoding='utf-8') as out_file:
                    json.dump(existing_results, out_file, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"处理行时出错: {str(e)}")
                continue

        print(f"谣言验证完成！共处理 {total_rows} 行，成功处理 {processed_rows} 行，结果已保存到 {output_path}")

    except FileNotFoundError:
        print(f"错误：找不到输入文件 {input_path}")
    except Exception as e:
        print(f"处理Excel文件时出错: {str(e)}")
        # 打印详细的异常信息用于调试
        import traceback
        traceback.print_exc()

def main(input_path, output_path, cache_path, search_models):
    """主函数：规范化结构"""
    # 调用验证函数
    verify_rumors(
        input_path=input_path,
        output_path=output_path,
        cache_path=cache_path,
        search_models=search_models
    )


if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    INPUT_PATH = r'\rumor\dataset\webdataset.xlsx'
    OUTPUT_PATH = r'\rumor\query_results_perplexity.json'
    CACHE_PATH = r'\rumor\query_cache_temp1.json'
    SEARCH_MODELS = ['perplexity', 'youchat']
    main(INPUT_PATH, OUTPUT_PATH, CACHE_PATH, SEARCH_MODELS)