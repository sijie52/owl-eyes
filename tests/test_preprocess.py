#!/usr/bin/env python3
"""owl-eyes 单元测试：preprocess（16-bit 转换、尺寸压缩）"""
import base64
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

import preprocess

# 测试素材：16-bit PNG（几何题原图，1290x2796 16-bit）、普通截图、超大图
SRC_16BIT = Path("/Users/caosijie/.hermes/images/clip_20260806_184540_4.png")
SRC_GEOM = Path("/tmp/vision_test/math_question.jpg")
GENERATED = Path("/tmp/vision_test/gen_test.png")


def make_test_images():
    """生成测试图：16-bit PNG + 超大 PNG"""
    # 16-bit PNG（用验收考卷原图，本来就是 16-bit）
    if not SRC_16BIT.exists():
        print(f"SKIP: 缺少 {SRC_16BIT}")
        return False
    # 超大图：4000x3000
    img = Image.new("RGB", (4000, 3000), (200, 100, 50))
    img.save(GENERATED)
    return True


def test_16bit_to_jpeg():
    data = SRC_16BIT.read_bytes()
    b64 = preprocess.image_bytes_to_jpeg_b64(data)
    raw = base64.b64decode(b64)
    # 验证是有效 JPEG
    img = Image.open(io.BytesIO(raw))
    print(f"[1] 16-bit PNG → JPEG: mode={img.mode} size={img.size} bytes={len(raw)}")
    assert img.mode == "RGB"
    assert img.size[0] <= 2048 and img.size[1] <= 2048, "尺寸应被压缩到 2048 内"
    print("    PASS")
    return True


def test_oversize_compress():
    data = GENERATED.read_bytes()
    b64 = preprocess.image_bytes_to_jpeg_b64(data)
    raw = base64.b64decode(b64)
    img = Image.open(io.BytesIO(raw))
    print(f"[2] 4000x3000 → JPEG: size={img.size} bytes={len(raw)}")
    assert max(img.size) <= 2048, "超大图应压缩到 2048 内"
    assert img.size == (2048, 1536), f"等比缩放应保持比例，实际 {img.size}"
    print("    PASS")
    return True


def test_normal_passthrough():
    data = SRC_GEOM.read_bytes()
    b64 = preprocess.image_bytes_to_jpeg_b64(data)
    raw = base64.b64decode(b64)
    img = Image.open(io.BytesIO(raw))
    print(f"[3] 正常 JPEG: size={img.size} bytes={len(raw)}")
    assert max(img.size) <= 2048
    print("    PASS")
    return True


def test_invalid_image():
    try:
        preprocess.image_bytes_to_jpeg_b64(b"not an image at all")
        print("[4] 非法图片: 未抛异常 (FAIL)")
        return False
    except ValueError as e:
        print(f"[4] 非法图片: 正确拒绝 ({e})")
        print("    PASS")
        return True


if __name__ == "__main__":
    if not make_test_images():
        sys.exit(1)
    ok = True
    ok &= test_16bit_to_jpeg()
    ok &= test_oversize_compress()
    ok &= test_normal_passthrough()
    ok &= test_invalid_image()
    print("\n结果:", "全部通过 ✅" if ok else "有失败 ❌")
    sys.exit(0 if ok else 1)
