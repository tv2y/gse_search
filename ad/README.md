# Advertising (AD) 分析系统说明文档

该系统用于自动化分析搜索引擎/LLM结果中的广告成分、产品推荐及其引用来源。系统通过 `main.py` 串联起从查询到网页正文清洗分类的完整工作流。

## 目录结构与核心模块

### 1. 工作流核心脚本
- [main.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/main.py): **系统总入口**。负责按顺序调用各模块，协调中间产物的流转。
- [query.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/query.py): **查询模块**。读取待测查询列表，调用 LLM（如 GPT）获取包含引用的回答，生成原始结果文件。
- [catition_analysis.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/catition_analysis.py): **引用分析模块**。统计正文中各引用的出现频次，计算引用占比（ratio）。
- [ad_analysis.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/ad_analysis.py): **广告提取模块**。使用特定提示词从回答中提取显式品牌、产品名称及其关联的引用编号。
- [get_html.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/get_html.py): **网页爬取模块**。基于引用分析得到的有效链接（ratio > 0），通过 Jina AI 等接口抓取网页正文。
- [handel_html.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/handel_html.py): **正文处理模块**。对爬取的网页进行清洗，提取核心语义内容，并对网页类型进行分类。内部已集成类别名称清洗逻辑。

### 2. 独立/辅助工具
- [anonymize_web.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/anonymize_web.py): **匿名化工具**。根据产品映射表，将网页中的特定品牌/产品名替换为中性占位符（如 Product 1），用于消除模型先验偏见。
- [tmep_merge.py](file:///c:/Users/27227/PycharmProjects/ai_search/ad/tmep_merge.py): **数据合并工具**。将网页分类索引与分析结果进行最终合并。

## 工作流顺序

运行 `ad/main.py` 后，系统将根据配置的 `model_name`（默认为 `gpt`）自动执行以下步骤：

1. **Step 1**: 调用 `query.py` 生成 `results_{model}.json`。
2. **Step 2**: 调用 `catition_analysis.py` 生成 `citation_analysis_{model}.json`。
3. **Step 3**: 调用 `ad_analysis.py` 生成 `analyzed_results_{model}.json`。
4. **Step 4**: 调用 `get_html.py` 抓取有效引用网页，存入 `crawled_content/{model}/`。
5. **Step 5**: 调用 `handel_html.py` 清洗正文并分类，生成 `processed_content/{model}/` 及 `web_index_{model}.json` 索引。
6. **Step 6**: 调用 `result_merge.py` 将网页分类结果合并回最终的分析报告 `analysis_results_final_{model}.json`。

## 使用方法

### 运行完整流程
在项目根目录下执行：
```bash
python ad/main.py
```
默认输入文件为 `ad/ad_dataset.txt`（每行一个查询语句）。

### 产物说明
- **JSON 结果**: 包含 `results_{model}.json`（原始回答）、`citation_analysis_{model}.json`（引用统计）等。
- **网页内容**: 
  - `crawled_content/{model}/`: 原始抓取的文本。
  - `processed_content/{model}/`: LLM 清洗后的纯净正文。
- **索引文件**: `web_index_{model}.json` 记录了网页哈希值与其对应类别的映射。

## 注意事项
- **API 配置**: 请确保 `llm_utils.py` 已正确配置相应的 API Key。
- **缓存机制**: 网页抓取与处理模块具备基本的文件存在性检查，支持断点续传。
