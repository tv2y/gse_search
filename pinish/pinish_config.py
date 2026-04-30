import os

# Pinish 模块配置文件

def get_config():
    """
    返回所有配置项的字典。
    """
    # 输入输出文件路径配置 - 使用相对路径
    INPUT_PATHS = {
        'urls': 'url.txt',
        'queries': 'query.json',
        'answers': 'answer.json'
    }

    OUTPUT_PATHS = {
        'queries': 'query.json',
        'answers': 'answer.json',
        'results': 'result.json'
    }

    # 日志文件配置
    LOG_PATHS = {
        'query_generator': 'log.log',
        'query_tool': 'log.log',
        'judge_tool': 'log.log'
    }

    # 缓存文件配置
    CACHE_PATHS = {
        'phishing': 'phishing_cache.json'
    }

    # 其他配置文件
    CONFIG_PATHS = {
        'filter_words': 'filterword.txt'
    }

    # 模型配置
    DEFAULT_MODELS = {
        'query_generator': 'gpt-4o',
        'query_tool': 'perplexity',
        'judge_tool': 'gpt-4o'
    }

    # API调用配置
    API_CONFIG = {
        'timeout': 60,  # 请求超时时间（秒）
        'retry_count': 3,  # 请求失败重试次数
        'api_key': 'YOUR_API_KEY_HERE'  # 匿名化 API Key
    }

    return {
        'INPUT_PATHS': INPUT_PATHS,
        'OUTPUT_PATHS': OUTPUT_PATHS,
        'LOG_PATHS': LOG_PATHS,
        'CACHE_PATHS': CACHE_PATHS,
        'CONFIG_PATHS': CONFIG_PATHS,
        'DEFAULT_MODELS': DEFAULT_MODELS,
        'API_CONFIG': API_CONFIG
    }

# 直接暴露变量以便其他模块导入
config = get_config()
INPUT_PATHS = config['INPUT_PATHS']
OUTPUT_PATHS = config['OUTPUT_PATHS']
LOG_PATHS = config['LOG_PATHS']
CACHE_PATHS = config['CACHE_PATHS']
CONFIG_PATHS = config['CONFIG_PATHS']
DEFAULT_MODELS = config['DEFAULT_MODELS']
API_CONFIG = config['API_CONFIG']

def main():
    """
    主函数：展示当前配置。
    """
    current_config = get_config()
    print("Pinish Module Configuration:")
    for key, value in current_config.items():
        print(f"\n{key}:")
        if isinstance(value, dict):
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"  {value}")

if __name__ == "__main__":
    main()
