import re

def split_text_by_punctuation(text: str, max_length: int = 300) -> list:
    """智能文本切片：基于标点符号对大段文本进行拆分"""
    text = text.strip()
    if not text:
        return []

    # 按照句子结束符切分，同时保留标点
    sentences = re.split(r'(?<=[。！？!\?\n])', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 如果单句实在太长，强行截断（罕见极端情况）
            if len(sentence) > max_length:
                current_chunk = sentence[:max_length]
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks