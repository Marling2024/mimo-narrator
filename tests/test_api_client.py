"""
测试 api_client 模块。

覆盖场景：
  - 三种模式的构造函数（模型映射）
  - 无效模式抛异常
  - _build_messages：voice_design 模式下音色描述进入 user 消息
  - _build_audio_params：voice_design 模式下不传 voice 字段
  - synthesize mock 测试（preset / voice_clone）
  - voice_design 的 optimize_text 控制
"""
import base64
from unittest.mock import patch, MagicMock

import pytest

from utils.api_client import MimoTTS, _MODEL_MAP


# ── 模型映射 ──────────────────────────────────────────────
def test_model_map():
    assert _MODEL_MAP["preset"] == "mimo-v2.5-tts"
    assert _MODEL_MAP["voice_design"] == "mimo-v2.5-tts-voicedesign"
    assert _MODEL_MAP["voice_clone"] == "mimo-v2.5-tts-voiceclone"


# ── 构造函数 ──────────────────────────────────────────────
def test_constructor_preset():
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    assert tts.model == "mimo-v2.5-tts"


def test_constructor_voice_design():
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_design")
    assert tts.model == "mimo-v2.5-tts-voicedesign"


def test_constructor_voice_clone():
    tts = MimoTTS(api_key="fk", base_url="https://x")
    assert tts.model == "mimo-v2.5-tts-voiceclone"


def test_constructor_invalid_mode():
    with pytest.raises(ValueError):
        MimoTTS(api_key="fk", base_url="https://x", tts_mode="invalid")


# ── _build_messages ───────────────────────────────────────
def test_build_messages_preset():
    """预设模式下 user=风格指令, assistant=文本"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    msgs = tts._build_messages("你好。", "开心地说", "冰糖")
    assert msgs[0] == {"role": "user", "content": "开心地说"}
    assert msgs[1] == {"role": "assistant", "content": "你好。"}


def test_build_messages_preset_no_style():
    """预设模式下无风格指令时只有 assistant"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    msgs = tts._build_messages("你好。", "", "冰糖")
    assert len(msgs) == 1
    assert msgs[0] == {"role": "assistant", "content": "你好。"}


def test_build_messages_voice_design():
    """voice_design 模式下 user 消息融合音色描述 + 风格指令"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_design")
    msgs = tts._build_messages("你好。", "开心地说", "甜美的少女音色")
    assert msgs[0]["role"] == "user"
    assert "甜美的少女音色" in msgs[0]["content"]
    assert "开心地说" in msgs[0]["content"]
    assert msgs[1] == {"role": "assistant", "content": "你好。"}


def test_build_messages_voice_design_no_style():
    """voice_design 模式下无风格指令时 user 仅含音色描述"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_design")
    msgs = tts._build_messages("你好。", "", "甜美的少女音色")
    assert msgs[0] == {"role": "user", "content": "甜美的少女音色"}
    assert msgs[1] == {"role": "assistant", "content": "你好。"}


def test_build_messages_voice_clone():
    """克隆模式下 user 可选，assistant=文本"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_clone")
    msgs = tts._build_messages("Yes.", "风格指令", "data:audio/wav;base64,AAAA")
    assert msgs[0] == {"role": "user", "content": "风格指令"}
    assert msgs[1] == {"role": "assistant", "content": "Yes."}


# ── _build_audio_params ───────────────────────────────────
def test_audio_params_preset():
    """预设模式：voice=音色名"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    params = tts._build_audio_params("冰糖")
    assert params == {"format": "wav", "voice": "冰糖"}


def test_audio_params_voice_design_with_optimize():
    """voice_design 模式：无 voice 字段，有 optimize_text_preview"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_design")
    params = tts._build_audio_params("甜美的少女音色", optimize_text=True)
    assert "voice" not in params
    assert params["format"] == "wav"
    assert params["optimize_text_preview"] is True


def test_audio_params_voice_design_without_optimize():
    """voice_design 模式关闭 optimize 时不含该字段"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_design")
    params = tts._build_audio_params("甜美的少女音色", optimize_text=False)
    assert "voice" not in params
    assert "optimize_text_preview" not in params


