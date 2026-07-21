from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess

from src.config import WHISPER_CPU_THREADS, WHISPER_MODEL_NAME


class SpeechToTextProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> dict:
        """Return at least {'text': str}; providers may add language/timing metadata."""


class FasterWhisperProvider(SpeechToTextProvider):
    def __init__(self, model_name: str = WHISPER_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "Audio transcription is not installed. Install faster-whisper or submit a transcript."
                ) from exc
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
                cpu_threads=WHISPER_CPU_THREADS,
            )
        return self._model

    def transcribe(self, audio_path: str) -> dict:
        model = self._get_model()
        segments, info = model.transcribe(
            str(Path(audio_path)),
            vad_filter=True,
            word_timestamps=True,
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
        )
        items = [
            {"start": round(segment.start, 2), "end": round(segment.end, 2), "text": segment.text.strip()}
            for segment in segments
        ]
        return {
            "text": " ".join(segment["text"] for segment in items).strip(),
            "language": info.language,
            "segments": items,
        }


def normalize_audio(audio_path: str) -> str:
    """Normalize to mono 16 kHz WAV when FFmpeg is available."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return audio_path
    source = Path(audio_path)
    target = source.with_name(f"{source.stem}-normalized.wav")
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(source), "-ac", "1", "-ar", "16000", str(target)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError("Audio normalization failed. The recording may be invalid or corrupted.")
    return str(target)


@lru_cache(maxsize=1)
def get_speech_provider() -> SpeechToTextProvider:
    return FasterWhisperProvider()
