import os
import time
import yaml
from dotenv import load_dotenv
from utils.text_splitter import split_text_by_punctuation
from utils.audio_handler import encode_audio_to_base64, concatenate_and_save_audio
from utils.api_client import MimoTTS


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
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

    elif tts_mode == "voice_design":
        voice_desc = cfg.get("voice_design", {}).get("voice_description", "")
        if not voice_desc:
            raise ValueError("音色设计模式需要配置 voice_design.voice_description")
        return voice_desc

    elif tts_mode == "voice_clone":
        ref_path = cfg["paths"]["reference_audio"]
        return encode_audio_to_base64(ref_path)

    else:
        raise ValueError(f"不支持的 TTS 模式: {tts_mode}")


def main():
    print("🚀 开始执行 MIMO TTS 任务...")
    load_dotenv()
    api_key = os.environ.get("MIMO_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 MIMO_API_KEY")

    cfg = load_config()
    tts_mode = cfg["api"]["tts_mode"]
    print(f"📋 当前 TTS 模式: {tts_mode}")

    # 1. 准备大文本
    with open(cfg["paths"]["input_text"], "r", encoding="utf-8") as f:
        large_text = f.read()

    # 根据配置决定是否切分：切分是为了避免单次 API 调用超出模型最大生成长度（finish_reason=length 截断），
    # 但对于短文本或需要模型自行掌控语流连贯性的场合，关闭切分能获得更自然的韵律过渡
    enable_split = cfg["tts_params"].get("enable_split", True)
    if enable_split:
        chunks = split_text_by_punctuation(large_text, max_length=cfg["tts_params"]["max_chars_per_chunk"])
        print(f"📄 文本读取完毕，共切分为 {len(chunks)} 个处理分片。")
    else:
        chunks = [large_text]
        print(f"📄 文本读取完毕，未启用分片，整段提交合成（{len(large_text)} 字符）。")

    # 2. 根据模式解析 voice 参数
    voice_param = _resolve_voice_param(cfg)
    if tts_mode == "voice_clone":
        print("🎵 参考母带音频加载并Base64编码完成。")
    elif tts_mode == "preset":
        print(f"🎤 使用预置音色: {cfg['preset']['voice_name']}")
    elif tts_mode == "voice_design":
        print(f"🎨 使用音色描述: {cfg['voice_design']['voice_description'][:30]}...")

    # 3. 初始化 TTS 客户端（根据 tts_mode 自动路由模型）
    tts = MimoTTS(
        api_key=api_key,
        base_url=cfg["api"]["base_url"],
        tts_mode=tts_mode
    )

    style = cfg["tts_params"].get("style_instruction", "")
    generated_audio_chunks = []

    # voice_design 模式下是否启用文本智能润色
    optimize_text = cfg.get("voice_design", {}).get("optimize_text_preview", True)

    # 4. 遍历请求大文本的每一个分片
    for i, chunk in enumerate(chunks, 1):
        print(f"⏳ 正在合成第 {i}/{len(chunks)} 片段...")
        try:
            audio_bytes = tts.synthesize(
                text_chunk=chunk,
                style_instruction=style,
                voice_param=voice_param,
                optimize_text=optimize_text
            )
            generated_audio_chunks.append(audio_bytes)
        except Exception as e:
            print(f"❌ 第 {i} 片段合成失败: {str(e)}")
            raise

    # 5. 音频无缝拼接保存
    concatenate_and_save_audio(generated_audio_chunks, cfg["paths"]["output_audio"])


if __name__ == "__main__":
    main()
