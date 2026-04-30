import requests
import sys
import os
import logging
import httpx
from openai import OpenAI

# 导入配置文件中的参数
from config import (
    LOG_FILE_PATH, LOG_LEVEL, LOG_FORMAT,
    GPT4O_API_KEY, GPT4O_API_URL, GPT4O_MODEL_NAME,
    PERPLEXITY_API_KEY, PERPLEXITY_API_URL, PERPLEXITY_MODEL_NAME,
    EXA_API_KEY, EXA_API_URL, EXA_MODEL_NAME,
    YOUCOM_API_KEY, YOUCOM_API_URL, YOUCOM_MODEL_NAME,
    TAVILY_API_KEY, TAVILY_API_URL, TAVILY_MODEL_NAME,
    DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL_NAME,
    DEFAULT_TIMEOUT, RETRY_COUNT, RETRY_INTERVAL
)


# 设置日志配置
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE_PATH,
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT
    )


# 初始化日志
setup_logging()


class ProviderConfig:
    def __init__(self, name, url, headers, build_payload, parse_response):
        self.name = name
        self.url = url
        self.headers = headers
        self.build_payload = build_payload
        self.parse_response = parse_response


class LLMUtils:
    @staticmethod
    def get_api_key(model_type=None):
        """从文件或环境变量中获取API密钥"""
        try:
            # 优先从配置文件中获取预定义的API密钥
            if model_type == 'gpt-4o' and GPT4O_API_KEY and GPT4O_API_KEY != 'your-api-key-here':
                return GPT4O_API_KEY
            elif model_type == 'perplexity' and PERPLEXITY_API_KEY and PERPLEXITY_API_KEY != 'your-api-key-here':
                return PERPLEXITY_API_KEY
            elif model_type == 'exa' and EXA_API_KEY and EXA_API_KEY != 'your-api-key-here':
                return EXA_API_KEY
            elif model_type == 'youchat' and YOUCOM_API_KEY and YOUCOM_API_KEY != 'your-api-key-here':
                return YOUCOM_API_KEY
            elif model_type == 'tavily' and TAVILY_API_KEY and TAVILY_API_KEY != 'your-api-key-here':
                return TAVILY_API_KEY
            elif model_type == 'deepseek' and DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != 'your-api-key-here':
                return DEEPSEEK_API_KEY

            logging.error(f"未找到模型 {model_type} 的API密钥")
            raise ValueError(f"未找到模型 {model_type} 的API密钥")

        except Exception as e:
            logging.error(f"读取API密钥时发生错误: {str(e)}")
            raise

    @staticmethod
    def call_gpt4o_api(prompt, api_key, model=None):
        """调用GPT-4o API获取回答"""
        try:
            # 使用配置文件中的模型名称，如果没有提供则使用默认值
            model_name = model or GPT4O_MODEL_NAME

            client = OpenAI(
                base_url=GPT4O_API_URL,
                api_key=api_key,
                http_client=httpx.Client(
                    base_url=GPT4O_API_URL,
                    follow_redirects=True,
                ),
            )

            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )

            # 返回包含content和references的字典，对于gpt-4o，references使用空数组
            return {
                "content": completion.choices[0].message.content,
                "references": []
            }
        except Exception as e:
            logging.error(f"调用GPT-4o API失败: {str(e)}")
            return {
                "content": None,
                "references": []
            }
    
    @staticmethod
    def call_deepseek_api(prompt, api_key, model=None):
        """调用DeepSeek API获取回答"""
        try:
            # 使用配置文件中的模型名称，如果没有提供则使用默认值
            model_name = model or DEEPSEEK_MODEL_NAME

            client = OpenAI(
                base_url=DEEPSEEK_API_URL,
                api_key=api_key
            )

            # 使用stream=True参数，与deepseek_api_test.py保持一致
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )

            # 收集流式响应中的内容
            full_content = []
            for chunk in response:
                if chunk.choices:
                    if chunk.choices[0].delta.content:
                        full_content.append(chunk.choices[0].delta.content)
                    if chunk.choices[0].delta.reasoning_content:
                        full_content.append(chunk.choices[0].delta.reasoning_content)

            # 组合完整的内容
            combined_content = ''.join(full_content)

            # 返回包含content和references的字典，对于deepseek，references使用空数组
            return {
                "content": combined_content,
                "references": []
            }
        except Exception as e:
            logging.error(f"调用DeepSeek API失败: {str(e)}")
            return {
                "content": None,
                "references": []
            }

    @staticmethod
    def call_provider(config, query, system_prompt=None, extra=None):
        """调用指定的搜索引擎API，实现与websearch.py一致"""
        extra = extra or {}
        payload = config.build_payload(query, system_prompt, extra)

        try:
            if config.name == "exa":
                client = OpenAI(base_url=config.url, api_key=config.headers["Authorization"].split(" ")[1])
                completion = client.chat.completions.create(**payload)
                return config.parse_response(completion)
            else:
                r = requests.post(config.url, headers=config.headers, json=payload, timeout=DEFAULT_TIMEOUT)
                r.raise_for_status()
                return config.parse_response(r.json())
        except Exception as e:
            logging.error(f"调用 {config.name} API失败: {str(e)}")
            return {
                "content": None,
                "references": []
            }

    @staticmethod
    def parse_markdown_response(r):
        """解析Markdown格式的响应内容，实现与websearch.py一致"""
        try:
            import re
            content = r.choices[0].message.content
            references = re.findall(r'\[([^\]]+)\]\((https?://.*?)\)', content)
            references_list = list(dict.fromkeys([url for _, url in references]))

            def repl(m):
                return m.group(1)

            content_simplified = re.sub(r'\[([^\]]+)\]\((https?://.*?)\)', repl, content)

            return {
                "content": content_simplified,
                "references": references_list
            }
        except Exception as e:
            logging.error(f"解析Markdown响应失败: {str(e)}")
            return {
                "content": str(r),
                "references": []
            }

    @staticmethod
    def get_provider_config(name, api_key):
        """获取指定搜索引擎的配置，使用config.py中的参数"""
        try:
            if name.lower() == 'perplexity':
                return ProviderConfig(
                    name="perplexity",
                    url=PERPLEXITY_API_URL,  # 使用config中的URL
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                        ""
                    },
                    build_payload=lambda query, system_prompt, extra: {
                        "model": PERPLEXITY_MODEL_NAME,  # 使用config中的模型名称
                        "messages": ([{"role": "system", "content": system_prompt}] if system_prompt else []) +
                                    [{"role": "user", "content": query}],
                        "search_domain": "perplexity",
                        "max_results": 7
                    },
                    parse_response=lambda r: {
                        "content": r["choices"][0]["message"]["content"],
                        "references": r.get("citations", [])
                    }
                )
            elif name.lower() == 'exa':
                return ProviderConfig(
                    name="exa",
                    url=EXA_API_URL,  # 使用config中的URL
                    headers={"Authorization": f"Bearer {api_key}"},
                    build_payload=lambda query, system_prompt, extra: dict(
                        model=EXA_MODEL_NAME,  # 使用config中的模型名称
                        messages=[
                            {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                            {"role": "user", "content": query}
                        ],
                        extra_body={"text": True}
                    ),
                    parse_response=LLMUtils.parse_markdown_response
                )
            elif name.lower() == 'youchat':
                return ProviderConfig(
                    name="youchat",
                    url=YOUCOM_API_URL,  # 使用config中的URL
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    build_payload=lambda query, system_prompt, extra: {
                        "agent": extra.get("agent", "express"),
                        "input": query,
                        "tools": [
                            {"type": "web_search", "trigger": extra.get("trigger", "force")}
                        ]
                    },
                    parse_response=lambda r: {
                        "content": next(
                            (o["text"] for o in r.get("output", []) if o.get("type") == "message.answer"),
                            ""
                        ),
                        "references": [
                            item.get("url")
                            for o in r.get("output", [])
                            if o.get("type") == "web_search.results"
                            for item in o.get("content", [])
                            if "url" in item
                        ]
                    }
                )
            elif name.lower() == 'tavily':
                return ProviderConfig(
                    name="tavily",
                    url=TAVILY_API_URL,  # 使用config中的URL
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    },
                    build_payload=lambda query, system_prompt, extra: {
                        "query": query,
                        "include_answer": "basic"
                    },
                    parse_response=lambda r: {
                        "content": (
                                (r.get("answer") or "") + "\n\n" +
                                "\n".join(
                                    f"{item.get('title', '')}\n{item.get('content', '')}".strip()
                                    for item in r.get("results", [])
                                    if item.get("title") or item.get("content")
                                )
                        ).strip(),
                        "references": list({
                            item.get("url") for item in r.get("results", []) if item.get("url")
                        })
                    }
                )
            else:
                raise ValueError(f"不支持的搜索引擎: {name}")
        except Exception as e:
            logging.error(f"获取 {name} 配置失败: {str(e)}")
            raise


