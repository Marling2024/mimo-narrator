# mimo-narrator

基于小米 MiMo TTS API 的大文本语音合成工具：把整篇文稿自动变成一段完整、音色统一的语音——按标点智能切分、逐片合成、无缝拼接，全程只需一条命令。支持命令行和 Gradio Web UI 两种使用方式。

## 为什么需要它

TTS API 对单次请求的文本长度有限制，长文本直接提交会失败或超时。mimo-narrator 在本地处理好这件事：

```
整篇文稿 ──▶ 按标点智能切分 ──▶ 逐片调用 MiMo API 合成 ──▶ 参数归一化无缝拼接 ──▶ 完整 WAV 音频
```

- **智能切分**：优先在句号、问号、感叹号和换行处断句，保留语义完整；短句自动合并以减少 API 调用；超长单句按字符兜底切分，内容零丢失
- **音色统一**：三种模式（预置 / 设计 / 克隆）的音色参数在一次任务中全程复用，拼接后听感一致
- **无缝拼接**：拼接前统一采样率、声道、位深，直接拼原始音频字节，O(n) 一次导出
- **自动重试**：网络波动、限流、服务端 5xx 指数退避自动重试；鉴权失败等确定性错误立即报错，不浪费时间
- **实时进度**：Web UI 提供进度条和状态日志，长文合成过程一目了然

## 三种合成模式

| 模式 | 说明 | 关键配置 |
| --- | --- | --- |
| `preset` 预置音色 | 直接使用官方预置音色（如 "冰糖"） | `preset.voice_name` |
| `voice_design` 音色设计 | 用一段自然语言描述生成专属音色 | `voice_design.voice_description` |
| `voice_clone` 音色克隆 | 上传 10~15 秒清晰人声参考音频克隆音色 | `paths.reference_audio`（wav/mp3，≤10MB） |

切换模式只需改 `config.yaml` 中的 `api.tts_mode`，主流程自动路由到对应模型端点和参数格式，无需改代码。

## 快速开始

### 环境要求

- Python 3.10+
- **FFmpeg**：pydub 读取非 WAV 音频（如参考音频为 MP3）时依赖系统 FFmpeg，需自行安装并加入 PATH
  - Windows: `winget install ffmpeg` 或从官网下载
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

### 安装与配置

```bash
pip install -r requirements.txt
```

1. 在项目根目录创建 `.env` 文件，填入 API Key：

   ```
   MIMO_API_KEY=你的密钥
   ```

2. 按需编辑 `config.yaml`（模式、音色、风格指令、输入输出路径）。

### 使用

命令行：

```bash
python main.py
```

Web UI（浏览器访问 http://127.0.0.1:7860，可在页面内选模式、编辑文本、查看进度）：

```bash
python web_ui.py
```

合成结果输出到 `config.yaml` 中 `paths.output_audio` 指定的路径。

## 常用配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `api.tts_mode` | `voice_clone` | 合成模式，见上表 |
| `tts_params.enable_split` | `true` | 是否按标点切分；`false` 则整段提交 |
| `tts_params.max_chars_per_chunk` | `150` | 每片最大字符数，值越小单次响应越快 |
| `tts_params.style_instruction` | 空 | 风格指令（语速、情感、咬字等），可选 |
| `voice_design.optimize_text_preview` | `true` | 让模型先智能润色文本再合成（仅音色设计模式） |

## 常见问题

**参考音频有什么要求？**
不超过 10MB，wav 或 mp3 格式，10~15 秒清晰、无背景噪音的人声效果最佳。超过 15 秒的部分会被自动截断。

**合成中途某个分片失败了怎么办？**
瞬时错误（网络/限流）会自动重试最多 6 次；重试耗尽或遇到确定性错误（如密钥无效）会立即中断并明确报错，不会静默输出残缺音频。

**为什么提示找不到 FFmpeg？**
参考音频为 MP3 等非 WAV 格式时，pydub 需要 FFmpeg 解码。安装方法见"环境要求"，或直接改用 WAV 参考音频。

**更多 API 细节？**
`docs/` 目录收录了 MiMo TTS 的官方文档摘录：[API 参考](docs/api-reference.md)、[音频标记控制](docs/audio-tag-control.md)、[音色设计指南](docs/voice-design-guide.md)、[使用示例](docs/usage-examples.md)、[注意事项](docs/precautions.md)。

## 项目结构

```
main.py               # 命令行入口 + TTS 主流程（切分 → 逐片合成 → 拼接）
web_ui.py             # Gradio Web UI
utils/api_client.py   # MIMO API 客户端（三种模式模型路由、瞬时错误重试）
utils/audio_handler.py# 参考音频编码、音频拼接
utils/text_splitter.py# 按标点的文本切分
config.yaml           # 运行配置
docs/                 # MIMO API 官方文档摘录
tests/                # pytest 测试（45 个用例）
```

## 测试

```bash
python -m pytest
```
