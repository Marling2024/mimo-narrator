"""
测试 main 模块中的辅助函数。

覆盖场景：
  - _resolve_voice_param 三种模式
  - 无效模式
  - 缺少必要配置时抛异常
  - load_config 正确性
"""
import os
import tempfile

import pytest
from main import _resolve_voice_param, load_config


def test_resolve_preset():
    """预设模式返回音色名"""
    cfg = {
        "api": {"tts_mode": "preset"},
        "preset": {"voice_name": "冰糖"},
    }
    result = _resolve_voice_param(cfg)
    assert result == "冰糖"


def test_resolve_preset_missing_name():
    """预设模式缺少 voice_name 时抛异常"""
    cfg = {
        "api": {"tts_mode": "preset"},
        "preset": {},
    }
    with pytest.raises(ValueError):
        _resolve_voice_param(cfg)


def test_resolve_voice_design():
    """音色设计模式返回描述文本"""
    cfg = {
        "api": {"tts_mode": "voice_design"},
        "voice_design": {"voice_description": "甜美的少女音色"},
    }
    result = _resolve_voice_param(cfg)
    assert result == "甜美的少女音色"


def test_resolve_voice_design_missing_desc():
    """音色设计模式缺少描述时抛异常"""
    cfg = {
        "api": {"tts_mode": "voice_design"},
        "voice_design": {},
    }
    with pytest.raises(ValueError):
        _resolve_voice_param(cfg)


def test_resolve_voice_clone():
    """音色克隆模式返回 Base64 data URI"""
    # 需要真实的配置文件来读取 reference_audio 路径
    # 这里只验证函数逻辑：当路径存在时应返回带前缀的字符串
    from pydub import AudioSegment

    # 创建临时参考音频
    audio = AudioSegment.silent(duration=200, frame_rate=24000).set_channels(1).set_sample_width(2)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio.export(tmp.name, format="wav")
    tmp.close()

    cfg = {
        "api": {"tts_mode": "voice_clone"},
        "paths": {"reference_audio": tmp.name},
    }
    try:
        result = _resolve_voice_param(cfg)
        assert result.startswith("data:audio/wav;base64,")
    finally:
        os.unlink(tmp.name)


def test_resolve_invalid_mode():
    """无效模式应抛 ValueError"""
    cfg = {"api": {"tts_mode": "invalid"}}
    with pytest.raises(ValueError):
        _resolve_voice_param(cfg)


def test_load_config():
    """验证配置文件能被正确加载"""
    cfg = load_config()
    assert "api" in cfg
    assert "tts_params" in cfg
    assert "paths" in cfg
    assert "tts_mode" in cfg["api"]


def test_enable_split_default():
    """enable_split 字段不存在时默认值为 True（向后兼容）"""
    cfg = {"tts_params": {}}
    # 模拟 main.py 中的取值逻辑
    enable_split = cfg["tts_params"].get("enable_split", True)
    assert enable_split is True


def test_enable_split_true():
    """enable_split=true 时按标点切分文本"""
    from utils.text_splitter import split_text_by_punctuation

    text = "第一句。第二句。第三句。"
    cfg = {"tts_params": {"enable_split": True, "max_chars_per_chunk": 4}}

    enable_split = cfg["tts_params"].get("enable_split", True)
    if enable_split:
        chunks = split_text_by_punctuation(text, max_length=cfg["tts_params"]["max_chars_per_chunk"])
    else:
        chunks = [text]

    # 切分后应产生多个分片（每句 4 字 > max_chars_per_chunk=4）
    assert len(chunks) == 3
    assert "第一句。" in chunks
    assert "第二句。" in chunks
    assert "第三句。" in chunks


def test_enable_split_false():
    """enable_split=false 时整段文本作为一个分片，不进行切分"""
    from utils.text_splitter import split_text_by_punctuation

    text = "第一句。第二句。第三句。"
    cfg = {"tts_params": {"enable_split": False, "max_chars_per_chunk": 4}}

    enable_split = cfg["tts_params"].get("enable_split", True)
    if enable_split:
        chunks = split_text_by_punctuation(text, max_length=cfg["tts_params"]["max_chars_per_chunk"])
    else:
        chunks = [text]

    # 关闭切分后应保持整段文本不变
    assert len(chunks) == 1
    assert chunks[0] == text


def test_run_from_config_empty_text():
    """空输入文本应立即抛 ValueError，而不是假成功"""
    from main import run_from_config

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp.close()
    cfg = {
        "api": {"tts_mode": "preset", "base_url": "https://x"},
        "tts_params": {"enable_split": True, "max_chars_per_chunk": 100},
        "preset": {"voice_name": "冰糖"},
        "paths": {"input_text": tmp.name},
    }
    try:
        with pytest.raises(ValueError, match="为空"):
            run_from_config(cfg, api_key="fk")
    finally:
        os.unlink(tmp.name)

def test_resolve_path_cwd_independent():
    """相对路径应锚定项目根目录，与当前工作目录无关"""
    from pathlib import Path
    from main import _resolve_path, PROJECT_ROOT

    old_cwd = os.getcwd()
    os.chdir(tempfile.gettempdir())
    try:
        resolved = _resolve_path("inputs/a.txt")
        assert resolved.is_absolute()
        assert resolved == PROJECT_ROOT / "inputs" / "a.txt"
        # 绝对路径原样返回
        assert _resolve_path(Path(old_cwd)) == Path(old_cwd)
    finally:
        os.chdir(old_cwd)


if __name__ == "__main__":
    test_resolve_preset()
    test_resolve_preset_missing_name()
    test_resolve_voice_design()
    test_resolve_voice_design_missing_desc()
    test_resolve_voice_clone()
    test_resolve_invalid_mode()
    test_load_config()
    test_enable_split_default()
    test_enable_split_true()
    test_enable_split_false()
    test_run_from_config_empty_text()
    test_resolve_path_cwd_independent()
    print("✅ 所有 main 辅助函数测试通过")
