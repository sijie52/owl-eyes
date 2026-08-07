#!/usr/bin/env python3
"""owl-eyes 冒烟测试：模拟 Claude Code 请求走全链路
前提：代理已启动 (owl-eyes start)
测试：
  1. 无图请求 → 透传 DeepSeek → 正常回复
  2. 带图请求 → 视觉转写 → DeepSeek 回复应体现图片内容
  3. 流式请求 → SSE 事件流正常
"""
import base64
import json
import os
import sys
import urllib.request

PROXY = "http://127.0.0.1:8788"
IMAGE = os.environ.get("OWL_EYES_TEST_IMAGE", "/tmp/vision_test/math_question_small.jpg")


def send(payload: dict) -> tuple:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{PROXY}/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": "test-placeholder",  # 模拟 Claude Code 的认证头，代理应替换
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def test_no_image():
    payload = {
        "model": "deepseek-v4-flash",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "只回复四个字：冒烟测试"}],
        "stream": False,
    }
    status, text = send(payload)
    print(f"[1] 无图请求: status={status}")
    try:
        data = json.loads(text)
        content = next((b["text"] for b in data["content"] if b.get("type") == "text"), "")
        print(f"    回复: {content[:100]}")
        return status == 200 and len(content) > 0
    except Exception as e:
        print(f"    解析失败: {e} | {text[:200]}")
        return False


def test_with_image():
    if not os.path.exists(IMAGE):
        print(f"[2] 跳过: 测试图片不存在，可用 OWL_EYES_TEST_IMAGE 指定路径")
        return True
    img_b64 = base64.b64encode(open(IMAGE, "rb").read()).decode()
    payload = {
        "model": "deepseek-v4-flash",
        "max_tokens": 2000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "图片里是什么几何题？根据转写内容回答，用中文。"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
            ],
        }],
        "stream": False,
    }
    status, text = send(payload)
    print(f"[2] 带图请求: status={status}")
    try:
        data = json.loads(text)
        # 转写内容会进入模型的 thinking/text，全文搜验证
        full = " ".join((b.get("text") or b.get("thinking") or "") for b in data["content"])
        print(f"    上下文含图片信息: {'五边形' in full or '角' in full} (内容长度={len(full)})")
        return status == 200 and ("五边形" in full or "角" in full)
    except Exception as e:
        print(f"    解析失败: {e} | {text[:300]}")
        return False


def test_stream():
    payload = {
        "model": "deepseek-v4-flash",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "从1数到5"}],
        "stream": True,
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{PROXY}/v1/messages", data=body,
        headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode()
        has_event = "event:" in raw or "content_block_delta" in raw
        print(f"[3] 流式请求: status={resp.status} 含SSE事件={has_event} 长度={len(raw)}")
        return has_event
    except urllib.error.HTTPError as e:
        print(f"[3] 流式请求失败: {e.code} {e.read().decode()[:200]}")
        return False


if __name__ == "__main__":
    ok = True
    ok &= test_no_image()
    print()
    ok &= test_with_image()
    print()
    ok &= test_stream()
    print("\n结果:", "全部通过 ✅" if ok else "有失败 ❌")
    sys.exit(0 if ok else 1)
