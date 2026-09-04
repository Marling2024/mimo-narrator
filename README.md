# mimo-narrator

基于小米 MiMo TTS API 的大文本语音合成工具：自动将长文本按标点切分、逐片合成并无缝拼接为完整音频。支持命令行和 Gradio Web UI 两种使用方式。

## 环境要求

- Python 3.10+
- **FFmpeg**：pydub 读取非 WAV 音频（如参考音频为 MP3）时依赖系统 FFmpeg，需自行安装并加入 PATH
  - Windows: `winget install ffmpeg` 或从官网下载
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

## 安装

```bash
pip install -r requirements.txt
```

## 配置

1. 在项目根目录创建 `.env` 文件，填入 API Key：

   ```
   MIMO_API_KEY=你的密钥
   ```

2. 按需编辑 `config.yaml`，三种合成模式（`api.tts_mode`）：

   | 模式 | 说明 | 关键配置 |
   | --- | --- | --- |
   | `preset` | 预置音色 | `preset.voice_name`（如 "冰糖"） |
   | `voice_design` | 自然语言描述生成音色 | `voice_design.voice_description` |
   | `voice_clone` | 参考音频克隆音色 | `paths.reference_audio`（wav/mp3，≤10MB，建议 10~15 秒清晰人声） |

   其余参数：`enable_split`（按标点切分）、`max_chars_per_chunk`（每片最大字符数）、`style_instruction`（风格指令）等。

## 使用

命令行：

```bash
python main.py
```

Web UI（浏览器访问 http://127.0.0.1:7860，可在页面内选模式、编辑文本、查看进度）：

```bash
python web_ui.py
```

合成结果输出到 `config.yaml` 中 `paths.output_audio` 指定的路径。

## 测试

```bash
python -m pytest
```

## 项目结构

```
main.py               # 命令行入口 + TTS 主流程（切分 → 逐片合成 → 拼接）
web_ui.py             # Gradio Web UI
utils/api_client.py   # MIMO API 客户端（三种模式模型路由、重试）
utils/audio_handler.py# 参考音频编码、音频拼接
utils/text_splitter.py# 按标点的文本切分
config.yaml           # 运行配置
docs/                 # MIMO API 官方文档摘录
```
