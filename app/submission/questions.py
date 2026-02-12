"""Versioned question set utilities for submissions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

QUESTION_SETS_DIR = Path(__file__).resolve().parent / "question_sets"
DEFAULT_QUESTION_VERSION = "v1_6"


@dataclass(frozen=True)
class QuestionSet:
    version: str
    group_labels: Mapping[str, str]
    groups: Mapping[str, List[dict]]
    questions: List[dict]
    lookup: Mapping[str, dict]
    required_ids: frozenset[str]
    custom_ids: frozenset[str]
    metadata: Mapping[str, Any]

    def to_group_choices(
        self, *, include_non_selectable: bool = True
    ) -> List[tuple[str, List[tuple[str, str]]]]:
        excluded = set()
        if not include_non_selectable:
            excluded = set(self.metadata.get("non_selectable_groups", []))
        return [
            (
                self.group_labels.get(group_key, group_key),
                [(question["id"], question["text"]) for question in questions],
            )
            for group_key, questions in self.groups.items()
            if include_non_selectable or group_key not in excluded
        ]


def _load_raw_question_set(version: str) -> dict:
    path = QUESTION_SETS_DIR / f"{version}.json"
    if not path.exists():
        raise FileNotFoundError(f"Question set for version '{version}' not found at {path}")
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache
def load_question_set(version: str = DEFAULT_QUESTION_VERSION) -> QuestionSet:
    raw = _load_raw_question_set(version)
    groups: Dict[str, List[dict]] = {
        key: list(value) for key, value in raw.get("groups", {}).items()
    }
    questions: List[dict] = [question for value in groups.values() for question in value]
    lookup = {question["id"]: question for question in questions}
    required_ids = frozenset(q["id"] for q in questions if q.get("required"))
    custom_ids = frozenset(q["id"] for q in questions if q.get("custom"))
    metadata = {
        key: value
        for key, value in raw.items()
        if key not in {"version", "group_labels", "groups"}
    }
    return QuestionSet(
        version=raw.get("version", version),
        group_labels=raw.get("group_labels", {}),
        groups=groups,
        questions=questions,
        lookup=lookup,
        required_ids=required_ids,
        custom_ids=custom_ids,
        metadata=metadata,
    )


def get_group_labels(version: str = DEFAULT_QUESTION_VERSION) -> Mapping[str, str]:
    return load_question_set(version).group_labels


def get_grouped_questions(version: str = DEFAULT_QUESTION_VERSION) -> Mapping[str, List[dict]]:
    return load_question_set(version).groups


def get_default_questions(version: str = DEFAULT_QUESTION_VERSION) -> Iterable[dict]:
    return load_question_set(version).questions


def get_question_lookup(version: str = DEFAULT_QUESTION_VERSION) -> Mapping[str, dict]:
    return load_question_set(version).lookup


def get_required_question_ids(version: str = DEFAULT_QUESTION_VERSION) -> frozenset[str]:
    return load_question_set(version).required_ids


def get_custom_question_ids(version: str = DEFAULT_QUESTION_VERSION) -> frozenset[str]:
    return load_question_set(version).custom_ids


# Backwards-compatible default exports -------------------------------------
DEFAULT_QUESTION_SET = load_question_set()
QUESTION_GROUP_LABELS = DEFAULT_QUESTION_SET.group_labels
GROUPED_QUESTIONS = DEFAULT_QUESTION_SET.groups
DEFAULT_QUESTIONS = DEFAULT_QUESTION_SET.questions
REQUIRED_QUESTION_IDS = DEFAULT_QUESTION_SET.required_ids
CUSTOM_QUESTION_IDS = DEFAULT_QUESTION_SET.custom_ids
QUESTION_LOOKUP = DEFAULT_QUESTION_SET.lookup  
# --------------------------------------------------------------------------
