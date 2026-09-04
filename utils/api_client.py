import base64
from openai import APIConnectionError, InternalServerError, OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# 三种 TTS 模式各自对应不同的模型端点，
# 集中管理映射关系，避免散落在多处硬编码
_MODEL_MAP = {
    "preset":       "mimo-v2.5-tts",
    "voice_design": "mimo-v2.5-tts-voicedesign",
    "voice_clone":  "mimo-v2.5-tts-voiceclone",
}

class MimoTTS:
    """通用 MIMO TTS 客户端，根据 tts_mode 自动路由到对应模型和 voice 参数格式。"""

    def __init__(self, api_key: str, base_url: str, tts_mode: str = "voice_clone"):
        if tts_mode not in _MODEL_MAP:
            raise ValueError(f"不支持的 TTS 模式: {tts_mode}，可选值: {list(_MODEL_MAP.keys())}")
        self.tts_mode = tts_mode
        self.model = _MODEL_MAP[tts_mode]
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0
        )

    def _build_messages(self, text_chunk: str, style_instruction: str, voice_param: str) -> list[dict]:
        """
        按模式构造 messages 列表。

        voice_design 模式下音色描述必须放在 user 角色消息中（MIMO 官方规范），
        而非 audio.voice 参数；preset 和 voice_clone 则保持
        user → 可选风格指令、assistant → 目标文本的结构。
        """
        messages = []

        if self.tts_mode == "voice_design":
            # voice_design 的 user 消息承载音色描述（必填），
            # 风格指令作为补充信息追加其后，提升合成表现力
            parts = [voice_param]
            if style_instruction:
                parts.append(style_instruction)
            user_content = "。".join(parts)
            messages.append({"role": "user", "content": user_content})
        else:
            if style_instruction:
                messages.append({"role": "user", "content": style_instruction})

        # 目标合成文本必须在 assistant 角色中
        messages.append({"role": "assistant", "content": text_chunk})
        return messages

    def _build_audio_params(self, voice_param: str, optimize_text: bool = True) -> dict:
        """
        按模式构造 audio 参数字典。

        voice_design 不支持 voice 字段，改为传递 optimize_text_preview
        让系统智能润色目标文本后再合成（MIMO 官方推荐用法）。
        """
        params = {"format": "wav"}

        if self.tts_mode == "voice_design":
            # voice_design 模型不接受 voice 字段，音色描述已通过 user 消息传递
            if optimize_text:
                params["optimize_text_preview"] = True
        else:
            # preset: voice = 音色名；voice_clone: voice = data URI
            params["voice"] = voice_param

        return params

    # 只重试瞬时错误（网络/限流/服务端 5xx）；鉴权失败、参数错误、解析失败立即抛出，
    # 否则确定性错误会白等 6 次指数退避（约 2 分钟）才报错
    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, InternalServerError)
        ),
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=4, max=40),
        reraise=True  # 耗尽重试次数后抛出原始异常，便于排查
    )
    def synthesize(
        self,
        text_chunk: str,
        style_instruction: str,
        voice_param: str,
        optimize_text: bool = True
    ) -> bytes:
        """
        调用 MIMO TTS API 合成语音。

        voice_param 含义取决于 tts_mode:
          - preset:       预置音色名（如 "冰糖"）
          - voice_design: 音色文本描述（自动放入 user 消息，不传 audio.voice）
          - voice_clone:  带 data URI 前缀的 Base64 参考音频
        """
        messages = self._build_messages(text_chunk, style_instruction, voice_param)
        audio_params = self._build_audio_params(voice_param, optimize_text)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            audio=audio_params
        )

        message = completion.choices[0].message
        if message.audio is None or not message.audio.data:
            raise ValueError(
                "API 未返回音频数据（可能是文本为空或触发内容审查），"
                f"返回内容: {message.content!r}"
            )
        return base64.b64decode(message.audio.data)
