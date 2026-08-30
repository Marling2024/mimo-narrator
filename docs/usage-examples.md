根据小米 MiMo 官方文档，MiMo-V2.5-TTS 系列共包含三种模型。以下是使用 Python 代码（通过 OpenAI SDK）调用这三种模型的详细信息与代码示例，已整理为规范的 Markdown 格式：

## 通用准备工作与注意事项
1. **依赖环境**：调用依赖于 `openai` SDK，流式调用中还会用到 `numpy` 和 `soundfile` 进行音频数据的处理与保存。
2. **API 基础配置**：统一通过 `https://api.xiaomimimo.com/v1` 作为 `base_url` 进行调用，并需要配置 `MIMO_API_KEY`。
3. **消息角色传递**：
   - 目标语音生成的文本必须填写在 `role: "assistant"` 的 `content` 中。
   - `role: "user"` 可选（`voicedesign` 模型为必填），用于传入自然语言指令控制语气和风格，或用于描述定制的音色。
4. **输出格式**：非流式调用通常指定 `wav` 格式，流式调用请指定为 `pcm16` 格式以便于拼接。

---

## 1. 预置音色模型 (`mimo-v2.5-tts`)
**功能说明**：内置多种精品音色（如 `Chloe`, `Mia`, `冰糖` 等），开箱即用。当前模型支持低延迟的流式和非流式调用。

### 1.1 非流式调用
```python
import os
from openai import OpenAI
import base64

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts",
    messages=[
        {
            "role": "user",
            "content": "Bright, bouncy, slightly sing-song tone — like you're bursting with good news you can barely hold in. Fast pace, rising pitch at the end."
        },
        {
            "role": "assistant",
            "content": "Hey boss — guess what, guess what? I just got the results back and I actually passed! Not just passed, I got a distinction! I know, I know — you told me I was cutting it close, but hey, here we are. Drinks are on me tonight, okay?"
        }
    ],
    audio={
        "format": "wav",
        "voice": "Chloe"
    }
)

message = completion.choices[0].message
audio_bytes = base64.b64decode(message.audio.data)

with open("audio_file.wav", "wb") as f:
    f.write(audio_bytes)
```

### 1.2 流式调用
```python
import base64
import os
import numpy as np
import soundfile as sf
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts",
    messages=[
        {
            "role": "user",
            "content": "Bright, bouncy, slightly sing-song tone — like you're bursting with good news you can barely hold in. Fast pace, rising pitch at the end."
        },
        {
            "role": "assistant",
            "content": "Hey boss — guess what, guess what? I just got the results back and I actually passed! Not just passed, I got a distinction! I know, I know — you told me I was cutting it close, but hey, here we are. Drinks are on me tonight, okay?"
        }
    ],
    audio={
        "format": "pcm16",
        "voice": "Chloe"
    },
    stream=True
)

# 24kHz PCM16LE mono audio
collected_chunks: np.ndarray = np.array([], dtype=np.float32)

for chunk in completion:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    audio = getattr(delta, "audio", None)
    if audio is not None:
        assert isinstance(audio, dict), f"Expected audio to be a dict, got {type(audio)}"
        pcm_bytes = base64.b64decode(audio["data"])
        np_pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        collected_chunks = np.concatenate((collected_chunks, np_pcm))
        print(f"Received audio chunk of size {len(pcm_bytes)} bytes")

# Save the collected audio to a file
os.makedirs("tmp", exist_ok=True)
sf.write("tmp/output.wav", collected_chunks, samplerate=24000)
print("Audio saved to tmp/output.wav")
```

---

## 2. 文本设计音色模型 (`mimo-v2.5-tts-voicedesign`)
**功能说明**：无需提供音频文件，只需在角色为 `user` 的消息中添加音色描述文本，即可生成定制化音色。支持参数 `optimize_text_preview=True` 让系统智能润色目标播报文本。
**注意**：低延迟流式输出功能暂未上线，目前降级为**兼容模式**，仅在所有推理完成后以流式格式返回一次结果。

### 2.1 非流式调用
```python
import os
from openai import OpenAI
import base64

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts-voicedesign",
    messages=[
        {
            "role": "user",
            "content": "Give me a young male tone."
        },
        {
            "role": "assistant",
            "content": "Yes, I had a sandwich."
        }
    ],
    audio={
        "format": "wav",
        "optimize_text_preview": True
    }
)

message = completion.choices[0].message
audio_bytes = base64.b64decode(message.audio.data)

with open("audio_file.wav", "wb") as f:
    f.write(audio_bytes)
```

### 2.2 流式调用 (兼容模式)
```python
import base64
import os
import numpy as np
import soundfile as sf
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts-voicedesign",
    messages=[
        {
            "role": "user",
            "content": "Give me a young male tone."
        },
        {
            "role": "assistant",
            "content": "You are UN-BE-LIEVABLE! I am sooooo done with your constant lies. GET. OUT!"
        }
    ],
    audio={
        "format": "pcm16",
        "optimize_text_preview": True
    },
    stream=True
)

# 24kHz PCM16LE mono audio
collected_chunks: np.ndarray = np.array([], dtype=np.float32)

for chunk in completion:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    audio = getattr(delta, "audio", None)
    if audio is not None:
        assert isinstance(audio, dict), f"Expected audio to be a dict, got {type(audio)}"
        pcm_bytes = base64.b64decode(audio["data"])
        np_pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        collected_chunks = np.concatenate((collected_chunks, np_pcm))
        print(f"Received audio chunk of size {len(pcm_bytes)} bytes")

# Save the collected audio to a file
os.makedirs("tmp", exist_ok=True)
sf.write("tmp/output.wav", collected_chunks, samplerate=24000)
print("Audio saved to tmp/output.wav")
```

---

## 3. 音色复刻模型 (`mimo-v2.5-tts-voiceclone`)
**功能说明**：通过传入本地音频样本，精准复刻目标音色并生成语音。
**注意**：
- 音频大小不可超过 10 MB，支持 `.mp3` 和 `.wav` 格式。
- 音频需要转换为 Base64 字符串，并携带格式前缀：`data:{MIME_TYPE};base64,$BASE64_AUDIO`，例如 `data:audio/mpeg;base64,...`。

### 3.1 非流式调用
```python
import base64
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1",
)

# 读取本地作为克隆参考的音频文件
with open("voice.mp3", "rb") as f:
    voice_bytes = f.read()

# 转换为 Base64 编码
voice_base64 = base64.b64encode(voice_bytes).decode("utf-8")

completion = client.chat.completions.create(
    model="mimo-v2.5-tts-voiceclone",
    messages=[
        {
            "role": "user",
            "content": ""
        },
        {
            "role": "assistant",
            "content": "Yes, I had a sandwich."
        }
    ],
    audio={
        "format": "wav",
        # 此处的格式为 mp3 所以使用 audio/mpeg
        "voice": f"data:audio/mpeg;base64,{voice_base64}"
    }
)

message = completion.choices[0].message
audio_bytes = base64.b64decode(message.audio.data)

with open("audio_file.wav", "wb") as f:
    f.write(audio_bytes)
```