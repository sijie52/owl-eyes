#!/usr/bin/env python3
"""owl-eyes 图片预处理：转 8-bit、压缩到尺寸上限、编码 JPEG"""
import base64
import io

from PIL import Image

import config


def image_bytes_to_jpeg_b64(data: bytes) -> str:
    """把任意图片字节转成 8-bit JPEG 的 base64（无 data URL 前缀）"""
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"无法解析图片: {e}")

    # 统一转 RGB（16-bit PNG 或带 alpha 的图都会在此变成 8-bit RGB）
    img = img.convert("RGB")

    # 等比压缩到上限内
    max_dim = int(config.get("MAX_IMAGE_DIM"))
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def is_valid_image(data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        return True
    except Exception:
        return False
