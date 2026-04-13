"""Data models for Senseis enrichment pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SenseisPageData:
    """Metadata extracted from a Senseis problem page."""

    problem_number: int
    page_name: str
    title_english: str = ""
    title_chinese: str = ""
    title_pinyin: str = ""
    difficulty: str = ""
    instruction: str = ""
    diagram_sgf_url: str = ""  # URL to the problem diagram SGF (for position matching)
    cross_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "problem_number": self.problem_number,
            "page_name": self.page_name,
            "title_english": self.title_english,
            "title_chinese": self.title_chinese,
            "title_pinyin": self.title_pinyin,
            "difficulty": self.difficulty,
            "instruction": self.instruction,
            "diagram_sgf_url": self.diagram_sgf_url,
            "cross_references": self.cross_references,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SenseisPageData:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SenseisDiagram:
    """A single diagram from a Senseis solution page."""

    diagram_name: str
    sgf_url: str
    sgf_content: str = ""
    commentary: str = ""

    def to_dict(self) -> dict:
        return {
            "diagram_name": self.diagram_name,
            "sgf_url": self.sgf_url,
            "sgf_content": self.sgf_content,
            "commentary": self.commentary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SenseisDiagram:
        return cls(**d)


@dataclass
class SenseisSolutionData:
    """All solution data from a Senseis solution page."""

    problem_number: int
    diagrams: list[SenseisDiagram] = field(default_factory=list)
    preamble_text: str = ""
    status: str = "ok"  # "ok", "404", "empty", "error"

    def to_dict(self) -> dict:
        return {
            "problem_number": self.problem_number,
            "diagrams": [d.to_dict() for d in self.diagrams],
            "preamble_text": self.preamble_text,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SenseisSolutionData:
        diagrams = [SenseisDiagram.from_dict(dd) for dd in d.get("diagrams", [])]
        return cls(
            problem_number=d["problem_number"],
            diagrams=diagrams,
            preamble_text=d.get("preamble_text", ""),
            status=d.get("status", "ok"),
        )


@dataclass
class PositionTransform:
    """Rotation/reflection transform to map Senseis coords to local coords."""

    rotation: int = 0  # 0, 90, 180, 270
    reflect: bool = False  # horizontal reflection after rotation

    def to_dict(self) -> dict:
        return {"rotation": self.rotation, "reflect": self.reflect}

    @classmethod
    def from_dict(cls, d: dict) -> PositionTransform:
        return cls(rotation=d["rotation"], reflect=d["reflect"])


@dataclass
class MatchResult:
    """Result of position matching for one problem."""

    problem_number: int
    matched: bool = False
    transform: PositionTransform | None = None
    local_hash: str = ""
    senseis_hash: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "problem_number": self.problem_number,
            "matched": self.matched,
            "transform": self.transform.to_dict() if self.transform else None,
            "local_hash": self.local_hash,
            "senseis_hash": self.senseis_hash,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MatchResult:
        transform = None
        if d.get("transform"):
            transform = PositionTransform.from_dict(d["transform"])
        return cls(
            problem_number=d["problem_number"],
            matched=d["matched"],
            transform=transform,
            local_hash=d.get("local_hash", ""),
            senseis_hash=d.get("senseis_hash", ""),
            detail=d.get("detail", ""),
        )
