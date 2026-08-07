#!/usr/bin/env python3
"""owl-eyes 配置加载
优先级：环境变量 > 配置文件 (~/.config/owl-eyes/config)
"""
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("OWL_EYES_CONFIG_DIR", "~/.config/owl-eyes")).expanduser()
CONFIG_FILE = CONFIG_DIR / "config"

DEFAULTS = {
    "PORT": "8788",
    "HOST": "127.0.0.1",
    "VISION_MODEL": "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "MODELSCOPE_BASE": "https://api-inference.modelscope.cn/v1",
    "DEEPSEEK_BASE": "https://api.deepseek.com/anthropic",
    "MAX_IMAGE_DIM": "2048",
    "VISION_TIMEOUT": "90",
}


def _load_file() -> dict:
    cfg = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def get(key: str) -> str:
    env_key = "OWL_EYES_" + key
    if env_key in os.environ and os.environ[env_key]:
        return os.environ[env_key]
    file_cfg = _load_file()
    if key in file_cfg:
        return file_cfg[key]
    return DEFAULTS.get(key, "")


def modelscope_key() -> str:
    """ModelScope key：去掉 ms- 前缀"""
    key = get("MODELSCOPE_KEY")
    if key.startswith("ms-"):
        key = key[3:]
    return key


def deepseek_key() -> str:
    return get("DEEPSEEK_KEY")


def ensure_config_file() -> Path:
    """确保配置文件存在（不存在则写模板），返回路径"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            "# owl-eyes 配置\n"
            "# ModelScope 令牌（https://modelscope.cn/my/myaccesstoken 获取，ms- 前缀可留可去）\n"
            "MODELSCOPE_KEY=\n"
            "# DeepSeek API key（转发上游用）\n"
            "DEEPSEEK_KEY=\n"
            "# 可选：视觉模型 / 端口 / 上游地址\n"
            "# VISION_MODEL=Qwen/Qwen3-VL-235B-A22B-Instruct\n"
            "# PORT=8788\n"
            "# DEEPSEEK_BASE=https://api.deepseek.com/anthropic\n"
        )
    return CONFIG_FILE
