import re


def _split_long_sentence(sentence: str, max_length: int) -> list[str]:
    """对超过 max_length 的长句按字符硬切分，避免丢失内容。"""
    return [sentence[i:i + max_length] for i in range(0, len(sentence), max_length)]


def split_text_by_punctuation(text: str, max_length: int = 300) -> list[str]:
    """智能文本切片：基于标点符号对大段文本进行拆分。

    策略：
      1. 优先按句子结束符切分，保留标点语义完整性；
      2. 在 max_length 范围内尽可能合并短句，减少 API 调用次数；
      3. 遇到超长单句时，再按字符硬切分，避免内容丢失。
    """
    text = text.strip()
    if not text:
        return []

    # 按照句子结束符切分，同时保留标点
    sentences = re.split(r'(?<=[。！？!?\?\n])', text)
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len = 0

    def _flush():
        nonlocal buffer_len
        if buffer:
            chunks.append("".join(buffer))
            buffer.clear()
            buffer_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_len = len(sentence)

        # 单句本身超过限制：先清空当前缓冲区，再对长句硬切分
        if sentence_len > max_length:
            _flush()
            chunks.extend(_split_long_sentence(sentence, max_length))
            continue

        # 当前缓冲区加入该句后会超限，先 flush 再重新累积
        if buffer_len + sentence_len > max_length:
            _flush()

        buffer.append(sentence)
        buffer_len += sentence_len

    _flush()
    return chunks
