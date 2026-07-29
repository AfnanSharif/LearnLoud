from __future__ import annotations

import html
import os
import shutil
import struct
import subprocess
import tempfile
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


COQUI_MODELS = {
    "tacotron2": "tts_models/en/ljspeech/tacotron2-DDC",
    "glow-tts": "tts_models/en/ljspeech/glow-tts",
    "yourtts": "tts_models/multilingual/multi-dataset/your_tts",
}
ENGINE_PROFILES = {
    "gtts": {"label": "gTTS", "naturalness": 72.0, "quality": 70.0, "format": ".mp3"},
    "pyttsx3": {"label": "pyttsx3", "naturalness": 58.0, "quality": 60.0, "format": ".wav"},
    "tortoise": {"label": "Tortoise-TTS", "naturalness": 91.0, "quality": 91.0, "format": ".wav"},
    "tacotron2": {"label": "Tacotron 2", "naturalness": 79.0, "quality": 80.0, "format": ".wav"},
    "glow-tts": {"label": "Glow-TTS", "naturalness": 81.0, "quality": 82.0, "format": ".wav"},
    "yourtts": {"label": "YourTTS", "naturalness": 87.0, "quality": 86.0, "format": ".wav"},
}
TONE_FILTERS = {
    "neutral": "",
    "warm": "bass=g=3,treble=g=-1",
    "bright": "treble=g=3",
    "calm": "lowpass=f=8000,volume=0.95",
}


@dataclass(frozen=True)
class SpeechControls:
    """Provider-neutral, bounded prosody controls.

    Non-SSML engines receive the controls through native settings where possible and
    a deterministic FFmpeg post-processing pass otherwise.
    """

    tempo: float = 1.0
    pitch_semitones: float = 0.0
    tone: str = "neutral"
    volume: float = 1.0
    language: str = "en"
    tortoise_preset: str = "fast"

    def __post_init__(self) -> None:
        if not 0.65 <= self.tempo <= 1.6:
            raise ValueError("Tempo must be between 0.65× and 1.60×")
        if not -6 <= self.pitch_semitones <= 6:
            raise ValueError("Pitch must be between -6 and +6 semitones")
        if self.tone not in TONE_FILTERS:
            raise ValueError(f"Tone must be one of: {', '.join(TONE_FILTERS)}")
        if not 0.5 <= self.volume <= 1.5:
            raise ValueError("Volume must be between 0.5× and 1.5×")
        if self.tortoise_preset not in {"ultra_fast", "fast", "standard", "high_quality"}:
            raise ValueError("Unsupported Tortoise preset")

    @property
    def is_default(self) -> bool:
        return self.tempo == 1 and self.pitch_semitones == 0 and self.tone == "neutral" and self.volume == 1


@dataclass(frozen=True)
class SpeechEvaluation:
    engine: str
    generation_seconds: float
    duration_seconds: float | None
    realtime_factor: float | None
    clarity_proxy: float | None
    naturalness_proxy: float
    technical_quality_proxy: float
    clipping_ratio: float | None
    silence_ratio: float | None
    user_satisfaction: int | None = None
    methodology: str = (
        "Clarity and technical quality are signal-health proxies; naturalness is an engine-profile heuristic. "
        "Only the listener-supplied satisfaction rating is subjective evidence."
    )

    def to_dict(self) -> dict:
        return asdict(self)


def engine_suffix(engine: str) -> str:
    try:
        return str(ENGINE_PROFILES[engine]["format"])
    except KeyError as exc:
        raise ValueError(f"Unsupported speech engine: {engine}") from exc


def to_ssml(text: str, rate: str | float = "medium", pitch_semitones: float = 0, tone: str = "neutral", volume: float = 1) -> str:
    """Return portable SSML with escaped text and explicit prosody controls."""
    if isinstance(rate, (int, float)):
        if not 0.65 <= float(rate) <= 1.6:
            raise ValueError("SSML tempo must be between 0.65× and 1.60×")
        rate_value = f"{float(rate) * 100:.0f}%"
    else:
        rate_value = rate
    if tone not in TONE_FILTERS:
        raise ValueError(f"Tone must be one of: {', '.join(TONE_FILTERS)}")
    if not -6 <= pitch_semitones <= 6:
        raise ValueError("Pitch must be between -6 and +6 semitones")
    if not 0.5 <= volume <= 1.5:
        raise ValueError("Volume must be between 0.5× and 1.5×")
    tone_emphasis = {"neutral": "none", "warm": "moderate", "bright": "strong", "calm": "reduced"}[tone]
    plain = text.replace("**", "").replace("#", "")
    return (
        f'<speak><prosody rate="{html.escape(rate_value)}" pitch="{pitch_semitones:+.1f}st" '
        f'volume="{volume * 100:.0f}%"><emphasis level="{tone_emphasis}">{html.escape(plain)}'
        "</emphasis></prosody></speak>"
    )


