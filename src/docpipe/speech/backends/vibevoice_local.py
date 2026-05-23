"""Local VibeVoice-ASR inference (optional vibevoice install + GPU)."""

from __future__ import annotations

import logging
import threading
from typing import Any

from docpipe.core.errors import ConfigurationError, TranscriptionError
from docpipe.speech.types import TranscribeResult, TranscriptionSegment

logger = logging.getLogger(__name__)

_engine_lock = threading.Lock()
_engine: Any | None = None
_engine_config: tuple[str, str, str] | None = None


def _resolve_device(requested: str) -> str:
    if requested and requested != "auto":
        return requested
    try:
        import torch
    except ImportError as err:
        raise ConfigurationError(
            "VibeVoice local backend requires PyTorch. Install VibeVoice per "
            "https://github.com/microsoft/VibeVoice/blob/main/docs/vibevoice-asr.md"
        ) from err

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    if hasattr(torch.backends, "xpu") and torch.backends.xpu.is_available():
        return "xpu"
    return "cpu"


def _resolve_attn(device: str, requested: str) -> str:
    if requested and requested != "auto":
        return requested
    if device != "cuda":
        return "sdpa"
    try:
        import flash_attn  # noqa: F401

        return "flash_attention_2"
    except ImportError:
        return "sdpa"


def _set_inference_mode(model: Any) -> None:
    set_mode = getattr(model, "eval", None)
    if callable(set_mode):
        set_mode()


def _get_engine(*, model_path: str, device: str, attn_implementation: str) -> Any:
    global _engine, _engine_config
    config_key = (model_path, device, attn_implementation)
    with _engine_lock:
        if _engine is not None and _engine_config == config_key:
            return _engine

        try:
            import torch
            from vibevoice.modular.modeling_vibevoice_asr import (
                VibeVoiceASRForConditionalGeneration,
            )
            from vibevoice.processor.vibevoice_asr_processor import VibeVoiceASRProcessor
        except ImportError as err:
            raise ConfigurationError(
                "VibeVoice is not installed. Clone https://github.com/microsoft/VibeVoice and "
                "run `pip install -e .`, or set DOCPIPE_TRANSCRIBE_BACKEND=openai."
            ) from err

        resolved_device = _resolve_device(device)
        dtype = (
            torch.float32
            if resolved_device in ("mps", "xpu", "cpu")
            else torch.bfloat16
        )

        attn = _resolve_attn(resolved_device, attn_implementation)
        logger.info(
            "Loading VibeVoice ASR | model=%s device=%s attn=%s",
            model_path,
            resolved_device,
            attn,
        )

        processor = VibeVoiceASRProcessor.from_pretrained(
            model_path,
            language_model_pretrained_name="Qwen/Qwen2.5-7B",
        )
        model = VibeVoiceASRForConditionalGeneration.from_pretrained(
            model_path,
            dtype=dtype,
            device_map=resolved_device if resolved_device == "auto" else None,
            attn_implementation=attn,
            trust_remote_code=True,
        )
        if resolved_device != "auto":
            model = model.to(resolved_device)
        _set_inference_mode(model)

        class _Engine:
            def __init__(self) -> None:
                self.processor = processor
                self.model = model
                self.device = resolved_device if resolved_device != "auto" else next(
                    model.parameters()
                ).device

            def transcribe(
                self,
                audio_path: str,
                *,
                context_info: str | None,
                max_new_tokens: int,
            ) -> dict[str, Any]:
                inputs = self.processor(
                    audio=audio_path,
                    sampling_rate=None,
                    return_tensors="pt",
                    padding=True,
                    add_generation_prompt=True,
                    context_info=context_info,
                )
                inputs = {
                    key: value.to(self.device) if hasattr(value, "to") else value
                    for key, value in inputs.items()
                }
                input_length = inputs["input_ids"].shape[1]
                gen_kwargs = {
                    "max_new_tokens": max_new_tokens,
                    "pad_token_id": self.processor.pad_id,
                    "eos_token_id": self.processor.tokenizer.eos_token_id,
                    "do_sample": False,
                }
                import torch

                with torch.no_grad():
                    output_ids = self.model.generate(**inputs, **gen_kwargs)

                generated_ids = output_ids[0, input_length:]
                eos_positions = (
                    generated_ids == self.processor.tokenizer.eos_token_id
                ).nonzero(as_tuple=True)[0]
                if len(eos_positions) > 0:
                    generated_ids = generated_ids[: eos_positions[0] + 1]

                raw_text = self.processor.decode(generated_ids, skip_special_tokens=True)
                try:
                    segments = self.processor.post_process_transcription(raw_text)
                except Exception as parse_err:
                    logger.warning("VibeVoice segment parse failed: %s", parse_err)
                    segments = []

                return {"raw_text": raw_text, "segments": segments}

        _engine = _Engine()
        _engine_config = config_key
        return _engine


def _plain_text_from_segments(segments: list[dict[str, Any]], raw_text: str) -> str:
    if not segments:
        return raw_text.strip()
    parts = [str(seg.get("text", "")).strip() for seg in segments if seg.get("text")]
    return " ".join(part for part in parts if part).strip() or raw_text.strip()


def transcribe_file(
    audio_path: str,
    *,
    model_path: str,
    device: str = "auto",
    attn_implementation: str = "auto",
    hotwords: list[str] | None = None,
    max_new_tokens: int = 8192,
) -> TranscribeResult:
    context_info = ", ".join(hotwords) if hotwords else None
    engine = _get_engine(
        model_path=model_path,
        device=device,
        attn_implementation=attn_implementation,
    )
    try:
        payload = engine.transcribe(
            audio_path,
            context_info=context_info,
            max_new_tokens=max_new_tokens,
        )
    except Exception as exc:
        raise TranscriptionError(f"VibeVoice transcription failed: {exc}") from exc

    raw_text = str(payload.get("raw_text", ""))
    segments_raw = payload.get("segments") or []
    segments = [
        TranscriptionSegment(
            start_time=seg.get("start_time"),
            end_time=seg.get("end_time"),
            speaker_id=seg.get("speaker_id"),
            text=str(seg.get("text", "")),
        )
        for seg in segments_raw
        if isinstance(seg, dict)
    ]
    text = _plain_text_from_segments(segments_raw, raw_text)
    return TranscribeResult(
        text=text,
        backend="vibevoice",
        raw_text=raw_text,
        segments=segments,
        metadata={"model_path": model_path},
    )