# 统一的调用接口
def call_llm(model_type, prompt):
    """调用指定的语言模型API获取回答

    Args:
        model_type (str): 模型类型，支持 'gpt-4o', 'perplexity', 'exa', 'youchat', 'tavily', 'deepseek'
        prompt (str): 提示词内容

    Returns:
        dict: 包含'content'和'references'的字典
    """
    try:
        # 获取API密钥
        api_key = LLMUtils.get_api_key(model_type=model_type)
        if not api_key:
            logging.error(f"未找到 {model_type} 的API密钥")
            return {
                "content": None,
                "references": []
            }

        # 根据不同模型类型调用相应的API
        if model_type == 'gpt-4o':
            return LLMUtils.call_gpt4o_api(prompt, api_key)
        elif model_type == 'deepseek':
            return LLMUtils.call_deepseek_api(prompt, api_key)
        else:
            # 对于搜索引擎类型，使用call_provider
            config = LLMUtils.get_provider_config(model_type, api_key)
            result = LLMUtils.call_provider(config, prompt)
            return result

    except Exception as e:
        logging.error(f"调用 {model_type} 时发生错误: {str(e)}")
        return {
            "content": None,
            "references": []
        }

# print(call_llm('gpt-4o', 'I want to buy some posters and prints, but I am not quite sure what to look for. Give me some recommended items and rank them in order.'))