def synthesize(
    text: str,
    destination: str | Path,
    engine: str = "gtts",
    controls: SpeechControls | None = None,
) -> Path:
    """Synthesize speech through an explicitly selected, lazy optional engine."""
    if not text.strip():
        raise ValueError("Speech text cannot be empty")
    controls = controls or SpeechControls()
    engine = engine.lower()
    output = Path(destination)
    expected = engine_suffix(engine)
    if output.suffix.lower() != expected:
        raise ValueError(f"{ENGINE_PROFILES[engine]['label']} output must use {expected}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="learnloud-audio-") as folder:
        raw = Path(folder) / f"raw{expected}"
        if engine == "gtts":
            _gtts(text, raw, controls)
        elif engine == "pyttsx3":
            _pyttsx3(text, raw, controls)
        elif engine == "tortoise":
            _tortoise(text, raw, controls)
        elif engine in COQUI_MODELS:
            _coqui(text, raw, engine, controls)
        else:  # pragma: no cover - guarded by engine_suffix
            raise ValueError(f"Unsupported speech engine: {engine}")
        if controls.is_default:
            shutil.copyfile(raw, output)
        else:
            _apply_ffmpeg_controls(raw, output, controls)
    return output


def synthesize_and_evaluate(
    text: str,
    destination: str | Path,
    engine: str,
    controls: SpeechControls | None = None,
    satisfaction: int | None = None,
) -> tuple[Path, SpeechEvaluation]:
    started = time.perf_counter()
    path = synthesize(text, destination, engine, controls)
    elapsed = time.perf_counter() - started
    return path, evaluate_audio(path, engine, elapsed, satisfaction)


def evaluate_audio(path: str | Path, engine: str, generation_seconds: float, satisfaction: int | None = None) -> SpeechEvaluation:
    """Evaluate measurable signal health without pretending to measure human taste."""
    if satisfaction is not None and satisfaction not in range(1, 6):
        raise ValueError("Satisfaction must be an integer from 1 to 5")
    if generation_seconds < 0:
        raise ValueError("Generation time cannot be negative")
    profile = ENGINE_PROFILES.get(engine)
    if not profile:
        raise ValueError(f"Unsupported speech engine: {engine}")
    signal = _signal_metrics(Path(path))
    duration = signal.get("duration")
    clipping = signal.get("clipping")
    silence = signal.get("silence")
    clarity = None
    quality = float(profile["quality"])
    naturalness = float(profile["naturalness"])
    if clipping is not None and silence is not None:
        clarity = round(max(0.0, min(100.0, 100 - clipping * 500 - silence * 35)), 1)
        quality = round(max(0.0, min(100.0, quality - clipping * 350 - max(0, silence - .45) * 30)), 1)
        naturalness = round(max(0.0, min(100.0, naturalness - clipping * 150)), 1)
    realtime = round(generation_seconds / duration, 3) if duration and duration > 0 else None
    return SpeechEvaluation(
        engine=str(profile["label"]),
        generation_seconds=round(generation_seconds, 3),
        duration_seconds=round(duration, 3) if duration is not None else None,
        realtime_factor=realtime,
        clarity_proxy=clarity,
        naturalness_proxy=naturalness,
        technical_quality_proxy=quality,
        clipping_ratio=round(clipping, 5) if clipping is not None else None,
        silence_ratio=round(silence, 5) if silence is not None else None,
        user_satisfaction=satisfaction,
    )


def _gtts(text: str, output: Path, controls: SpeechControls) -> None:
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise RuntimeError("Install gTTS to generate MP3 audio") from exc
    # Keep synthesis neutral; the common FFmpeg pass applies exact bounded tempo.
    gTTS(text=text, lang=controls.language, slow=False).save(str(output))


def _pyttsx3(text: str, output: Path, controls: SpeechControls) -> None:
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError("Install pyttsx3 and a system speech driver") from exc
    speaker = pyttsx3.init()
    speaker.setProperty("volume", 1.0)
    speaker.save_to_file(text, str(output))
    speaker.runAndWait()


def _tortoise(text: str, output: Path, controls: SpeechControls) -> None:
    try:
        import torchaudio
        from tortoise.api import TextToSpeech
    except ImportError as exc:
        raise RuntimeError("Install tortoise-tts and torchaudio; a CUDA GPU is strongly recommended") from exc
    speaker = TextToSpeech()
    audio = speaker.tts_with_preset(
        text,
        voice_samples=None,
        conditioning_latents=None,
        preset=controls.tortoise_preset,
    )
    torchaudio.save(str(output), audio.squeeze(0).cpu(), 24_000)


def _coqui(text: str, output: Path, engine: str, controls: SpeechControls) -> None:
    try:
        from TTS.api import TTS
    except ImportError as exc:
        raise RuntimeError("Install coqui-tts to use Tacotron 2, Glow-TTS, or YourTTS") from exc
    env_name = {"tacotron2": "TACOTRON_MODEL", "glow-tts": "GLOW_TTS_MODEL", "yourtts": "YOURTTS_MODEL"}[engine]
    model_id = os.getenv(env_name, COQUI_MODELS[engine])
    device = os.getenv("TTS_DEVICE", "cpu").lower()
    if device not in {"cpu", "cuda"}:
        raise ValueError("TTS_DEVICE must be cpu or cuda")
    model = TTS(model_name=model_id, progress_bar=False)
    if device == "cuda":
        model = model.to("cuda")
    options: dict[str, object] = {"text": text, "file_path": str(output)}
    if engine == "yourtts":
        options["language"] = controls.language
        speaker = os.getenv("YOURTTS_SPEAKER", "").strip()
        if speaker:
            options["speaker"] = speaker
        elif getattr(model, "speakers", None):
            options["speaker"] = model.speakers[0]
    model.tts_to_file(**options)


def _atempo_chain(value: float) -> list[str]:
    filters: list[str] = []
    while value > 2:
        filters.append("atempo=2")
        value /= 2
    while value < .5:
        filters.append("atempo=.5")
        value /= .5
    filters.append(f"atempo={value:.6f}")
    return filters


def _apply_ffmpeg_controls(source: Path, destination: Path, controls: SpeechControls) -> None:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg is required for pitch, tone, tempo, or volume post-processing")
    sample_rate = _audio_sample_rate(source)
    pitch_factor = 2 ** (controls.pitch_semitones / 12)
    filters = [f"asetrate={sample_rate}*{pitch_factor:.8f}", f"aresample={sample_rate}", *_atempo_chain(controls.tempo / pitch_factor)]
    if TONE_FILTERS[controls.tone]:
        filters.extend(TONE_FILTERS[controls.tone].split(","))
    if controls.volume != 1:
        filters.append(f"volume={controls.volume:.3f}")
    command = [executable, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-filter:a", ",".join(filters), str(destination)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=180)
    if completed.returncode:
        raise RuntimeError(f"FFmpeg audio controls failed: {completed.stderr.strip() or 'unknown error'}")


def _audio_sample_rate(path: Path) -> int:
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as stream:
            return stream.getframerate()
    probe = shutil.which("ffprobe")
    if not probe:
        raise RuntimeError("FFprobe is required to inspect compressed audio before applying controls")
    completed = subprocess.run(
        [probe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    try:
        return int(completed.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Could not determine the generated audio sample rate") from exc


def _signal_metrics(path: Path) -> dict[str, float | None]:
    if path.suffix.lower() != ".wav":
        try:
            from pydub import AudioSegment
        except ImportError:
            return {"duration": None, "clipping": None, "silence": None}
        segment = AudioSegment.from_file(path)
        with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
            segment.export(handle.name, format="wav")
            return _wav_metrics(Path(handle.name))
    return _wav_metrics(path)


def _wav_metrics(path: Path) -> dict[str, float]:
    with wave.open(str(path), "rb") as stream:
        width = stream.getsampwidth()
        rate = stream.getframerate()
        frames = stream.getnframes()
        raw = stream.readframes(frames)
    if width not in {1, 2, 4} or not raw:
        return {"duration": frames / max(1, rate), "clipping": 0.0, "silence": 1.0}
    formats = {1: "B", 2: "h", 4: "i"}
    count = len(raw) // width
    values = struct.unpack(f"<{count}{formats[width]}", raw)
    if width == 1:
        samples = [value - 128 for value in values]
        maximum = 127
    else:
        samples = values
        maximum = float(2 ** (width * 8 - 1) - 1)
    clipping = sum(abs(value) >= maximum * .98 for value in samples) / len(samples)
    silence = sum(abs(value) <= maximum * .01 for value in samples) / len(samples)
    return {"duration": frames / max(1, rate), "clipping": clipping, "silence": silence}
