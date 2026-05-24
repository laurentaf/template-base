"""Confidence Scoring Engine — Agreement Matrix + Research-Driven Self-Improvement.

Implements the confidence validation protocol from the agent template:
1. CLASSIFY task type and threshold
2. LOAD KB patterns
3. VALIDATE via MCP if KB insufficient
4. CALCULATE base score + modifiers = final confidence
5. DECIDE: execute / research / ask user / refuse

Key improvement: when confidence < threshold, agents research
(KB, MCP, internet) up to MAX_ROUNDS before asking the user.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.core.config import settings


class TaskCategory(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    STANDARD = "standard"
    ADVISORY = "advisory"


class AgreementLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    MCP_ONLY = "mcp_only"
    CONFLICT = "conflict"
    LOW = "low"


class DecisionAction(StrEnum):
    EXECUTE = "execute"
    RESEARCH = "research"
    ASK_USER = "ask_user"
    REFUSE = "refuse"
    DISCLAIM = "disclaim"


AGREEMENT_MATRIX: dict[str, dict[str, AgreementLevel]] = {
    "kb_has_pattern": {
        "mcp_agrees": AgreementLevel.HIGH,
        "mcp_disagrees": AgreementLevel.CONFLICT,
        "mcp_silent": AgreementLevel.MEDIUM,
    },
    "kb_silent": {
        "mcp_agrees": AgreementLevel.MCP_ONLY,
        "mcp_disagrees": AgreementLevel.CONFLICT,
        "mcp_silent": AgreementLevel.LOW,
    },
}

AGREEMENT_BASE_SCORES: dict[AgreementLevel, float] = {
    AgreementLevel.HIGH: 0.95,
    AgreementLevel.MEDIUM: 0.75,
    AgreementLevel.MCP_ONLY: 0.85,
    AgreementLevel.CONFLICT: 0.50,
    AgreementLevel.LOW: 0.50,
}

CATEGORY_THRESHOLDS: dict[TaskCategory, float] = {
    TaskCategory.CRITICAL: settings.CONFIDENCE_THRESHOLD_CRITICAL,
    TaskCategory.IMPORTANT: settings.CONFIDENCE_THRESHOLD_IMPORTANT,
    TaskCategory.STANDARD: settings.CONFIDENCE_THRESHOLD_STANDARD,
    TaskCategory.ADVISORY: settings.CONFIDENCE_THRESHOLD_ADVISORY,
}

CATEGORY_DEFAULT_ACTIONS_BELOW: dict[TaskCategory, DecisionAction] = {
    TaskCategory.CRITICAL: DecisionAction.REFUSE,
    TaskCategory.IMPORTANT: DecisionAction.ASK_USER,
    TaskCategory.STANDARD: DecisionAction.RESEARCH,
    TaskCategory.ADVISORY: DecisionAction.DISCLAIM,
}


class ConfidenceModifier(BaseModel):
    condition: str
    modifier: float
    applied: bool = False


MODIFIERS: list[ConfidenceModifier] = [
    ConfidenceModifier(condition="fresh_info_lt_1_month", modifier=0.05),
    ConfidenceModifier(condition="stale_info_gt_6_months", modifier=-0.05),
    ConfidenceModifier(condition="breaking_change_known", modifier=-0.15),
    ConfidenceModifier(condition="production_examples_exist", modifier=0.05),
    ConfidenceModifier(condition="no_examples_found", modifier=-0.05),
    ConfidenceModifier(condition="exact_use_case_match", modifier=0.05),
    ConfidenceModifier(condition="tangential_match", modifier=-0.05),
    ConfidenceModifier(condition="multiple_kb_sources_agree", modifier=0.05),
    ConfidenceModifier(condition="research_round_improved_score", modifier=0.03),
]


class ValidationSource(BaseModel):
    source_type: str
    name: str
    result: str
    summary: str = ""


class ConfidenceReport(BaseModel):
    task_description: str
    category: TaskCategory
    threshold: float
    kb_result: str = "not_found"
    mcp_result: str = "silent"
    agreement_level: AgreementLevel = AgreementLevel.LOW
    base_score: float = 0.0
    modifiers_applied: list[dict[str, Any]] = Field(default_factory=list)
    final_score: float = 0.0
    decision: DecisionAction = DecisionAction.ASK_USER
    research_rounds: int = 0
    research_notes: list[str] = Field(default_factory=list)
    sources: list[ValidationSource] = Field(default_factory=list)


class ConfidenceEngine:
    def __init__(self):
        self.max_research_rounds = settings.MAX_CONFIDENCE_RESEARCH_ROUNDS

    def classify_category(self, task_description: str, task_type: str = "") -> TaskCategory:
        critical_keywords = [
            "security", "auth", "secret",
            "credential", "production_deploy", "delete_data",
        ]
        important_keywords = [
            "architecture", "breaking_change", "migration",
            "schema_change", "config_change",
        ]

        text = f"{task_description} {task_type}".lower()
        for kw in critical_keywords:
            if kw in text:
                return TaskCategory.CRITICAL
        for kw in important_keywords:
            if kw in text:
                return TaskCategory.IMPORTANT
        if any(kw in text for kw in ["new_feature", "refactor", "pipeline", "agent"]):
            return TaskCategory.STANDARD
        return TaskCategory.ADVISORY

    def calculate_agreement(self, kb_has_pattern: bool, mcp_result: str) -> AgreementLevel:
        kb_key = "kb_has_pattern" if kb_has_pattern else "kb_silent"
        mcp_key = {
            "agrees": "mcp_agrees",
            "disagrees": "mcp_disagrees",
        }.get(mcp_result, "mcp_silent")
        return AGREEMENT_MATRIX[kb_key][mcp_key]

    def calculate_base_score(self, agreement_level: AgreementLevel) -> float:
        return AGREEMENT_BASE_SCORES[agreement_level]

    def apply_modifiers(
        self,
        base_score: float,
        active_conditions: list[str],
    ) -> tuple[float, list[dict[str, Any]]]:
        score = base_score
        applied: list[dict[str, Any]] = []
        for mod in MODIFIERS:
            if mod.condition in active_conditions:
                score = max(0.0, min(1.0, score + mod.modifier))
                applied.append({"condition": mod.condition, "modifier": mod.modifier})
        return round(score, 4), applied

    def decide(
        self,
        final_score: float,
        threshold: float,
        category: TaskCategory,
        research_rounds: int = 0,
    ) -> DecisionAction:
        if final_score >= threshold:
            return DecisionAction.EXECUTE
        if research_rounds < self.max_research_rounds:
            if category in (TaskCategory.STANDARD, TaskCategory.ADVISORY):
                return DecisionAction.RESEARCH
            if final_score >= (threshold - 0.10):
                return DecisionAction.RESEARCH
        if category == TaskCategory.CRITICAL:
            return DecisionAction.REFUSE
        if category == TaskCategory.IMPORTANT:
            return DecisionAction.ASK_USER
        if category == TaskCategory.STANDARD:
            if final_score >= (threshold - 0.10):
                return DecisionAction.DISCLAIM
            return DecisionAction.ASK_USER
        return DecisionAction.DISCLAIM

    def evaluate(
        self,
        task_description: str,
        task_type: str = "",
        kb_has_pattern: bool = False,
        mcp_result: str = "silent",
        active_conditions: list[str] | None = None,
        research_rounds: int = 0,
        research_notes: list[str] | None = None,
        sources: list[ValidationSource] | None = None,
    ) -> ConfidenceReport:
        category = self.classify_category(task_description, task_type)
        threshold = CATEGORY_THRESHOLDS[category]
        agreement = self.calculate_agreement(kb_has_pattern, mcp_result)
        base_score = self.calculate_base_score(agreement)
        final_score, applied = self.apply_modifiers(base_score, active_conditions or [])
        decision = self.decide(final_score, threshold, category, research_rounds)

        return ConfidenceReport(
            task_description=task_description,
            category=category,
            threshold=threshold,
            kb_result="found" if kb_has_pattern else "not_found",
            mcp_result=mcp_result,
            agreement_level=agreement,
            base_score=base_score,
            modifiers_applied=applied,
            final_score=final_score,
            decision=decision,
            research_rounds=research_rounds,
            research_notes=research_notes or [],
            sources=sources or [],
        )

    async def evaluate_with_research(
        self,
        task_description: str,
        task_type: str = "",
        kb_lookup: Any = None,
        mcp_query: Any = None,
        internet_search: Any = None,
    ) -> ConfidenceReport:
        """Evaluate confidence with iterative research rounds.

        When initial confidence < threshold, researches up to MAX_ROUNDS
        using KB → MCP → internet to improve confidence before asking user.
        """
        kb_has_pattern = False
        mcp_result = "silent"
        active_conditions: list[str] = []
        sources: list[ValidationSource] = []
        research_notes: list[str] = []

        if kb_lookup:
            try:
                kb_result = await kb_lookup(task_description)
                if kb_result and kb_result.get("found"):
                    kb_has_pattern = True
                    sources.append(ValidationSource(
                        source_type="kb",
                        name=kb_result.get("source", "unknown"),
                        result="found",
                        summary=kb_result.get("summary", ""),
                    ))
                    if kb_result.get("multiple_sources"):
                        active_conditions.append("multiple_kb_sources_agree")
                    if kb_result.get("fresh"):
                        active_conditions.append("fresh_info_lt_1_month")
                    elif kb_result.get("stale"):
                        active_conditions.append("stale_info_gt_6_months")
                    if kb_result.get("production_examples"):
                        active_conditions.append("production_examples_exist")
                    elif not kb_result.get("production_examples", True):
                        active_conditions.append("no_examples_found")
                    if kb_result.get("exact_match"):
                        active_conditions.append("exact_use_case_match")
                    elif kb_result.get("tangential"):
                        active_conditions.append("tangential_match")
            except Exception:
                research_notes.append("KB lookup failed")

        report = self.evaluate(
            task_description, task_type, kb_has_pattern, mcp_result,
            active_conditions, 0, research_notes, sources,
        )

        for round_num in range(1, self.max_research_rounds + 1):
            if report.decision != DecisionAction.RESEARCH:
                break

            research_notes.append(f"Research round {round_num}")

            if mcp_query and mcp_result == "silent":
                try:
                    mcp_resp = await mcp_query(task_description)
                    if mcp_resp:
                        mcp_result = "agrees" if mcp_resp.get("agrees", False) else "disagrees"
                        sources.append(ValidationSource(
                            source_type="mcp",
                            name=mcp_resp.get("source", "mcp"),
                            result=mcp_result,
                            summary=mcp_resp.get("summary", ""),
                        ))
                        if mcp_resp.get("fresh"):
                            active_conditions.append("fresh_info_lt_1_month")
                        if mcp_resp.get("production_examples"):
                            active_conditions.append("production_examples_exist")
                        if mcp_resp.get("breaking_change"):
                            active_conditions.append("breaking_change_known")
                except Exception:
                    research_notes.append("MCP query failed")

            if internet_search and report.final_score < report.threshold - 0.05:
                try:
                    web_resp = await internet_search(task_description)
                    if web_resp and web_resp.get("found"):
                        active_conditions.append("research_round_improved_score")
                        sources.append(ValidationSource(
                            source_type="internet",
                            name=web_resp.get("source", "web_search"),
                            result="found",
                            summary=web_resp.get("summary", ""),
                        ))
                        if web_resp.get("production_examples"):
                            active_conditions.append("production_examples_exist")
                except Exception:
                    research_notes.append("Internet search failed")

            report = self.evaluate(
                task_description, task_type, kb_has_pattern, mcp_result,
                active_conditions, round_num, research_notes, sources,
            )

        return report


confidence_engine = ConfidenceEngine()