def test_audio_params_voice_clone():
    """克隆模式：voice=data URI"""
    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_clone")
    uri = "data:audio/wav;base64,AAAA"
    params = tts._build_audio_params(uri)
    assert params == {"format": "wav", "voice": uri}


# ── synthesize mock ────────────────────────────────────────
@patch("utils.api_client.OpenAI")
def test_synthesize_preset(mock_openai):
    """预设模式合成：验证 voice 是音色名纯文本"""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.audio.data = base64.b64encode(b"fake-audio").decode()
    mock_client.chat.completions.create.return_value.choices = [mock_choice]
    mock_openai.return_value = mock_client

    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    result = tts.synthesize("你好。", "开心地说", "冰糖")
    assert result == b"fake-audio"

    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["audio"]["voice"] == "冰糖"
    assert call_args["model"] == "mimo-v2.5-tts"


@patch("utils.api_client.OpenAI")
def test_synthesize_voice_design_no_voice_field(mock_openai):
    """voice_design 模式：audio 参数中不含 voice 字段"""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.audio.data = base64.b64encode(b"fake-vd").decode()
    mock_client.chat.completions.create.return_value.choices = [mock_choice]
    mock_openai.return_value = mock_client

    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_design")
    result = tts.synthesize("你好。", "开心地说", "甜美的少女音色")
    assert result == b"fake-vd"

    call_args = mock_client.chat.completions.create.call_args[1]
    assert "voice" not in call_args["audio"]
    assert call_args["audio"]["optimize_text_preview"] is True

    # user 消息中应包含音色描述
    messages = call_args["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "甜美的少女音色" in user_msg["content"]


@patch("utils.api_client.OpenAI")
def test_synthesize_voice_clone(mock_openai):
    """克隆模式合成：验证 voice data URI"""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.audio.data = base64.b64encode(b"fake-clone").decode()
    mock_client.chat.completions.create.return_value.choices = [mock_choice]
    mock_openai.return_value = mock_client

    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="voice_clone")
    voice_uri = "data:audio/wav;base64,AAAA"
    result = tts.synthesize("Yes.", "风格指令", voice_uri)
    assert result == b"fake-clone"

    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["audio"]["voice"] == voice_uri


# ── synthesize 错误处理 ─────────────────────────────────────
@patch("utils.api_client.OpenAI")
def test_synthesize_no_audio_raises_immediately(mock_openai):
    """API 未返回音频时应抛 ValueError，且不触发重试"""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.audio = None
    mock_choice.message.content = "抱歉"
    mock_client.chat.completions.create.return_value.choices = [mock_choice]
    mock_openai.return_value = mock_client

    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    with pytest.raises(ValueError, match="未返回音频"):
        tts.synthesize("你好。", "", "冰糖")
    assert mock_client.chat.completions.create.call_count == 1


@patch("utils.api_client.OpenAI")
def test_auth_error_not_retried(mock_openai):
    """鉴权失败等确定性错误不应重试，只调用一次"""
    from openai import AuthenticationError

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        "bad key", response=MagicMock(), body=None
    )
    mock_openai.return_value = mock_client

    tts = MimoTTS(api_key="fk", base_url="https://x", tts_mode="preset")
    with pytest.raises(AuthenticationError):
        tts.synthesize("你好。", "", "冰糖")
    assert mock_client.chat.completions.create.call_count == 1


if __name__ == "__main__":
    test_model_map()
    test_constructor_preset()
    test_constructor_voice_design()
    test_constructor_voice_clone()
    test_constructor_invalid_mode()
    test_build_messages_preset()
    test_build_messages_preset_no_style()
    test_build_messages_voice_design()
    test_build_messages_voice_design_no_style()
    test_build_messages_voice_clone()
    test_audio_params_preset()
    test_audio_params_voice_design_with_optimize()
    test_audio_params_voice_design_without_optimize()
    test_audio_params_voice_clone()
    test_synthesize_preset()
    test_synthesize_voice_design_no_voice_field()
    test_synthesize_voice_clone()
    test_synthesize_no_audio_raises_immediately()
    test_auth_error_not_retried()
    print("✅ 所有 api_client 测试通过")
