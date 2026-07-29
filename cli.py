from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

from edu_qa.service import EducationService


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the offline-first educational tutor")
    parser.add_argument("question")
    parser.add_argument("--level", choices=["Beginner", "Intermediate", "Advanced"], default="Beginner")
    parser.add_argument("--provider", choices=["offline", "gemini"], default="offline")
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    args = parser.parse_args()
    answer = EducationService(ROOT / "sample_data" / "knowledge.json").ask(args.question, args.level, args.provider)
    print(json.dumps(answer.to_dict(), indent=2) if args.json else answer.response)


if __name__ == "__main__":
    main()
