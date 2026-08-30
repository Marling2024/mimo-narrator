好，这份是 MiMo TTS（语音合成）**API 参考文档**，比上一轮那份《使用指南》更偏工程侧。给你整理成一份可直接用的 Markdown 笔记👇

---

# MiMo TTS 语音合成 API 笔记

> 文档地址：https://mimo.mi.com/docs/zh-CN/api/audio/tts
> 更新时间：2026-07-17｜接口兼容 OpenAI Chat Completion 格式

## 📌 前置提醒

- **MiMo-V2 系列已于 2026-06-30 下线**，模型名已失效，需切到 V2.5 系列。
- 请求端点复用 Chat Completion：`POST https://api.xiaomimimo.com/v1/chat/completions`

---

## 请求

### 请求头（二选一鉴权）

| Header | 值 |
|---|---|
| `api-key` | `$MIMO_API_KEY`（API Key 鉴权）|
| `Authorization` | `Bearer $MIMO_API_KEY`（Bearer 鉴权）|
| `Content-Type` | `application/json` |

### 请求体关键字段

| 字段 | 类型 | 必选 | 说明 |
|---|---|---|---|
| `model` | string | ✅ | `mimo-v2.5-tts` / `voicedesign` / `voiceclone` |
| `messages` | array | ✅ | user（风格/描述）+ assistant（合成文本）|
| `audio` | object | ✅（输出音频时）| 见下方 |
| `stream` | boolean | 默认 `false` | `true` 时 SSE 流式返回，audio.format 强制 pcm |

#### `audio` 对象

| 字段 | 默认值 | 说明 |
|---|---|---|
| `format` | `wav` | `wav` / `mp3` / `pcm`(=pcm16)；stream=true 时强制 pcm |
| `voice` | — | 三模型行为不同，见下表 |
| `optimize_text_preview` | `false` | 开启后智能润色播报文本；voicedesign 模型下可省 assistant message |

#### `voice` 字段按模型差异

| 模型 | voice 是否必填 | 取值说明 |
|---|---|---|
| `mimo-v2.5-tts` | 可选，默认 `mimo_default` | 仅预置音色：`mimo_default` / 冰糖 / 茉莉 / 苏打 / 白桦 / Mia / Chloe / Milo / Dean |
| `mimo-v2.5-tts-voicedesign` | ❌ 不支持此字段 | 音色由 user message 的自然语言描述决定 |
| `mimo-v2.5-tts-voiceclone` | ✅ 必填 | 仅接受**参考音频的 base64**（mp3 / wav，≤10MB）|

#### messages 约定

- **合成文本必须放在 `role: assistant` 的 message** 里
- `role: user` 在 voicedesign 模型下为必填，用作音色描述文本
- voicedesign + `optimize_text_preview: true` 时可省略 assistant

---

## 响应

### 非流式（`chat.completion`）

```json
{
  "id": "6ebed286b58546f6b87fa7fa9d0e806b",
  "choices": [{
    "finish_reason": "stop",
    "index": 0,
    "message": {
      "content": "",
      "role": "assistant",
      "audio": {
        "id": "979a91904f9a4143928d9e1f54837b4f",
        "data": "base64Data",
        "expires_at": null,
        "transcript": null
      }
    }
  }],
  "created": 1776954802,
  "model": "mimo-v2.5-tts",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 97,
    "prompt_tokens": 213,
    "total_tokens": 310,
    "completion_tokens_details": { "reasoning_tokens": 0 },
    "prompt_tokens_details": { "cached_tokens": 109 }
  }
}
```

#### `finish_reason` 取值

| 值 | 含义 |
|---|---|
| `stop` | 自然结束 / 命中停止序列 |
| `length` | **超出模型最大生成长度** → 呼应你上轮问的字数限制，本文档仍未给死数，但靠这个字段可反推 |
| `content_filter` | 触发内容过滤被拦截 |

#### `usage` 关键项

- `prompt_tokens` / `completion_tokens` / `total_tokens`
- `final_text_preview`：仅 `optimize_text_preview=true` 时返回，即**实际送入模型合成的最终文本**（已被智能润色过）

### 流式（`chat.completion.chunk`，SSE）

结构与非流式对齐，差异点：

- `choices.delta` 替代 `choices.message`，增量返回
- `choices.delta.audio.data` 逐块吐 base64 音频
- 每个 chunk 共享同一 `id` / `created`

---

## 调用示例（curl）

```bash
curl --location --request POST 'https://api.xiaomimimo.com/v1/chat/completions' \
  --header "api-key: $MIMO_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "model": "mimo-v2.5-tts",
    "messages": [
      {
        "role": "user",
        "content": "Bright, bouncy, slightly sing-song tone — like you are bursting with good news..."
      },
      {
        "role": "assistant",
        "content": "Hey boss — guess what, guess what? I just got the results back and I actually passed! ..."
      }
    ],
    "audio": {
      "format": "wav",
      "voice": "mimo_default"
    }
  }'
```

---

## 几个容易踩的点

1. **三个模型不是简单换 ID**——voiceclone 要 base64 参考音频、voicedesign 不要 voice 字段但要 user message，调错直接 4xx。
2. **stream + format 有强绑定**：stream=true 时 format 会被忽略，实际出 pcm16。
3. **字数/长度限制本文档仍没写死数**，但 `finish_reason: "length"` 的存在说明服务端有 max，超出会截断，生产里建议每次查 `finish_reason`。
4. `optimize_text_preview: true` 在 voicedesign 下可以省掉 assistant message，相当于"描述音色 → 自动生成播报稿 → 合成"一条龙。