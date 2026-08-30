import base64
import io
import os
from pathlib import Path
from pydub import AudioSegment


def encode_audio_to_base64(file_path: str | os.PathLike, max_duration_sec: int = 15) -> str:
    """
    读取参考音频，仅做必要的长度截断以满足平台大小要求，
    保留原始音质、采样率和声道，并转为带 data URI 的 Base64。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"未找到参考音频文件: {path}")

    # 使用 pydub 加载克隆参考母带
    audio = AudioSegment.from_file(str(path))

    # 仅做时长限制，通常 10~15 秒的清晰人声足以完美克隆，
    # 截断可以防止文件体积超标（官方限制 < 10MB）或导致请求体过大
    max_ms = max_duration_sec * 1000
    if len(audio) > max_ms:
        print(f"✂️ 参考音频超过 {max_duration_sec} 秒，自动截取前端有效声纹，保留无损音质...")
        audio = audio[:max_ms]

    # 直接以无损 WAV 格式导出到内存缓冲区，保留原声的丰富细节
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")
    b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # MIMO 官方规范：附带格式前缀
    return f"data:audio/wav;base64,{b64_str}"


def concatenate_and_save_audio(audio_bytes_list: list[bytes], output_path: str | os.PathLike):
    """将多个 WAV 音频的二进制数据无缝拼接并保存为一个长音频。

    优化点：
      - 避免使用 AudioSegment 的 `+=` 循环拼接（O(n²) 复杂度）；
      - 改为直接拼接各片段的 raw_data 后一次性构造 AudioSegment（O(n)）。
    """
    if not audio_bytes_list:
        print("警告：没有可拼接的音频片段。")
        return

    segments = [
        AudioSegment.from_file(io.BytesIO(data), format="wav")
        for data in audio_bytes_list
    ]

    first = segments[0]
    normalized_segments = []
    for seg in segments:
        # 统一音频参数，确保 raw_data 可以直接拼接
        if (seg.frame_rate != first.frame_rate
                or seg.channels != first.channels
                or seg.sample_width != first.sample_width):
            seg = (seg.set_frame_rate(first.frame_rate)
                     .set_channels(first.channels)
                     .set_sample_width(first.sample_width))
        normalized_segments.append(seg)

    # O(n) 直接拼接原始音频字节，避免反复构造 AudioSegment
    combined_data = b"".join(seg.raw_data for seg in normalized_segments)
    combined_audio = AudioSegment(
        data=combined_data,
        sample_width=first.sample_width,
        frame_rate=first.frame_rate,
        channels=first.channels
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined_audio.export(str(out_path), format="wav")
    print(f"✅ 长音频无缝拼接完成，成功保存至：{out_path}")
