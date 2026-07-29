from __future__ import annotations

import os
from typing import Protocol

from .models import Evidence


class AnswerProvider(Protocol):
    name: str

    def answer(self, question: str, evidence: list[Evidence], level: str) -> str: ...


class OfflineTutor:
    name = "Offline tutor"

    _level_notes = {
        "Beginner": "I’ll use plain language and one concrete analogy.",
        "Intermediate": "I’ll connect the idea to its mechanism and a practical example.",
        "Advanced": "I’ll emphasize assumptions, mechanism, and limitations.",
    }

    def answer(self, question: str, evidence: list[Evidence], level: str) -> str:
        if not evidence:
            return (
                "I don’t have enough reliable material in the local learning library to answer that "
                "question confidently. Try naming the subject and the specific concept, or enable "
                "Gemini for broader coverage."
            )
        primary = evidence[0]
        note = self._level_notes.get(level, self._level_notes["Beginner"])
        if level == "Beginner":
            explanation = (
                f"**Short answer:** {primary.excerpt}\n\n"
                f"**Think of it this way:** the important idea in *{primary.title}* is to focus on "
                "what changes, what causes the change, and what can be observed."
            )
        elif level == "Advanced":
            explanation = (
                f"**Core explanation:** {primary.excerpt}\n\n"
                "**Reasoning lens:** distinguish the definition from the underlying mechanism, then "
                "test the explanation against its assumptions and edge cases."
            )
        else:
            explanation = (
                f"**Explanation:** {primary.excerpt}\n\n"
                "**How to use it:** identify the inputs, follow the process, and check whether the "
                "predicted outcome matches the evidence."
            )
        related = "\n".join(f"- **{item.title}:** {item.excerpt}" for item in evidence[1:])
        return f"{note}\n\n{explanation}" + (f"\n\n**Related ideas**\n{related}" if related else "")


class GeminiTutor:
    name = "Google Gemini"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def answer(self, question: str, evidence: list[Evidence], level: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install the google-genai optional dependency") from exc
        context = "\n".join(f"[{e.title}] {e.excerpt}" for e in evidence) or "No local context."
        prompt = f"""You are a careful educational tutor. Answer at a {level.lower()} level.
State uncertainty, never invent citations, use a short example, and end with one self-check question.

Local context (use it when relevant):
{context}

Learner question: {question}
"""
        client = genai.Client(api_key=api_key)
        result = client.models.generate_content(model=self.model, contents=prompt)
        if not getattr(result, "text", None):
            raise RuntimeError("Gemini returned an empty response")
        return result.text.strip()
