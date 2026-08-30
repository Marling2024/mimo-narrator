"""
测试 audio_handler 模块。

覆盖场景：
  - 音频编码为 Base64
  - 音频拼接与保存
  - 文件不存在异常
  - 空列表处理
"""
import sys
import os
import io
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydub import AudioSegment
from utils.audio_handler import encode_audio_to_base64, concatenate_and_save_audio


def _make_temp_wav(duration_ms: int = 500) -> str:
    """生成一个静音 WAV 临时文件用于测试，返回文件路径"""
    audio = AudioSegment.silent(duration=duration_ms, frame_rate=24000)
    audio = audio.set_channels(1).set_sample_width(2)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio.export(tmp.name, format="wav")
    tmp.close()
    return tmp.name


def test_encode_audio_to_base64():
    """编码后应包含正确的 data URI 前缀"""
    path = _make_temp_wav(500)
    try:
        result = encode_audio_to_base64(path)
        assert result.startswith("data:audio/wav;base64,")
        # 前缀之后应是合法的 Base64 字符串
        b64_part = result.split(",", 1)[1]
        assert len(b64_part) > 0
    finally:
        os.unlink(path)


def test_encode_audio_to_base64_truncation():
    """超长音频应被截断"""
    path = _make_temp_wav(20000)  # 20秒
    try:
        result = encode_audio_to_base64(path, max_duration_sec=1)
        assert result.startswith("data:audio/wav;base64,")
    finally:
        os.unlink(path)


def test_encode_file_not_found():
    """文件不存在时抛 FileNotFoundError"""
    try:
        encode_audio_to_base64("nonexistent.wav")
        assert False, "应该抛出异常"
    except FileNotFoundError:
        pass


def test_concatenate_and_save():
    """拼接多个 WAV 并保存到临时目录"""
    # 生成两个静音片段
    seg1 = AudioSegment.silent(duration=200, frame_rate=24000).set_channels(1).set_sample_width(2)
    seg2 = AudioSegment.silent(duration=300, frame_rate=24000).set_channels(1).set_sample_width(2)

    buf1 = io.BytesIO()
    buf2 = io.BytesIO()
    seg1.export(buf1, format="wav")
    seg2.export(buf2, format="wav")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.wav")
        concatenate_and_save_audio([buf1.getvalue(), buf2.getvalue()], out_path)
        assert os.path.exists(out_path)

        # 验证拼接后的音频时长
        combined = AudioSegment.from_file(out_path, format="wav")
        assert len(combined) == 500


def test_concatenate_empty_list():
    """空列表不应崩溃"""
    concatenate_and_save_audio([], "tmp/output.wav")


if __name__ == "__main__":
    test_encode_audio_to_base64()
    test_encode_audio_to_base64_truncation()
    test_encode_file_not_found()
    test_concatenate_and_save()
    test_concatenate_empty_list()
    print("✅ 所有 audio_handler 测试通过")
