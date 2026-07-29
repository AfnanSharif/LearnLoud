<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=00c6ff,0072ff&height=200&section=header&text=LearnLoud&fontSize=70&fontColor=ffffff&animation=twinkling" width="100%" />

<img src="https://img.icons8.com/?id=44010&format=png&size=100" width="90" />

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=22&duration=2500&pause=1000&color=00c6ff&center=true&vCenter=true&width=700&height=50&lines=Offline-first%20educational%20question%20answering%20with;Python%20+%20Streamlit" alt="Typing SVG" />

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](#)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](#)

</div>

---

## 📖 Overview

**LearnLoud** — Offline-first educational question answering with optional AI and speech providers.

Core logic lives in `src/edu_qa/`. Configuration is centralized in `config/settings.yaml`
and secrets/API keys are loaded from a local `.env` (see `.env.example`).

## 🏗️ Project Layout

```
LearnLoud/
├── app.py               # Streamlit entry point
├── src/edu_qa/
│   └── ...              # Core package — offline-first educational question answering with optional ai and speech providers
├── config/settings.yaml # App configuration
├── tests/                # Unit tests
├── scripts/setup.sh      # venv + install helper (macOS/Linux)
├── requirements-ai.txt
├── requirements.txt
```

### Also included
- `cli.py` — command-line interface


## ⚡ Setup & Run

### 🪟 Windows (PowerShell / CMD)
```cmd
git clone https://github.com/AfnanSharif/LearnLoud.git
cd LearnLoud

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ai.txt  # optional extras

copy .env.example .env
:: edit .env to add any API keys — the app runs fully offline without them

streamlit run app.py
```

### 🍎 macOS / 🐧 Linux
```bash
git clone https://github.com/AfnanSharif/LearnLoud.git
cd LearnLoud

./scripts/setup.sh                 # creates .venv and installs requirements.txt
source .venv/bin/activate
pip install -r requirements-ai.txt  # optional extras

cp .env.example .env
# edit .env to add any API keys — the app runs fully offline without them

streamlit run app.py
```

Open **http://localhost:8501**.

```bash
make test    # run the test suite
make lint    # lint the codebase
```

---

<div align="center">

**Created by [AfnanSharif](https://github.com/AfnanSharif)** · ⭐ star this repo if it helped you

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=00c6ff,0072ff&height=80&section=footer" width="100%" />

</div>
