"""
MIMO TTS 极简 Web UI

特点：
  - 三种模式通过下拉选择
  - 参数根据模式动态显示
  - 可在界面内直接编辑输入文本
  - 实时进度条 + 状态日志监控合成过程

用法：
    python web_ui.py
"""
import os
import tempfile
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from main import load_config, run_from_config

PROJECT_ROOT = Path(__file__).parent
INPUT_FILE = PROJECT_ROOT / "inputs" / "web_input.txt"
OUTPUT_FILE = PROJECT_ROOT / "outputs" / "web_output.wav"


def _load_api_key() -> str:
    load_dotenv()
    key = os.environ.get("MIMO_API_KEY", "")
    if not key:
        raise gr.Error("请在 .env 文件中设置 MIMO_API_KEY")
    return key


def _load_default_text() -> str:
    default_path = PROJECT_ROOT / "inputs" / "large_text.txt"
    if default_path.exists():
        return default_path.read_text(encoding="utf-8")
    return ""


def _toggle_mode(mode: str):
    """根据模式切换参数区可见性。"""
    return {
        "preset": (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)),
        "voice_design": (gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)),
        "voice_clone": (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)),
    }[mode]


def _build_cfg(
    mode: str,
    text: str,
    style: str,
    enable_split: bool,
    max_chars: int,
    preset_voice: str,
    voice_desc: str,
    optimize_text: bool,
    reference_path: str | None,
    output_path: str,
) -> dict:
    base_cfg = load_config()

    # 将界面中编辑的文本落盘，供后续流程读取
    INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    INPUT_FILE.write_text(text, encoding="utf-8")

    return {
        "api": {
            "base_url": base_cfg["api"]["base_url"],
            "tts_mode": mode,
        },
        "tts_params": {
            "format": "wav",
            "enable_split": enable_split,
            "max_chars_per_chunk": max_chars,
            "style_instruction": style or "",
        },
        "preset": {"voice_name": preset_voice or ""},
        "voice_design": {
            "voice_description": voice_desc or "",
            "optimize_text_preview": optimize_text,
        },
        "voice_clone": {},
        "paths": {
            "input_text": str(INPUT_FILE),
            "reference_audio": reference_path or "",
            "output_audio": output_path or str(OUTPUT_FILE),
        },
    }


def _synthesize(
    mode: str,
    text: str,
    style: str,
    enable_split: bool,
    max_chars: int,
    preset_voice: str,
    voice_desc: str,
    optimize_text: bool,
    reference_path: str | None,
    output_path: str,
    progress=gr.Progress(track_tqdm=False),
):
    """执行合成并实时返回状态与进度。"""
    api_key = _load_api_key()

    status_lines = ["⚡ 准备配置..."]
    yield "\n".join(status_lines), None

    cfg = _build_cfg(
        mode=mode,
        text=text,
        style=style,
        enable_split=enable_split,
        max_chars=max_chars,
        preset_voice=preset_voice,
        voice_desc=voice_desc,
        optimize_text=optimize_text,
        reference_path=reference_path,
        output_path=output_path,
    )

    status_lines.append(f"📄 当前模式: {mode}")
    yield "\n".join(status_lines), None

    progress(0.1, desc="初始化 TTS 客户端")

    def on_progress(msg: str, current: int | None = None, total: int | None = None):
        # run_from_config 通过结构化回调传入分片进度，无需解析文案
        if current is not None and total:
            progress(0.2 + 0.7 * (current / total), desc=f"合成第 {current}/{total} 片段")
        status_lines.append(msg)

    try:
        output = run_from_config(cfg, api_key, progress_callback=on_progress)
    except Exception as e:
        status_lines.append(f"❌ 合成失败: {e}")
        yield "\n".join(status_lines), None
        return

    progress(1.0, desc="完成")
    status_lines.append(f"✅ 完成: {output}")
    yield "\n".join(status_lines), str(output)


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="MIMO TTS", css=".container { max-width: 720px; margin: 0 auto; }") as demo:
        gr.Markdown("# MIMO TTS · 极简控制台")

        with gr.Row():
            mode = gr.Dropdown(
                choices=[("预置音色", "preset"), ("音色设计", "voice_design"), ("音色克隆", "voice_clone")],
                value="preset",
                label="合成模式",
            )

        # 动态参数区
        with gr.Column():
            preset_voice = gr.Textbox(
                label="预置音色名称",
                value="冰糖",
                visible=True,
            )
            voice_desc = gr.Textbox(
                label="音色描述",
                placeholder="用一段话描述你想要的音色...",
                lines=3,
                visible=False,
            )
            optimize_text = gr.Checkbox(
                label="启用智能润色",
                value=True,
                visible=False,
            )
            reference_audio = gr.Audio(
                label="参考音频",
                type="filepath",
                visible=False,
            )

        text_input = gr.Textbox(
            label="输入文本",
            value=_load_default_text(),
            lines=8,
            placeholder="在此输入或编辑需要合成的文本...",
        )

        style_input = gr.Textbox(
            label="风格指令（可选）",
            placeholder="例如：明亮清甜的微笑音...",
            lines=2,
        )

        with gr.Row():
            enable_split = gr.Checkbox(label="按标点切分文本", value=True)
            max_chars = gr.Slider(label="每片最大字符数", minimum=50, maximum=500, step=10, value=150)

        output_path = gr.Textbox(
            label="输出音频路径",
            value=str(OUTPUT_FILE),
        )

        submit_btn = gr.Button("▶ 开始合成", variant="primary")

        status_box = gr.Textbox(
            label="状态",
            value="准备就绪",
            lines=6,
            interactive=False,
        )

        output_audio = gr.Audio(label="输出音频", type="filepath")

        # 交互逻辑
        mode.change(
            fn=_toggle_mode,
            inputs=mode,
            outputs=[preset_voice, voice_desc, optimize_text, reference_audio],
        )

        submit_btn.click(
            fn=_synthesize,
            inputs=[
                mode, text_input, style_input, enable_split, max_chars,
                preset_voice, voice_desc, optimize_text, reference_audio, output_path,
            ],
            outputs=[status_box, output_audio],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860)
