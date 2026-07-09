"""Evaluation metrics for generated GitHub issue drafts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from rouge_score import rouge_scorer

from issue_draft_generator.models import IssueDraft


@dataclass
class QualityMetrics:
    title_similarity: float
    body_rouge_l: float
    label_f1: float
    severity_match: float
    composite_score: float


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def title_similarity(predicted: str, expected: str) -> float:
    left = _normalize_text(predicted)
    right = _normalize_text(expected)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def body_rouge_l(predicted: str, expected: str) -> float:
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(expected, predicted)
    return float(scores["rougeL"].fmeasure)


def label_f1(predicted: list[str], expected: list[str]) -> float:
    pred = {label.lower().strip() for label in predicted if label.strip()}
    truth = {label.lower().strip() for label in expected if label.strip()}
    if not pred and not truth:
        return 1.0
    if not pred or not truth:
        return 0.0
    tp = len(pred & truth)
    precision = tp / len(pred)
    recall = tp / len(truth)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def severity_match(predicted: str, expected: str) -> float:
    return 1.0 if predicted.strip().lower() == expected.strip().lower() else 0.0


def composite_quality_score(
    *,
    title_similarity_score: float,
    body_rouge_l_score: float,
    label_f1_score: float,
    severity_match_score: float,
) -> float:
    return (
        0.25 * title_similarity_score
        + 0.40 * body_rouge_l_score
        + 0.20 * label_f1_score
        + 0.15 * severity_match_score
    )


def evaluate_draft(predicted: IssueDraft, expected: IssueDraft) -> QualityMetrics:
    title_score = title_similarity(predicted.title, expected.title)
    body_score = body_rouge_l(predicted.body, expected.body)
    labels_score = label_f1(predicted.labels, expected.labels)
    severity_score = severity_match(predicted.severity, expected.severity)
    composite = composite_quality_score(
        title_similarity_score=title_score,
        body_rouge_l_score=body_score,
        label_f1_score=labels_score,
        severity_match_score=severity_score,
    )
    return QualityMetrics(
        title_similarity=title_score,
        body_rouge_l=body_score,
        label_f1=labels_score,
        severity_match=severity_score,
        composite_score=composite,
    )
