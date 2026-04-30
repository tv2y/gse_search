from mutation_test import get_query_contents
from tree_attack import run_optimization_framework

if __name__ == '__main__':
    # 1. 配置
    QUERIES_FILE = 'low_score_queries.txt'
    MAX_ROUNDS = 5

    # 硬编码的目标得分：Middle 34% 阈值 (CF, CCR, AA, SF, KIC, SC, AD)
    # 对应的值为: 0.322, 0.09, 0.96, 0.96, 0.84, 0.87, 0.82
    TARGET_SCORES = [0.322, 0.09, 0.96, 0.96, 0.84, 0.87, 0.82]

    print("--- 批量攻击测试开始 ---")
    print(f"硬编码目标得分 (Middle 34% 阈值): {TARGET_SCORES}")

    # 2. 读取查询列表
    try:
        with open(QUERIES_FILE, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误：查询文件 {QUERIES_FILE} 未找到。请确保已运行第一步脚本生成此文件。")
        exit()

    total_queries = len(queries)
    if total_queries == 0:
        print("查询列表为空，无需执行测试。")
        exit()

    print(f"共发现 {total_queries} 个查询进行测试 (最大轮次: {MAX_ROUNDS})。")

    for i, query in enumerate(queries):
        print(f"\n[{i + 1}/{total_queries}] 正在处理查询: {query}")

        # 3a. 获取内容数据 (调用外部函数)
        init_content, other_content, _ = get_query_contents(query)
        if not init_content or not other_content:
            print(f"警告：无法为查询 '{query}' 加载内容数据，已跳过。")
            continue

        # 3b. 调用外部函数进行攻击测试
        test_result = run_optimization_framework(
            query=query,
            initial_content=init_content,
            other_docs=other_content,
            max_rounds=MAX_ROUNDS,
            target_scores=TARGET_SCORES  # 使用硬编码的 TARGET_SCORES
        )

    print("\n--- 批量攻击测试完成 ---")