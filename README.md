# owl-eyes

给 DeepSeek 加视觉的本地代理。

DeepSeek 官方 API 是纯文本模型，在 Claude Code 里贴图它看不到内容，还会瞎编。owl-eyes 在中间加一层：图片先转成文字描述，再喂给 DeepSeek。它就能看图了。

## 原理

```
你粘贴图片
    │
    ▼
Claude Code ──→ 127.0.0.1:8788 (owl-eyes 代理)
                    │
        ┌───────────┴───────────┐
        │ 请求里有图片?          │
        ├─ 有 → 压缩 → 视觉模型  │
        │       → 文字描述       │
        │       → 注入请求       │
        └───────────┬───────────┘
                    ▼
          DeepSeek API（纯文本）
```

有图片的请求转成文字再转发，没有图片的请求原样透传。

## 安装

需要 macOS、Python 3、Claude Code、一个 DeepSeek API key。

```bash
git clone https://github.com/sijie52/owl-eyes.git
cd owl-eyes
bash install.sh
```

脚本会装好命令、配置 Claude Code（原配置自动备份）、检查 Pillow。

### 拿 ModelScope 免费 key

视觉转写用的 ModelScope 免费额度，要先注册：

1. 打开 https://modelscope.cn 注册（手机号即可）
2. 访问 https://modelscope.cn/my/myaccesstoken，新建访问令牌
3. 首次使用必须绑定阿里云账号。不绑会报 `Please bind your Alibaba Cloud account before use`，这个错很常见，别慌

### 填配置

```bash
nano ~/.config/owl-eyes/config
```

```
MODELSCOPE_KEY=ms-你的令牌
DEEPSEEK_KEY=你的 DeepSeek API key
```

然后新开一个 Claude Code 会话，贴图就能用了。

## 使用

日常无感：开 claude 自动起代理，退出自动停。手动控制：

```bash
owl-eyes status   # 代理状态
owl-eyes logs     # 查看日志
owl-eyes start    # 手动启动
owl-eyes stop     # 手动停止
```

## 已知限制

- 安装脚本是 bash，目前只支持 macOS
- 视觉模型对歧义图形（凹角/外角那种几何题）判断不稳定
- ModelScope 免费额度每天 2000 次（单模型 500 次），用完了等明天

## License

MIT
