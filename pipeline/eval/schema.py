"""Genormaliseerd tussenformaat voor externe argumentatie-datasets in het
evalharnas (issue #62). Eén regel JSON per record (JSONL). Zie
docs/eval-elecdebate.md voor de motivatie en het conversiepad vanaf het
ruwe ELECDEBATE60TO16-bestand."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Span:
    """Tekenpositie [start, end) binnen EvalRecord.text."""

    start: int
    end: int


@dataclass(frozen=True)
class FallacySpan:
    """Zoals Span, met het gouden drogreden-label van de brondataset (bv.
    "AdHominem") -- nog niet omgezet naar onze eigen tag-sleutel, dat gebeurt
    pas in pipeline/eval/label_mapping.py."""

    start: int
    end: int
    label: str


@dataclass(frozen=True)
class EvalRecord:
    text: str
    speaker: str | None
    spans: list[Span] = field(default_factory=list)
    fallacies: list[FallacySpan] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "EvalRecord":
        return cls(
            text=data["text"],
            speaker=data.get("speaker"),
            spans=[Span(**s) for s in data.get("spans", [])],
            fallacies=[FallacySpan(**f) for f in data.get("fallacies", [])],
        )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "speaker": self.speaker,
            "spans": [{"start": s.start, "end": s.end} for s in self.spans],
            "fallacies": [{"start": f.start, "end": f.end, "label": f.label} for f in self.fallacies],
        }
