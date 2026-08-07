# owl-eyes 🦉

**给 DeepSeek 装上眼睛** —— 本地代理，让 Claude Code + DeepSeek（或其他纯文本模型）也能"看见"图片。

DeepSeek 系列模型没有视觉能力，粘贴图片时它只会说"我看不到"甚至瞎猜内容。owl-eyes 在中间加一层：图片自动转成文字描述，再喂给 DeepSeek——它就能"看见"了。

## 原理

```
你粘贴图片
    │
    ▼
Claude Code ──→ 127.0.0.1:8788 (owl-eyes 本地代理)
                    │
        ┌───────────┴───────────┐
        │ 检测到图片?            │
        ├─ 有 → 压缩/转8bit      │
        │       ↓               │
        │  ModelScope 视觉模型   │
        │  → 文字描述（LaTeX）   │
        │       ↓               │
        │  文字注入请求          │
        └───────────┬───────────┘
                    ▼
          DeepSeek API（纯文本，无感知）
```

- 有图片的请求：自动转成文字后转发
- 无图片的请求：原样透传，零干预

## 特性

- 🆓 **零成本**：视觉模型走 ModelScope 免费额度（每天 2000 次）
- ⚡ **轻量**：纯 Python 标准库，392 行，无 Docker，无框架
- 🤖 **全自动**：开 Claude Code 自动起代理，退出自动停（hooks）
- 📐 **公式友好**：数学题截图转成 LaTeX，不是模糊描述
- 🔒 **本地隐私**：只监听 127.0.0.1，图片不出本机

## 安装

需要：macOS、Python 3、Claude Code、一个 DeepSeek API key。

### 1. 克隆并安装

```bash
git clone https://github.com/sijie52/owl-eyes.git
cd owl-eyes
bash install.sh
```

install.sh 会自动：检查/安装 Pillow、装命令、配置 Claude Code（自动备份原配置）。

### 2. 获取 ModelScope 免费 key（⚠️ 重点看这里）

1. 打开 https://modelscope.cn 注册/登录（手机号即可）
2. 访问 https://modelscope.cn/my/myaccesstoken
3. **必须绑定阿里云账号**（用支付宝/淘宝扫码最快）——不绑定会报
   `Please bind your Alibaba Cloud account before use`，这是最常见的坑
4. 新建访问令牌，复制（`ms-` 开头的格式）

### 3. 填配置

```bash
nano ~/.config/owl-eyes/config
```

```ini
MODELSCOPE_KEY=ms-你的令牌
DEEPSEEK_KEY=你的 DeepSeek API key
```

### 4. 完成

新开一个 Claude Code 会话（会自动起代理），粘贴一张图片试试。

## 使用

- 日常使用：无感知，开 claude 贴图即可
- 代理状态：`owl-eyes status`
- 查看日志：`owl-eyes logs`
- 手动启停：`owl-eyes start` / `owl-eyes stop`

## 视觉模型

默认 `Qwen/Qwen3-VL-235B-A22B-Instruct`（ModelScope 免费），可在配置里换：

```ini
VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct
```

ModelScope 上可用的视觉模型（2026-08）：Qwen3-VL-235B / Qwen3-VL-8B / Qwen3-VL-8B-Thinking / InternVL3_5-241B / ERNIE-4.5-VL-28B。

## 卸载

```bash
# 恢复 Claude Code 原配置（install.sh 自动备份过）
cp ~/.claude/settings.json.owl-eyes.bak ~/.claude/settings.json
# 删命令和配置
rm ~/.local/bin/owl-eyes ~/bin/owl-eyes
rm -rf ~/.config/owl-eyes
```

## 已知限制

- 仅 macOS（install.sh 是 bash，Windows 需手动配置）
- 视觉转写对"歧义图形"（凹角/外角、信息不全的几何题）判断可能不稳定
- 免费额度：ModelScope 每天 2000 次（单模型 500 次），超了等明天

## License

MIT
