import json
import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edu_qa.knowledge import KnowledgeBase
from edu_qa.service import EducationService
from edu_qa.speech import SpeechControls, engine_suffix, evaluate_audio, to_ssml


class EducationTests(unittest.TestCase):
    def setUp(self):
        self.service = EducationService(ROOT / "sample_data" / "knowledge.json")

    def test_retrieves_relevant_evidence(self):
        answer = self.service.ask("Why do seasons happen?")
        self.assertEqual(answer.evidence[0].title, "Seasons")
        self.assertIn("axial tilt", answer.response)

    def test_unknown_question_is_honest(self):
        answer = self.service.ask("Explain zephyrian quuxology")
        self.assertLess(answer.confidence, 0.2)
        self.assertIn("don’t have enough", answer.response)

    def test_invalid_knowledge_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps([{"title": "Missing content"}]), encoding="utf-8")
            with self.assertRaises(ValueError):
                KnowledgeBase.from_json(path)

    def test_ssml_escapes_markup(self):
        rendered = to_ssml("A < B & B > C")
        self.assertIn("&lt;", rendered)
        self.assertIn("&amp;", rendered)

    def test_ssml_includes_bounded_prosody_controls(self):
        rendered = to_ssml("A controlled explanation", 1.2, 2.5, "warm", .9)
        self.assertIn('rate="120%"', rendered)
        self.assertIn('pitch="+2.5st"', rendered)
        self.assertIn('volume="90%"', rendered)
        with self.assertRaises(ValueError):
            SpeechControls(tempo=2.0)

    def test_named_tts_adapters_have_real_output_contracts(self):
        self.assertEqual(engine_suffix("tacotron2"), ".wav")
        self.assertEqual(engine_suffix("glow-tts"), ".wav")
        self.assertEqual(engine_suffix("yourtts"), ".wav")

    def test_wav_evaluation_reports_signal_health_without_invented_satisfaction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tone.wav"
            rate = 8_000
            samples = [int(8_000 * math.sin(2 * math.pi * 440 * index / rate)) for index in range(rate)]
            with wave.open(str(path), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(rate)
                stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            report = evaluate_audio(path, "tacotron2", generation_seconds=.5)
        self.assertAlmostEqual(report.duration_seconds, 1.0)
        self.assertIsNotNone(report.clarity_proxy)
        self.assertIsNone(report.user_satisfaction)
        self.assertAlmostEqual(report.realtime_factor, .5)


if __name__ == "__main__":
    unittest.main()
