import os
import logging
import json
import sys

def setup_logging(log_file=None):
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file) if log_file else logging.StreamHandler(),
            logging.StreamHandler()
        ]
    )


def load_json_file(file_path):
    """加载JSON文件"""
    try:
        if not os.path.exists(file_path):
            logging.warning(f"文件不存在: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        logging.error(f"解析JSON文件失败: {str(e)}")
        # 尝试按行解析JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = []
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                return data if data else None
        except Exception as ex:
            logging.error(f"按行解析JSON文件也失败: {str(ex)}")
            return None
    except Exception as e:
        logging.error(f"读取文件时发生错误: {str(e)}")
        return None


def save_json_file(data, file_path):
    """保存数据到JSON文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"数据已保存到: {file_path}")
        return True
    except Exception as e:
        logging.error(f"保存数据到文件时发生错误: {str(e)}")
        return False


def generate_timestamped_filename(base_path, timestamp):
    """生成带时间戳的文件名"""

    # 分离目录、文件名和扩展名
    dir_name, file_name = os.path.split(base_path)
    name_without_ext, ext = os.path.splitext(file_name)

    # 生成新的文件名
    new_file_name = f"{name_without_ext}_{timestamp}{ext}"

    # 组合成新的完整路径
    new_path = os.path.join(dir_name, new_file_name)

    return new_path


def generate_id(content):
    """根据内容生成唯一ID"""
    try:
        import hashlib
        if isinstance(content, dict):
            content = json.dumps(content, sort_keys=True)
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    except Exception as e:
        logging.error(f"生成ID时发生错误: {str(e)}")
        return None


def read_file_lines(file_path):
    """读取文件的所有行"""
    try:
        if not os.path.exists(file_path):
            logging.warning(f"文件不存在: {file_path}")
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"读取文件行时发生错误: {str(e)}")
        return []


def get_file_paths(directory, extension=None):
    """获取目录下所有指定扩展名的文件路径"""
    file_paths = []
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if extension and not file.endswith(extension):
                    continue
                file_paths.append(os.path.join(root, file))
    except Exception as e:
        logging.error(f"获取文件路径时发生错误: {str(e)}")
    return file_paths