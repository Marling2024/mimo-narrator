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
        gr.Markdown("# MIMO TTS \u00b7 \u6781\u7b80\u63a7\u5236\u53f0")

        with gr.Row():
            mode = gr.Dropdown(
                choices=[("\u9884\u7f6e\u97f3\u8272", "preset"), ("\u97f3\u8272\u8bbe\u8ba1", "voice_design"), ("\u97f3\u8272\u514b\u9686", "voice_clone")],
                value="preset",
                label="\u5408\u6210\u6a21\u5f0f",
            )

        # \u52a8\u6001\u53c2\u6570\u533a
        with gr.Column():
            preset_voice = gr.Textbox(
                label="\u9884\u7f6e\u97f3\u8272\u540d\u79f0",
                value="\u51b0\u7cd6",
                visible=True,
            )
            voice_desc = gr.Textbox(
                label="\u97f3\u8272\u63cf\u8ff0",
                placeholder="\u7528\u4e00\u6bb5\u8bdd\u63cf\u8ff0\u4f60\u60f3\u8981\u7684\u97f3\u8272...",
                lines=3,
                visible=False,
            )
            optimize_text = gr.Checkbox(
                label="\u542f\u7528\u667a\u80fd\u6da6\u8272",
                value=True,
                visible=False,
            )
            reference_audio = gr.Audio(
                label="\u53c2\u8003\u97f3\u9891",
                type="filepath",
                visible=False,
            )

        text_input = gr.Textbox(
            label="\u8f93\u5165\u6587\u672c",
            value=_load_default_text(),
            lines=8,
            placeholder="\u5728\u6b64\u8f93\u5165\u6216\u7f16\u8f91\u9700\u8981\u5408\u6210\u7684\u6587\u672c...",
        )

        style_input = gr.Textbox(
            label="\u98ce\u683c\u6307\u4ee4\uff08\u53ef\u9009\uff09",
            placeholder="\u4f8b\u5982\uff1a\u660e\u4eae\u6e05\u751c\u7684\u5fae\u7b11\u97f3...",
            lines=2,
        )

        with gr.Row():
            enable_split = gr.Checkbox(label="\u6309\u6807\u70b9\u5207\u5206\u6587\u672c", value=True)
            max_chars = gr.Slider(label="\u6bcf\u7247\u6700\u5927\u5b57\u7b26\u6570", minimum=50, maximum=500, step=10, value=150)

        output_path = gr.Textbox(
            label="\u8f93\u51fa\u97f3\u9891\u8def\u5f84",
            value=str(OUTPUT_FILE),
        )

        submit_btn = gr.Button("\u25b6 \u5f00\u59cb\u5408\u6210", variant="primary")

        status_box = gr.Textbox(
            label="\u72b6\u6001",
            value="\u51c6\u5907\u5c31\u7eea",
            lines=6,
            interactive=False,
        )

        output_audio = gr.Audio(label="\u8f93\u51fa\u97f3\u9891", type="filepath")

        # \u4ea4\u4e92\u903b辑
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
