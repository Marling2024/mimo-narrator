"""
测试 text_splitter 模块。

覆盖场景：
  - 正常切分
  - 空文本
  - 单句超长
  - 边界值
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_splitter import split_text_by_punctuation


def test_empty_text():
    """空文本应返回空列表"""
    assert split_text_by_punctuation("") == []
    assert split_text_by_punctuation("   ") == []


def test_single_sentence():
    """单句短文本应返回包含自身的列表"""
    result = split_text_by_punctuation("你好世界。", max_length=100)
    assert result == ["你好世界。"]


def test_multiple_sentences_within_limit():
    """多个短句不超过 max_length 时合并为一个分片"""
    text = "第一句。第二句。第三句。"
    result = split_text_by_punctuation(text, max_length=100)
    assert result == [text]


def test_split_at_limit():
    """超过 max_length 时正确切分"""
    text = "A" * 5 + "。" + "B" * 5 + "。"
    result = split_text_by_punctuation(text, max_length=6)
    assert len(result) == 2
    assert all(len(chunk) <= 6 for chunk in result)


def test_single_sentence_too_long():
    """单句超长时强制截断"""
    long_sentence = "A" * 100 + "。"
    result = split_text_by_punctuation(long_sentence, max_length=50)
    assert len(result) == 1
    assert len(result[0]) == 50


def test_mixed_punctuation():
    """混合中英文标点的切分"""
    text = "Hello!你好吗？Fine."
    result = split_text_by_punctuation(text, max_length=50)
    assert len(result) >= 1


def test_whitespace_only_sentences():
    """包含空句子（纯空格）的文本"""
    text = "第一句。   \n第二句。"
    result = split_text_by_punctuation(text, max_length=50)
    assert len(result) == 1
    assert "第一句" in result[0]
    assert "第二句" in result[0]


def test_preserve_punctuation():
    """验证标点符号被保留"""
    text = "测试。"
    result = split_text_by_punctuation(text, max_length=50)
    assert result[0].endswith("。")


if __name__ == "__main__":
    test_empty_text()
    test_single_sentence()
    test_multiple_sentences_within_limit()
    test_split_at_limit()
    test_single_sentence_too_long()
    test_mixed_punctuation()
    test_whitespace_only_sentences()
    test_preserve_punctuation()
    print("✅ 所有 text_splitter 测试通过")
