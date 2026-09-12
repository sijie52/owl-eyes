#!/bin/bash
# owl-eyes 一键安装：
#   1. 装 owl-eyes 命令到 ~/bin
#   2. 生成配置模板 ~/.config/owl-eyes/config
#   3. 配置 Claude Code（hooks 自动起停 + env 指向本地代理）
#   4. 提示注意事项
set -e

PROXY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/owl-eyes"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

echo "==> 0/4 检查依赖 (Python + Pillow)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "    错误: 未找到 python3，请先安装 Python 3"
    exit 1
fi
if ! python3 -c "import PIL" 2>/dev/null; then
    echo "    未找到 Pillow，正在安装..."
    pip3 install Pillow || { echo "    Pillow 安装失败，请手动执行: pip3 install Pillow"; exit 1; }
fi
echo "    OK"

echo "==> 1/4 安装命令（同时装到 ~/.local/bin 和 ~/bin，兼容不同 PATH 配置）"
for d in "$HOME/.local/bin" "$HOME/bin"; do
    mkdir -p "$d"
    # 用符号链接而非复制：脚本才能解析链接定位回项目目录、找到同目录的 proxy.py。
    # 复制件会因 BASH_SOURCE 指向 PATH 目录（如 ~/.local/bin）而找不到 proxy.py。
    ln -sf "$PROXY_DIR/owl-eyes" "$d/owl-eyes"
done
echo "    已安装: ~/.local/bin/owl-eyes + ~/bin/owl-eyes"

echo "==> 2/4 生成配置模板"
mkdir -p "$CONFIG_DIR"
python3 - "$CONFIG_DIR" <<'PYEOF'
import sys, os
from pathlib import Path
cfg_dir = Path(sys.argv[1])
cfg_file = cfg_dir / "config"
if not cfg_file.exists():
    cfg_file.write_text(
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
    print(f"    已生成: {cfg_file}  （请填入两个 key）")
else:
    print(f"    已存在: {cfg_file}")
PYEOF

echo "==> 3/4 配置 Claude Code (settings.json)"
python3 - "$CLAUDE_SETTINGS" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)

data = {}
if path.exists():
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        print("    警告: settings.json 解析失败，将覆盖（建议先备份）")

# 备份
bak = path.with_suffix(".json.owl-eyes.bak")
if path.exists():
    import shutil
    shutil.copy(path, bak)
    print(f"    已备份: {bak}")

# env: 指向本地代理
env = data.setdefault("env", {})
env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8788"
env["ANTHROPIC_AUTH_TOKEN"] = "owl-eyes-local"

# hooks: 会话开始自动起代理，结束自动停
hooks = data.setdefault("hooks", {})
hooks["SessionStart"] = [{"matcher": "", "hooks": [{"type": "command", "command": "owl-eyes start"}]}]
hooks["SessionEnd"] = [{"matcher": "", "hooks": [{"type": "command", "command": "owl-eyes stop"}]}]

path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
print("    已写入 env(ANTHROPIC_BASE_URL=http://127.0.0.1:8788) + hooks(自动起停)")
PYEOF

echo ""
echo "=============================================="
echo " 安装完成！还差两步："
echo ""
echo " 1. 编辑 $CONFIG_DIR/config 填入："
echo "    MODELSCOPE_KEY=xxx（ModelScope 令牌，ms- 开头）"
echo "    DEEPSEEK_KEY=xxx（DeepSeek API key）"
echo ""
echo " 2. 验证：新开一个 Claude Code 会话，贴一张图片测试"
echo "    代理日志: owl-eyes logs"
echo ""
echo " 注意事项："
echo " - 装了 owl-eyes 后，Claude Code 固定走本地代理，"
echo "   cc-switch 切换供应商会被绕过（上游由 owl-eyes 配置决定）"
echo " - 不想用了：编辑 ~/.claude/settings.json 删掉 env 和 hooks，"
echo "   或直接恢复备份 $CLAUDE_SETTINGS.owl-eyes.bak"
echo "=============================================="
