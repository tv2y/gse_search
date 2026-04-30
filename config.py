"""
项目配置文件
包含所有模块共用的配置参数，以变量形式定义便于管理和修改
"""

# 日志配置
# 日志文件路径
LOG_FILE_PATH = 'log.log'
# 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = 'INFO'
# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# LLM模型配置
# OpenAI GPT-4o配置
GPT4O_API_KEY = ''  # 可以留空，会从环境变量或文件中读取
GPT4O_API_URL = 'https://svip.xty.app/v1'
GPT4O_MODEL_NAME = 'gpt-4o-mini'

# Perplexity模型配置 - 与websearch.py保持一致
PERPLEXITY_API_KEY = ''
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'
PERPLEXITY_MODEL_NAME = 'sonar'  # 更新为websearch.py中使用的模型名称

# Exa模型配置 - 与websearch.py保持一致
EXA_API_KEY = ''
EXA_API_URL = 'https://api.exa.ai'
EXA_MODEL_NAME = 'exa'  # 更新为websearch.py中使用的模型名称

# You.com模型配置 - 与websearch.py保持一致
YOUCOM_API_KEY = ''
YOUCOM_API_URL = 'https://api.you.com/v1/agents/runs'
YOUCOM_MODEL_NAME = 'youchat'

# Tavily模型配置 - 与websearch.py保持一致

TAVILY_API_KEY = ''
TAVILY_API_URL = 'https://api.tavily.com/search'
TAVILY_MODEL_NAME = 'tavily'

# Deepseek模型配置
DEEPSEEK_API_KEY = ''
DEEPSEEK_API_URL = 'https://api.siliconflow.cn/v1'
DEEPSEEK_MODEL_NAME = 'Pro/deepseek-ai/DeepSeek-V3'

# 钓鱼检测配置
# 钓鱼检测使用的模型名称
PHISHING_DETECTION_MODEL = 'gpt-4o'
# 默认超时时间（秒）
DEFAULT_TIMEOUT = 30
# 重试次数
RETRY_COUNT = 3
# 重试间隔（秒）
RETRY_INTERVAL = 2

# URL处理配置
# 短链接展开最大深度
MAX_SHORTENED_URL_EXPAND_DEPTH = 5
# 用户代理
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'