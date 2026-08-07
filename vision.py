#!/usr/bin/env python3
"""owl-eyes 视觉转写：调 ModelScope 视觉模型，把图片转成严格转写文字"""
import json
import urllib.error
import urllib.request

import config

STRICT_PROMPT = (
    "你是图片转写器，任务只有一个：把这张图片转成文字。\n"
    "输出格式：\n"
    "1. 图片内容原文（中文，逐字转写）\n"
    "2. 图形/画面描述（形状、布局、每个标记的位置）\n"
    "3. 已知信息清单\n"
    "4. 所求内容（如果有）\n"
    "硬性规则：\n"
    "- 禁止解题、禁止计算答案、禁止推理、禁止假设任何未标注的信息\n"
    "- 公式和角一律用 LaTeX（如 $\\angle 1$、$60^\\circ$）\n"
    "- 看不清就写'看不清'，绝不编造\n"
    "- 只转写，不输出任何其他内容"
)


class VisionError(Exception):
    pass


def describe_image(jpeg_b64: str) -> str:
    """把 8-bit JPEG base64 图片转成文字描述。失败抛 VisionError。"""
    key = config.modelscope_key()
    if not key:
        raise VisionError("未配置 MODELSCOPE_KEY（运行 owl-eyes setup 或编辑 ~/.config/owl-eyes/config）")

    body = {
        "model": config.get("VISION_MODEL"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": STRICT_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{jpeg_b64}"}},
            ],
        }],
        "max_tokens": 1500,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        f"{config.get('MODELSCOPE_BASE')}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    timeout = int(config.get("VISION_TIMEOUT"))
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            last_err = f"视觉模型 HTTP {e.code}: {detail}"
            # 429 限流 / 5xx 服务错误：退避重试
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                import time as _t
                _t.sleep(2 * (attempt + 1))
                continue
            raise VisionError(last_err)
        except urllib.error.URLError as e:
            last_err = f"视觉模型网络错误: {e.reason}"
            if attempt < 2:
                import time as _t
                _t.sleep(2 * (attempt + 1))
                continue
            raise VisionError(last_err)
    raise VisionError(last_err or "视觉模型调用失败")
