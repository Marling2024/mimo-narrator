import base64
import io
import os
from pydub import AudioSegment

def encode_audio_to_base64(file_path: str, max_duration_sec: int = 15) -> str:
    """
    读取参考音频，仅做必要的长度截断以满足平台大小要求，
    保留原始音质、采样率和声道，并转为带 data URI 的 Base64。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到参考音频文件: {file_path}")
    
    # 使用 pydub 加载克隆参考母带
    audio = AudioSegment.from_file(file_path)
    
    # 仅做时长限制，通常 10~15 秒的清晰人声足以完美克隆，
    # 截断可以防止文件体积超标（官方限制 < 10MB）或导致请求体过大
    if len(audio) > max_duration_sec * 1000:
        print(f"✂️ 参考音频超过 {max_duration_sec} 秒，自动截取前端有效声纹，保留无损音质...")
        audio = audio[:max_duration_sec * 1000]
        
    # 直接以无损 WAV 格式导出到内存缓冲区，保留原声的丰富细节
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")
    b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # MIMO 官方规范：附带格式前缀
    return f"data:audio/wav;base64,{b64_str}"

def concatenate_and_save_audio(audio_bytes_list: list, output_path: str):
    """将多个WAV音频的二进制数据无缝拼接并保存为一个长音频"""
    if not audio_bytes_list:
        print("警告：没有可拼接的音频片段。")
        return

    combined_audio = AudioSegment.empty()
    for audio_data in audio_bytes_list:
        segment = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
        combined_audio += segment
        
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_audio.export(output_path, format="wav")
    print(f"✅ 长音频无缝拼接完成，成功保存至：{output_path}")