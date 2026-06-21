import json
import threading
import time
from pathlib import Path
from openai import OpenAI
from typing import Dict, Any, Optional

class DictionaryManager:
    def __init__(self, dict_path):
        self.dict_path = Path(dict_path)
        self.dictionary = {}
        self.last_modified = 0
        self.lock = threading.Lock()
        self.load_dictionary()
        
    def load_dictionary(self):
        """加载或重新加载字典"""
        try:
            if not self.dict_path.exists():
                print(f"\033[33m[配置重载]警告：dictionary文件 {self.dict_path} 未找到\033[0m")
                return {}
                
            current_modified = self.dict_path.stat().st_mtime
            if current_modified <= self.last_modified:
                return  # 文件未修改
                
            with open(self.dict_path, 'r', encoding='utf8') as f:
                new_dict = json.load(f)
                
            if not isinstance(new_dict, dict):
                print(f"\033[31m[配置重载]错误：dictionary文件 {self.dict_path} 不是有效的JSON对象\033[0m")
                return
                
            # 按key长度降序排序
            sorted_dict = {
                k: new_dict[k] 
                for k in sorted(new_dict.keys(), key=len, reverse=True)
            }
            
            with self.lock:
                self.dictionary = sorted_dict
                self.last_modified = current_modified
                
            print(f"\033[33m[配置重载]dictionary已重新加载，修改时间: {time.ctime(current_modified)}，共 {len(sorted_dict)} 条记录\033[0m")
            
        except json.JSONDecodeError:
            print(f"\033[31m[配置重载]错误：dictionary文件 {self.dict_path} JSON格式错误\033[0m")
        except Exception as e:
            print(f"\033[31m[配置重载]读取dictionary文件时发生错误: {e}\033[0m")
            
    def get_dict_matches(self, text):
        """获取匹配的字典条目"""
        with self.lock:
            if not self.dictionary:
                return {}
                
            matches = {}
            remaining_text = text
            
            for key in self.dictionary:
                if key in remaining_text:
                    matches[key] = self.dictionary[key]
                    remaining_text = remaining_text.replace(key, '')
                    if not remaining_text:
                        break
                        
            return matches

    def start_watcher(self, interval=5):
        """启动字典文件监视器"""
        def watch():
            while True:
                self.load_dictionary()
                time.sleep(interval)
                
        watcher_thread = threading.Thread(target=watch, daemon=True)
        watcher_thread.start()
        print(f"\033[33m[配置重载]dictionary文件监视器已启动，每 {interval} 秒检查一次更新\033[0m")

class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.last_modified: float = 0
        self.lock = threading.Lock()
        self.load_config()
        
    def load_config(self) -> Optional[Dict[str, Any]]:
        """加载或重新加载config文件"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config file {self.config_path} not found")
                
            current_modified = self.config_path.stat().st_mtime
            if current_modified <= self.last_modified:
                return None  # 文件未修改
                
            with open(self.config_path, 'r', encoding='utf8') as f:
                new_config = json.load(f)
                
            # 验证必要字段
            required_sections = ['api_keys', 'model_params', 'api_priority']
            for section in required_sections:
                if section not in new_config:
                    raise ValueError(f"Missing required section: {section}")
            
            with self.lock:
                self.config = new_config
                self.last_modified = current_modified
                
            print(f"\033[33m[配置重载]config已重新加载，修改时间: {time.ctime(current_modified)}\033[0m")
            return new_config
            
        except json.JSONDecodeError:
            print(f"\033[31m[配置重载]错误：config文件 {self.config_path} JSON格式错误\033[0m")
        except Exception as e:
            print(f"\033[31m[配置重载]读取config文件时发生错误: {e}\033[0m")
        return None
            
    def get_config(self) -> Dict[str, Any]:
        """获取当前config"""
        with self.lock:
            return self.config.copy()
            
    def update_clients(self, clients: Dict[str, Any], model_types: Dict[str, Any]) -> bool:
        """更新API客户端config"""
        try:
            config = self.get_config()
            if 'api_keys' not in config:
                return False
                
            new_clients = {}
            new_model_types = {}
            
            # 循环初始化所有API客户端
            for api_type, api_config in config['api_keys'].items():
                new_clients[api_type] = OpenAI(
                    api_key=api_config['api_key'],
                    base_url=api_config['base_url']
                )
                new_model_types[api_type] = api_config['model_type']
            
            # 原子性替换
            with self.lock:
                clients.clear()
                clients.update(new_clients)
                model_types.clear()
                model_types.update(new_model_types)
            
            return True
            
        except Exception as e:
            print(f"\033[31m[配置重载]更新API客户端config失败: {e}\033[0m")
            return False

    def start_watcher(self, interval: int = 5):
        """启动config文件监视器"""
        def watch():
            while True:
                self.load_config()
                time.sleep(interval)
                
        watcher_thread = threading.Thread(target=watch, daemon=True)
        watcher_thread.start()
        print(f"\033[33m[配置重载]config文件监视器已启动，每 {interval} 秒检查一次更新\033[0m")