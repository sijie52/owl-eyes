#!/usr/bin/env python3
"""owl-eyes 本地代理：Claude Code → (图片转文字) → DeepSeek
监听 127.0.0.1:8788，处理 Anthropic Messages API 请求。
有图片的请求：预处理 → 视觉模型转文字 → 替换图片块 → 转发 DeepSeek
无图片的请求：认证替换后原样转发
"""
import base64
import json
import time
from http.client import HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import preprocess
import vision

VISION_PREFIX = "[图片内容（owl-eyes 视觉转写）]\n"


class OwlEyesHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 静默默认日志，用自定义
        pass

    def _log(self, msg):
        print(f"[owl-eyes {time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def _send_json(self, status: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_health(self):
        self._send_json(200, {"status": "ok"})

    def _clean_path(self) -> str:
        """去掉查询参数，如 /v1/messages?beta=true → /v1/messages"""
        from urllib.parse import urlsplit
        return urlsplit(self.path).path

    def do_GET(self):
        path = self._clean_path()
        self._log(f"GET {self.path}")
        if path == "/health":
            self._send_health()
        elif path == "/v1/models":
            # Claude Code 启动/运行 /model 时会请求模型列表并校验配置的模型名
            # 同时返回标准名和 cc-switch 的 [1m] 变体，避免本地校验失败
            self._send_json(200, {"data": [
                {"id": "deepseek-v4-flash", "object": "model", "owned_by": "deepseek"},
                {"id": "deepseek-v4-pro", "object": "model", "owned_by": "deepseek"},
                {"id": "DeepSeek-V4-pro[1m]", "object": "model", "owned_by": "deepseek"},
                {"id": "Deepseek-v4-pro[1m]", "object": "model", "owned_by": "deepseek"},
                {"id": "DeepSeek-V4-flash[1m]", "object": "model", "owned_by": "deepseek"},
                {"id": "Deepseek-v4-flash[1m]", "object": "model", "owned_by": "deepseek"},
            ]})
        else:
            self._send_json(404, {"error": {"type": "not_found", "message": "not found"}})

    def do_POST(self):
        path = self._clean_path()
        self._log(f"POST {self.path} (len={self.headers.get('Content-Length', 0)})")
        if path != "/v1/messages":
            self._send_json(404, {"error": {"type": "not_found", "message": "not found"}})
            return

        t0 = time.time()
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b""

        # 解析请求，处理图片块
        try:
            req = json.loads(raw_body)
        except json.JSONDecodeError:
            req = None

        images_found = 0
        vision_total = 0.0
        if req and isinstance(req.get("messages"), list):
            for msg in req["messages"]:
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                new_blocks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image":
                        images_found += 1
                        vt0 = time.time()
                        try:
                            src = block.get("source", {})
                            img_b64 = src.get("data", "")
                            jpeg_b64 = preprocess.image_bytes_to_jpeg_b64(
                                base64.b64decode(img_b64)
                            )
                            desc = vision.describe_image(jpeg_b64)
                            new_blocks.append({
                                "type": "text",
                                "text": VISION_PREFIX + desc,
                            })
                        except vision.VisionError as e:
                            new_blocks.append({
                                "type": "text",
                                "text": f"[owl-eyes 视觉转写失败: {e}]",
                            })
                        except Exception as e:
                            new_blocks.append({
                                "type": "text",
                                "text": f"[owl-eyes 图片处理失败: {e}]",
                            })
                        vision_total += time.time() - vt0
                    else:
                        new_blocks.append(block)
                msg["content"] = new_blocks

        # 模型名归一化：cc-switch 的 [1m] 变体 → DeepSeek 标准名
        if req and req.get("model"):
            m = str(req["model"]).lower()
            if "flash" in m:
                req["model"] = "deepseek-v4-flash"
            elif "pro" in m:
                req["model"] = "deepseek-v4-pro"

        # 转发上游
        body = json.dumps(req).encode() if req else raw_body
        status = self._forward(body)
        dt = time.time() - t0
        self._log(
            f"POST {self.path} 图片={images_found} 视觉耗时={vision_total:.1f}s "
            f"总耗时={dt:.1f}s 上游状态={status}"
        )

    def _forward(self, body: bytes):
        """转发到 DeepSeek，流式回传。返回 (status, content_type)。"""
        from urllib.parse import urlsplit
        u = urlsplit(config.get("DEEPSEEK_BASE"))
        host = u.hostname
        port = u.port or (443 if u.scheme == "https" else 80)
        use_https = u.scheme == "https"
        path = u.path.rstrip("/") + "/v1/messages"

        if use_https:
            conn = HTTPSConnection(host, port, timeout=300)
        else:
            from http.client import HTTPConnection
            conn = HTTPConnection(host, port, timeout=300)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.deepseek_key()}",
            "anthropic-version": self.headers.get("anthropic-version", "2023-06-01"),
            "Content-Length": str(len(body)),
        }
        conn.request("POST", path, body=body, headers=headers)
        up_resp = conn.getresponse()
        status = up_resp.status

        self.send_response(status)
        skip = {"content-length", "connection", "transfer-encoding", "keep-alive"}
        for k, v in up_resp.getheaders():
            if k.lower() not in skip:
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        try:
            while True:
                chunk = up_resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            conn.close()
        return status


def main():
    import argparse
    ap = argparse.ArgumentParser(description="owl-eyes 本地代理")
    ap.add_argument("--port", type=int, default=int(config.get("PORT")))
    args = ap.parse_args()

    if not config.deepseek_key():
        print("警告: 未配置 DEEPSEEK_KEY，转发会失败。运行 owl-eyes setup 配置。")
    if not config.modelscope_key():
        print("警告: 未配置 MODELSCOPE_KEY，图片转写会失败。运行 owl-eyes setup 配置。")

    server = ThreadingHTTPServer((config.get("HOST"), args.port), OwlEyesHandler)
    print(f"owl-eyes 代理运行中: http://{config.get('HOST')}:{args.port} (Ctrl+C 停止)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nowl-eyes 已停止", flush=True)
        server.server_close()


if __name__ == "__main__":
    main()
