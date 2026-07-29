from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

from edu_qa.service import EducationService
from edu_qa.speech import SpeechControls, engine_suffix, synthesize_and_evaluate, to_ssml

st.set_page_config(page_title="LearnLoud", page_icon="🎓", layout="wide")
st.markdown("""
<style>
.stApp {background: radial-gradient(circle at 10% 0%, #172554 0, #080d1d 42%, #050713 100%); color:#eef2ff}
[data-testid="stSidebar"] {background:#0a1024}
.hero {padding:2rem;border:1px solid #29366d;border-radius:24px;background:linear-gradient(135deg,#111b3fdd,#211342cc);margin-bottom:1rem;animation:learn-in .55s ease-out both,learn-glow 7s ease-in-out infinite}
.hero h1 {font-size:3rem;margin:0;background:linear-gradient(90deg,#67e8f9,#c4b5fd);-webkit-background-clip:text;color:transparent}
.pill {display:inline-block;padding:.3rem .65rem;border-radius:99px;background:#1e2b58;color:#a5f3fc;margin-right:.35rem;animation:learn-in .5s ease-out both}
@keyframes learn-in {from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes learn-glow {50%{border-color:#67e8f977;box-shadow:0 16px 46px #312e8130}}
@media (prefers-reduced-motion: reduce){.hero,.pill{animation:none!important}}
</style>
<div class="hero"><span class="pill">Offline-first</span><span class="pill">Evidence-aware</span><span class="pill">Audio-ready</span>
<h1>LearnLoud</h1><p>Your patient, accessible study companion. Ask, understand, listen, and keep exploring.</p></div>
""", unsafe_allow_html=True)

service = EducationService(ROOT / "sample_data" / "knowledge.json")
with st.sidebar:
    st.header("Learning controls")
    level = st.select_slider("Explanation depth", ["Beginner", "Intermediate", "Advanced"])
    available = ["Offline"] + (["Gemini"] if os.getenv("GEMINI_API_KEY") else [])
    provider_label = st.selectbox("Tutor engine", available)
    st.caption("The offline tutor stays local. Gemini appears only when its key is configured.")

question = st.text_area("What would you like to understand?", placeholder="Why do seasons happen?", height=100)
if st.button("Explain it", type="primary", use_container_width=True):
    try:
        answer = service.ask(question, level, provider_label.lower())
        st.session_state["answer"] = answer
        st.session_state["audio_runs"] = []
    except Exception as exc:
        st.error(str(exc))

if answer := st.session_state.get("answer"):
    left, right = st.columns([3, 1])
    with left:
        st.markdown(answer.response)
        st.caption(f"{answer.provider} · confidence signal {answer.confidence:.0%} · not a substitute for primary sources")
        with st.expander("Sources and retrieval evidence"):
            for item in answer.evidence:
                st.markdown(f"**{item.title}** — {item.source}\n\n{item.excerpt}")
    with right:
        st.subheader("Keep exploring")
        for prompt in answer.follow_ups:
            st.info(prompt)
        st.subheader("Voice lab")
        voice_options = {
            "gTTS · quick network baseline": "gtts",
            "pyttsx3 · local system voice": "pyttsx3",
            "Tacotron 2 · Coqui": "tacotron2",
            "Glow-TTS · Coqui": "glow-tts",
            "YourTTS · multilingual Coqui": "yourtts",
            "Tortoise-TTS · expressive, GPU recommended": "tortoise",
        }
        voice_label = st.selectbox("Speech engine", list(voice_options))
        engine = voice_options[voice_label]
        tempo = st.slider("Tempo", .65, 1.60, 1.0, .05, format="%.2f×")
        pitch = st.slider("Pitch", -6.0, 6.0, 0.0, .5, format="%+.1f st")
        tone = st.selectbox("Tone profile", ["neutral", "warm", "bright", "calm"])
        volume = st.slider("Volume", .5, 1.5, 1.0, .05, format="%.2f×")
        preset = st.selectbox("Tortoise quality preset", ["ultra_fast", "fast", "standard", "high_quality"], index=1, disabled=engine != "tortoise")
        language = st.text_input("Language code", "en", help="Used by gTTS and multilingual YourTTS.")
        controls = SpeechControls(tempo, pitch, tone, volume, language.strip() or "en", preset)
        st.download_button(
            "Download controlled SSML",
            to_ssml(answer.response, tempo, pitch, tone, volume),
            "answer.ssml",
            "application/ssml+xml",
            use_container_width=True,
        )
        if st.button("Create audio", use_container_width=True):
            try:
                with tempfile.TemporaryDirectory() as folder:
                    suffix = engine_suffix(engine)
                    path, evaluation = synthesize_and_evaluate(answer.response, Path(folder) / f"answer{suffix}", engine, controls)
                    audio = path.read_bytes()
                st.session_state.setdefault("audio_runs", []).append(
                    {"audio": audio, "suffix": suffix, "engine_key": engine, "evaluation": evaluation.to_dict()}
                )
            except Exception as exc:
                st.warning(str(exc))

    runs = st.session_state.get("audio_runs", [])
    if runs:
        st.markdown("### Listen, rate, and compare")
        st.caption("Signal metrics are engineering proxies—not human judgments. Add a listener rating only after hearing each clip.")
        table = []
        for index, run in enumerate(runs):
            evaluation = run["evaluation"]
            with st.expander(f"{index + 1}. {evaluation['engine']}", expanded=index == len(runs) - 1):
                st.audio(run["audio"])
                st.download_button(
                    f"Download {evaluation['engine']} audio",
                    run["audio"],
                    f"learnloud-{run['engine_key']}{run['suffix']}",
                    key=f"download-audio-{index}",
                    use_container_width=True,
                )
                satisfaction = st.slider(
                    "Listener satisfaction (0 = not rated)", 0, 5, int(evaluation.get("user_satisfaction") or 0),
                    key=f"satisfaction-{index}", help="This is the only subjective score in the comparison."
                )
                evaluation["user_satisfaction"] = satisfaction or None
                st.caption(evaluation["methodology"])
            table.append(
                {
                    "Engine": evaluation["engine"],
                    "Generation (s)": evaluation["generation_seconds"],
                    "Realtime factor": evaluation["realtime_factor"],
                    "Clarity proxy": evaluation["clarity_proxy"],
                    "Naturalness proxy": evaluation["naturalness_proxy"],
                    "Technical quality": evaluation["technical_quality_proxy"],
                    "Listener satisfaction": evaluation["user_satisfaction"],
                }
            )
        st.dataframe(table, use_container_width=True, hide_index=True)
        if st.button("Clear voice comparison"):
            st.session_state["audio_runs"] = []
            st.rerun()
