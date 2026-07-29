from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Evidence:
    title: str
    excerpt: str
    source: str = "Built-in learning library"
    score: float = 0.0


@dataclass
class Answer:
    question: str
    response: str
    provider: str
    level: str
    evidence: list[Evidence] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
