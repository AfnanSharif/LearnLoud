"""Session history tracking for learning analytics."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SessionEntry:
    """A single Q&A interaction within a learning session."""
    question: str
    level: str
    provider: str
    confidence: float
    topic: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LearningSession:
    """Tracks a sequence of learning interactions with analytics."""
    entries: list[SessionEntry] = field(default_factory=list)
    started: float = field(default_factory=time.time)

    def add(self, question: str, level: str, provider: str, confidence: float, topic: str) -> SessionEntry:
        """Record a new Q&A interaction."""
        entry = SessionEntry(question, level, provider, confidence, topic)
        self.entries.append(entry)
        return entry

    @property
    def question_count(self) -> int:
        return len(self.entries)

    @property
    def topics_studied(self) -> list[str]:
        """Unique topics explored in this session."""
        seen: dict[str, None] = {}
        for e in self.entries:
            seen.setdefault(e.topic, None)
        return list(seen)

    @property
    def topic_frequency(self) -> dict[str, int]:
        """How many times each topic was asked about."""
        freq: dict[str, int] = {}
        for e in self.entries:
            freq[e.topic] = freq.get(e.topic, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))

    @property
    def avg_confidence(self) -> float:
        if not self.entries:
            return 0.0
        return round(sum(e.confidence for e in self.entries) / len(self.entries), 2)

    @property
    def duration_minutes(self) -> float:
        if not self.entries:
            return 0.0
        return round((time.time() - self.started) / 60, 1)

    @property
    def level_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for e in self.entries:
            dist[e.level] = dist.get(e.level, 0) + 1
        return dist

    def to_dict(self) -> dict:
        return {
            "started": self.started,
            "question_count": self.question_count,
            "topics_studied": self.topics_studied,
            "topic_frequency": self.topic_frequency,
            "avg_confidence": self.avg_confidence,
            "duration_minutes": self.duration_minutes,
            "level_distribution": self.level_distribution,
            "entries": [e.to_dict() for e in self.entries],
        }

    def to_markdown(self) -> str:
        """Export session as readable Markdown."""
        lines = [
            "# 🎓 LearnLoud — Learning Session Report\n",
            f"**Duration:** {self.duration_minutes} minutes  ",
            f"**Questions asked:** {self.question_count}  ",
            f"**Average confidence:** {self.avg_confidence:.0%}  ",
            f"**Topics explored:** {', '.join(self.topics_studied)}\n",
            "## Questions\n",
        ]
        for i, e in enumerate(self.entries, 1):
            lines.append(f"{i}. **{e.question}** ({e.level}) — confidence {e.confidence:.0%}")
        return "\n".join(lines)

    def save(self, path: str | Path) -> Path:
        """Save session as JSON."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return out

    @classmethod
    def load(cls, path: str | Path) -> Optional["LearningSession"]:
        """Load a session from JSON if it exists."""
        p = Path(path)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        session = cls(started=data.get("started", time.time()))
        for entry in data.get("entries", []):
            session.entries.append(SessionEntry(**entry))
        return session
