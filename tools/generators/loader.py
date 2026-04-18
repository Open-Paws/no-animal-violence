"""Load and validate rules.yaml."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Rule:
    name: str
    terms: list[str]
    alternatives: list[str]
    severity: str
    category: str
    note: str
    word_boundary: bool
    regex: str
    context_suppressions: list[str] = field(default_factory=list)

    @property
    def primary_term(self) -> str:
        return self.terms[0] if self.terms else ""

    @property
    def primary_alt(self) -> str:
        return self.alternatives[0] if self.alternatives else ""

    @property
    def semgrep_severity(self) -> str:
        return {"error": "ERROR", "warning": "WARNING", "info": "INFO"}.get(self.severity, "WARNING")


def load_rules(rules_yaml_path: Path) -> list[Rule]:
    with open(rules_yaml_path) as f:
        data = yaml.safe_load(f)
    rules = []
    for r in data.get("rules", []):
        rules.append(Rule(
            name=r["name"],
            terms=r["terms"],
            alternatives=r["alternatives"],
            severity=r["severity"],
            category=r.get("category", "animal-violence"),
            note=r.get("note", ""),
            word_boundary=r.get("word_boundary", True),
            regex=r["regex"],
            context_suppressions=r.get("context_suppressions", []),
        ))
    return rules


def canonical_rules_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "rules.yaml"
