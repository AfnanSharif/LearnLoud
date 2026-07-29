from __future__ import annotations

from pathlib import Path

from .knowledge import KnowledgeBase, tokens
from .models import Answer
from .providers import GeminiTutor, OfflineTutor


class EducationService:
    def __init__(self, knowledge_path: str | Path) -> None:
        self.knowledge = KnowledgeBase.from_json(knowledge_path)

    def ask(self, question: str, level: str = "Beginner", provider: str = "offline") -> Answer:
        question = " ".join(question.split())
        if len(question) < 4:
            raise ValueError("Please ask a complete question (at least 4 characters)")
        evidence = self.knowledge.search(question)
        engine = GeminiTutor() if provider.lower() == "gemini" else OfflineTutor()
        response = engine.answer(question, evidence, level)
        overlap = len(set(tokens(question)) & {t for e in evidence for t in tokens(e.excerpt)})
        confidence = min(0.95, 0.35 + overlap * 0.1) if evidence else 0.1
        subject = evidence[0].title if evidence else "this topic"
        follow_ups = [
            f"Can you give me a simple example of {subject}?",
            f"What is a common misconception about {subject}?",
            f"Quiz me on {subject}.",
        ]
        return Answer(question, response, engine.name, level, evidence, follow_ups, round(confidence, 2))
