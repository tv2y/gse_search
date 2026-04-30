# Rumor Analysis 系统说明文档

该系统是一个自动化的谣言分析与事实核查工具流。它能够从 Excel 原始数据出发，经过 AI 搜索、网页内容分析、多维度判定、句子级精细化分析以及翻译相似度对比，最终输出完整的分析报告。

## 目录结构

- `main.py`: **系统总入口**，负责串联并驱动整个工作流。
- `query.py`: 初始查询模块。读取 Excel 原始数据，通过 LLM（如 Perplexity, YouChat）获取初始搜索结果和参考链接。
- `web_analysis.py`: 网页抓取与预处理模块。对 `query.py` 得到的 URL 进行抓取、分句并进行本地缓存。
- `judge.py`: 综合判定模块。对模型回复的内容质量和引用的相关性进行评分和判定。
- `sentence_divide.py`: 句子精细划分模块。将模型生成的长文本拆解为独立的句子，并关联对应的引用来源。
- `sentences_analysis.py`: 句子关系分析模块。对拆分出的每一个句子进行立场分类（支持、反对、怀疑、背景）。
- `translate_analysis.py`: 翻译相似度分析模块。独立分析原始 Excel 中英文谣言描述与中文翻译之间的语义一致性。
- `llm_utils.py`: LLM 调用工具类。封装了对不同大模型的调用逻辑。
- `dataset/`: 存放原始数据集（如 `webdataset.xlsx`）及相关的处理脚本。
- `results/`: 默认的结果输出目录。
- `cache/`: 默认的缓存目录，存储抓取的网页内容和中间查询结果。

## 工作流顺序

系统通过 `main.py` 按照以下顺序自动执行：

1.  **Step 1 (query.py)**: 读取原始 Excel -> 搜索引擎查询 -> 生成 `query_results.json`。
2.  **Step 2 (web_analysis.py)**: 抓取 `query_results.json` 中的 URL -> 分句并缓存到本地。
3.  **Step 3 (judge.py)**: 评估内容得分与引用相关性 -> 生成 `judge_combined_results.json`。
4.  **Step 4 (sentence_divide.py)**: 判定结果精细化分句 -> 生成 `processed_results.json`。
5.  **Step 5 (sentences_analysis.py)**: 对每个句子进行分类分析。
6.  **Step 6 (translate_analysis.py)**: 对原始输入进行中英翻译相似度分析并生成可视化图表。

## 使用方法

### 环境准备

确保已安装必要的 Python 依赖（pandas, openpyxl, sentence_transformers, matplotlib, requests 等）。

### 运行完整流程

在项目根目录下运行：

```bash
python rumor/main.py [输入Excel路径]
```

**示例：**

```bash
python rumor/main.py rumor/dataset/webdataset.xlsx
```

### 可选参数

- `--output_dir`: 指定结果保存目录（默认为 `rumor/results/`）。
- `--cache_dir`: 指定缓存保存目录（默认为 `rumor/cache/`）。

## 注意事项

- **API 配置**: 确保 `llm_utils.py` 中相关的 API Key 已正确配置。
- **数据格式**: 输入的 Excel 文件必须至少包含 `rumor` (英文描述) 和 `chinese` (中文翻译) 两列。
- **断点续行**: 系统在 `query.py` 和 `web_analysis.py` 阶段具有基本的缓存机制，如果运行中断，再次启动时会尝试跳过已处理的内容。
