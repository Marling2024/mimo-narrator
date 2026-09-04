import os
from collections.abc import Callable
from pathlib import Path

import yaml
from dotenv import load_dotenv

from utils.text_splitter import split_text_by_punctuation
from utils.audio_handler import encode_audio_to_base64, concatenate_and_save_audio
from utils.api_client import MimoTTS


CONFIG_PATH = Path("config.yaml")


def load_config(config_path: str | Path = CONFIG_PATH) -> dict:
    """加载 YAML 配置文件。"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_voice_param(cfg: dict) -> str:
    """
    根据 tts_mode 解析 voice 参数。

    三种模式的 voice 格式完全不同（MIMO 官方规范）：
      - preset:       纯文本音色名
      - voice_design: 自然语言音色描述
      - voice_clone:  带 data URI 前缀的 Base64 参考音频
    """
    tts_mode = cfg["api"]["tts_mode"]

    if tts_mode == "preset":
        voice_name = cfg.get("preset", {}).get("voice_name", "")
        if not voice_name:
            raise ValueError("预置音色模式需要配置 preset.voice_name")
        return voice_name

    if tts_mode == "voice_design":
        voice_desc = cfg.get("voice_design", {}).get("voice_description", "")
        if not voice_desc:
            raise ValueError("音色设计模式需要配置 voice_design.voice_description")
        return voice_desc

    if tts_mode == "voice_clone":
        ref_path = cfg["paths"]["reference_audio"]
        return encode_audio_to_base64(ref_path)

    raise ValueError(f"不支持的 TTS 模式: {tts_mode}")


def _prepare_chunks(cfg: dict, large_text: str) -> list[str]:
    """根据配置决定按标点切分或整段返回。"""
    enable_split = cfg["tts_params"].get("enable_split", True)
    if enable_split:
        chunks = split_text_by_punctuation(
            large_text,
            max_length=cfg["tts_params"]["max_chars_per_chunk"]
        )
        print(f"📄 文本读取完毕，共切分为 {len(chunks)} 个处理分片。")
    else:
        chunks = [large_text]
        print(f"📄 文本读取完毕，未启用分片，整段提交合成（{len(large_text)} 字符）。")
    return chunks


def _print_voice_info(cfg: dict, tts_mode: str):
    """打印当前使用的 voice 信息。"""
    if tts_mode == "voice_clone":
        print("🎵 参考母带音频加载并 Base64 编码完成。")
    elif tts_mode == "preset":
        print(f"🎤 使用预置音色: {cfg['preset']['voice_name']}")
    elif tts_mode == "voice_design":
        desc = cfg["voice_design"]["voice_description"]
        print(f"🎨 使用音色描述: {desc[:30]}...")


def run_from_config(
    cfg: dict,
    api_key: str,
    progress_callback: Callable[[str], None] | None = None
) -> Path:
    """
    根据已解析的配置执行完整 TTS 流程。

    Args:
        cfg: 已加载/构造的配置字典，结构与 config.yaml 一致。
        api_key: MIMO API Key。
        progress_callback: 可选回调，接收状态文本，用于前端实时显示进度。

    Returns:
        输出音频文件路径。
    """
    def _emit(msg: str):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    tts_mode = cfg["api"]["tts_mode"]
    _emit(f"📋 当前 TTS 模式: {tts_mode}")

    # 1. 准备大文本
    input_path = Path(cfg["paths"]["input_text"])
    large_text = input_path.read_text(encoding="utf-8")

    # 2. 切分或整段
    chunks = _prepare_chunks(cfg, large_text)
    if not chunks:
        # 空文本若继续走完流程，会"成功"返回一个从未写出的音频文件
        raise ValueError(f"输入文本为空，无法合成: {input_path}")

    # 3. 根据模式解析 voice 参数
    voice_param = _resolve_voice_param(cfg)
    _print_voice_info(cfg, tts_mode)

    # 4. 初始化 TTS 客户端（根据 tts_mode 自动路由模型）
    tts = MimoTTS(
        api_key=api_key,
        base_url=cfg["api"]["base_url"],
        tts_mode=tts_mode
    )

    style = cfg["tts_params"].get("style_instruction", "")

    # voice_design 模式下是否启用文本智能润色
    optimize_text = cfg.get("voice_design", {}).get("optimize_text_preview", True)

    # 5. 遍历请求大文本的每一个分片
    generated_audio_chunks: list[bytes] = []
    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        _emit(f"⏳ 正在合成第 {i}/{total} 片段...")
        try:
            audio_bytes = tts.synthesize(
                text_chunk=chunk,
                style_instruction=style,
                voice_param=voice_param,
                optimize_text=optimize_text
            )
            generated_audio_chunks.append(audio_bytes)
        except Exception as e:
            _emit(f"❌ 第 {i} 片段合成失败: {e}")
            raise

    # 6. 音频无缝拼接保存
    output_path = Path(cfg["paths"]["output_audio"])
    concatenate_and_save_audio(generated_audio_chunks, output_path)
    return output_path


def main():
    print("🚀 开始执行 MIMO TTS 任务...")
    load_dotenv()
    api_key = os.environ.get("MIMO_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 MIMO_API_KEY")

    cfg = load_config()
    run_from_config(cfg, api_key)


if __name__ == "__main__":
    main()
